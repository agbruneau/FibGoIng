"""Backend For Frontend - BFF Mobile et BFF Courtier."""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from abc import ABC, abstractmethod


class BaseBFF(ABC):
    """Classe de base pour les BFF."""

    def __init__(self, services: Dict[str, Any]):
        """
        Args:
            services: Dictionnaire des services backend disponibles
        """
        self.services = services

    @abstractmethod
    async def get_home(self, user_id: str) -> dict:
        """Ecran d'accueil specifique au canal."""
        pass


class BFFMobile(BaseBFF):
    """
    BFF optimise pour l'application mobile.

    Caracteristiques:
    - Reponses compactes
    - Agregation pour reduire les appels
    - Donnees formatees pour affichage
    """

    async def get_home(self, user_id: str) -> dict:
        """
        Ecran d'accueil mobile.
        Agrege les donnees essentielles en un seul appel.
        """
        # Appels paralleles pour la performance
        customer_task = self._get_customer(user_id)
        policies_task = self._get_active_policies(user_id)
        claims_task = self._get_open_claims(user_id)
        balance_task = self._get_balance(user_id)

        customer, policies, claims, balance = await asyncio.gather(
            customer_task, policies_task, claims_task, balance_task,
            return_exceptions=True
        )

        # Construction de la reponse optimisee
        return {
            "greeting": self._build_greeting(customer),
            "summary": {
                "active_policies": len(policies) if isinstance(policies, list) else 0,
                "open_claims": len(claims) if isinstance(claims, list) else 0,
                "amount_due": balance.get("outstanding_balance", 0) if isinstance(balance, dict) else 0
            },
            "quick_actions": self._get_quick_actions(),
            "alerts": self._build_alerts(policies, claims, balance),
            "updated_at": datetime.now().isoformat()
        }

    async def get_policies_list(self, user_id: str) -> dict:
        """Liste simplifiee des polices pour mobile."""
        policies = await self._get_policies(user_id)

        return {
            "policies": [
                {
                    "id": p.get("number"),
                    "product": self._format_product(p.get("product")),
                    "status": self._format_status(p.get("status")),
                    "premium": f"{p.get('premium', 0):.2f} EUR/an"
                }
                for p in policies
            ],
            "total": len(policies)
        }

    async def get_claim_detail(self, claim_id: str) -> dict:
        """Detail d'un sinistre optimise pour mobile."""
        claim = await self._get_claim(claim_id)

        if claim.get("error"):
            return claim

        return {
            "id": claim.get("number"),
            "type": self._format_claim_type(claim.get("type")),
            "status": self._format_status(claim.get("status")),
            "description": claim.get("description", "")[:200],  # Tronque
            "incident_date": self._format_date(claim.get("incident_date")),
            "amount": {
                "estimated": claim.get("estimated_amount"),
                "approved": claim.get("approved_amount")
            },
            "can_add_documents": claim.get("status") in ["OPEN", "ASSESSED"]
        }

    async def declare_claim(self, user_id: str, claim_data: dict) -> dict:
        """Declaration simplifiee de sinistre depuis mobile."""
        # Validation simplifiee
        if not claim_data.get("policy_id"):
            return {"error": True, "message": "Selectionnez un contrat"}

        if not claim_data.get("description"):
            return {"error": True, "message": "Decrivez le sinistre"}

        # Creation via le service
        claims_service = self.services.get("claims")
        if not claims_service:
            return {"error": True, "message": "Service indisponible"}

        result = await claims_service.create_claim(
            policy_number=claim_data["policy_id"],
            claim_type=claim_data.get("type", "AUTRE"),
            description=claim_data["description"],
            incident_date=claim_data.get("incident_date")
        )

        if result.get("error"):
            return result

        return {
            "success": True,
            "claim_id": result.get("number"),
            "message": "Votre declaration a ete enregistree",
            "next_steps": [
                "Un expert vous contactera sous 48h",
                "Ajoutez des photos si possible"
            ]
        }

    # Methodes privees

    async def _get_customer(self, user_id: str) -> dict:
        customer_service = self.services.get("customer_hub")
        if customer_service:
            return await customer_service.get_customer(user_id)
        return {}

    async def _get_policies(self, user_id: str) -> list:
        policy_service = self.services.get("policy_admin")
        if policy_service:
            return await policy_service.list_policies(customer_id=user_id)
        return []

    async def _get_active_policies(self, user_id: str) -> list:
        policies = await self._get_policies(user_id)
        return [p for p in policies if p.get("status") == "ACTIVE"]

    async def _get_open_claims(self, user_id: str) -> list:
        claims_service = self.services.get("claims")
        if claims_service:
            all_claims = await claims_service.list_claims(status="OPEN")
            # TODO: Filtrer par user_id via les policies
            return all_claims
        return []

    async def _get_claim(self, claim_id: str) -> dict:
        claims_service = self.services.get("claims")
        if claims_service:
            return await claims_service.get_claim(claim_id)
        return {"error": True, "message": "Service indisponible"}

    async def _get_balance(self, user_id: str) -> dict:
        billing_service = self.services.get("billing")
        if billing_service:
            # Recupere le solde de toutes les polices du client
            return {"outstanding_balance": 0}  # Simplifie
        return {}

    def _build_greeting(self, customer: Any) -> str:
        if isinstance(customer, dict) and "name" in customer:
            first_name = customer["name"].split()[0]
            hour = datetime.now().hour
            if hour < 12:
                return f"Bonjour {first_name}"
            elif hour < 18:
                return f"Bon apres-midi {first_name}"
            else:
                return f"Bonsoir {first_name}"
        return "Bienvenue"

    def _get_quick_actions(self) -> list:
        return [
            {"id": "declare_claim", "label": "Declarer un sinistre", "icon": "alert"},
            {"id": "attestation", "label": "Mon attestation", "icon": "document"},
            {"id": "contact", "label": "Nous contacter", "icon": "phone"}
        ]

    def _build_alerts(self, policies: Any, claims: Any, balance: Any) -> list:
        alerts = []

        # Alerte si montant du
        if isinstance(balance, dict) and balance.get("outstanding_balance", 0) > 0:
            alerts.append({
                "type": "warning",
                "message": f"Vous avez {balance['outstanding_balance']:.2f} EUR a regler"
            })

        # Alerte sinistre en cours
        if isinstance(claims, list) and len(claims) > 0:
            alerts.append({
                "type": "info",
                "message": f"{len(claims)} sinistre(s) en cours de traitement"
            })

        return alerts

    def _format_product(self, product: str) -> str:
        mapping = {
            "AUTO": "Assurance Auto",
            "HABITATION": "Assurance Habitation",
            "MRH": "Multirisque Habitation"
        }
        return mapping.get(product, product or "")

    def _format_status(self, status: str) -> str:
        mapping = {
            "ACTIVE": "Actif",
            "DRAFT": "Brouillon",
            "PENDING": "En attente",
            "OPEN": "Ouvert",
            "ASSESSED": "Expertise",
            "APPROVED": "Approuve",
            "SETTLED": "Regle"
        }
        return mapping.get(status, status or "")

    def _format_claim_type(self, claim_type: str) -> str:
        mapping = {
            "ACCIDENT": "Accident",
            "VOL": "Vol",
            "DEGAT_EAU": "Degat des eaux",
            "INCENDIE": "Incendie",
            "BRIS_GLACE": "Bris de glace"
        }
        return mapping.get(claim_type, claim_type or "")

    def _format_date(self, date_str: str) -> str:
        if not date_str:
            return ""
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return date_str[:10] if len(date_str) >= 10 else date_str


class BFFCourtier(BaseBFF):
    """
    BFF optimise pour le portail courtier.

    Caracteristiques:
    - Donnees completes et detaillees
    - Acces multi-clients
    - Operations batch
    """

    async def get_home(self, broker_id: str) -> dict:
        """Dashboard courtier avec KPIs."""
        return {
            "broker_id": broker_id,
            "kpis": {
                "pending_quotes": await self._count_pending_quotes(broker_id),
                "active_policies": await self._count_active_policies(broker_id),
                "open_claims": await self._count_open_claims(broker_id),
                "commission_mtd": 0  # A implementer
            },
            "recent_activity": await self._get_recent_activity(broker_id),
            "alerts": await self._get_broker_alerts(broker_id)
        }

    async def search_customers(self, query: str, broker_id: str) -> dict:
        """Recherche de clients pour le courtier."""
        customer_service = self.services.get("customer_hub")
        if not customer_service:
            return {"results": [], "total": 0}

        customers = await customer_service.list_customers(search=query)

        return {
            "results": [
                {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "email": c.get("email"),
                    "policies_count": 0  # A enrichir
                }
                for c in customers[:20]
            ],
            "total": len(customers)
        }

    async def get_customer_360(self, customer_id: str) -> dict:
        """Vue 360 complete d'un client pour le courtier."""
        # Delegue au compositeur
        from app.integration.applications.composition import Customer360Composer

        composer = Customer360Composer(self.services)
        return await composer.compose(customer_id)

    async def create_quote_batch(self, quotes_data: List[dict]) -> dict:
        """Creation de plusieurs devis en batch."""
        quote_service = self.services.get("quote_engine")
        if not quote_service:
            return {"error": True, "message": "Service indisponible"}

        results = []
        for data in quotes_data:
            result = await quote_service.create_quote(
                customer_id=data["customer_id"],
                product=data["product"],
                risk_data=data.get("risk_data", {})
            )
            results.append({
                "customer_id": data["customer_id"],
                "success": not result.get("error"),
                "quote_id": result.get("id"),
                "premium": result.get("premium")
            })

        return {
            "processed": len(results),
            "successful": len([r for r in results if r["success"]]),
            "results": results
        }

    # Methodes privees

    async def _count_pending_quotes(self, broker_id: str) -> int:
        quote_service = self.services.get("quote_engine")
        if quote_service:
            quotes = await quote_service.list_quotes()
            return len([q for q in quotes if q.get("status") == "PENDING"])
        return 0

    async def _count_active_policies(self, broker_id: str) -> int:
        policy_service = self.services.get("policy_admin")
        if policy_service:
            policies = await policy_service.list_policies(status="ACTIVE")
            return len(policies)
        return 0

    async def _count_open_claims(self, broker_id: str) -> int:
        claims_service = self.services.get("claims")
        if claims_service:
            claims = await claims_service.list_claims(status="OPEN")
            return len(claims)
        return 0

    async def _get_recent_activity(self, broker_id: str) -> list:
        # Simplifie - retourne activite vide
        return []

    async def _get_broker_alerts(self, broker_id: str) -> list:
        return []

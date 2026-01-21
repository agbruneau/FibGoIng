"""API Composition - Agregation de services pour vues complexes."""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime


class Customer360Composer:
    """
    Compose une vue 360 degres d'un client.

    Agrege les donnees de:
    - Customer Hub (infos client)
    - Policy Admin (polices)
    - Claims Management (sinistres)
    - Billing (facturation)
    - Document Management (documents)
    - External Rating (score risque)
    """

    def __init__(self, services: Dict[str, Any]):
        """
        Args:
            services: Dictionnaire des services disponibles
        """
        self.services = services

    async def compose(self, customer_id: str, include: List[str] = None) -> dict:
        """
        Compose la vue 360 d'un client.

        Args:
            customer_id: ID du client
            include: Sections a inclure (default: toutes)

        Returns:
            Vue 360 agregee
        """
        include = include or ["customer", "policies", "claims", "billing", "documents", "risk"]

        # Prepare les taches
        tasks = {}

        if "customer" in include:
            tasks["customer"] = self._fetch_customer(customer_id)

        if "policies" in include:
            tasks["policies"] = self._fetch_policies(customer_id)

        if "claims" in include:
            tasks["claims"] = self._fetch_claims(customer_id)

        if "billing" in include:
            tasks["billing"] = self._fetch_billing(customer_id)

        if "documents" in include:
            tasks["documents"] = self._fetch_documents(customer_id)

        if "risk" in include:
            tasks["risk"] = self._fetch_risk_score(customer_id)

        # Execute en parallele
        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True
        )

        # Assemble la reponse
        response = {
            "customer_id": customer_id,
            "generated_at": datetime.now().isoformat(),
            "sections": {}
        }

        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                response["sections"][key] = {
                    "available": False,
                    "error": str(result)
                }
            else:
                response["sections"][key] = {
                    "available": True,
                    "data": result
                }

        # Ajoute des KPIs si toutes les donnees sont disponibles
        response["summary"] = self._build_summary(response["sections"])

        return response

    async def compose_minimal(self, customer_id: str) -> dict:
        """
        Version minimale pour les cas ou la performance est critique.
        Seulement client + policies.
        """
        customer, policies = await asyncio.gather(
            self._fetch_customer(customer_id),
            self._fetch_policies(customer_id),
            return_exceptions=True
        )

        return {
            "customer_id": customer_id,
            "customer": customer if not isinstance(customer, Exception) else None,
            "policies_count": len(policies) if isinstance(policies, list) else 0,
            "is_minimal": True
        }

    # Methodes de fetch

    async def _fetch_customer(self, customer_id: str) -> dict:
        """Recupere les infos client."""
        service = self.services.get("customer_hub")
        if not service:
            return {"error": True, "message": "Service unavailable"}

        result = await service.get_customer(customer_id)

        if result.get("error"):
            return result

        # Ne garde que les champs essentiels
        return {
            "id": result.get("id"),
            "name": result.get("name"),
            "email": result.get("email"),
            "phone": result.get("phone"),
            "status": result.get("status"),
            "since": result.get("created_at", "")[:10]
        }

    async def _fetch_policies(self, customer_id: str) -> dict:
        """Recupere les polices du client."""
        service = self.services.get("policy_admin")
        if not service:
            return {"total": 0, "items": []}

        policies = await service.list_policies(customer_id=customer_id)

        if isinstance(policies, dict) and policies.get("error"):
            return {"total": 0, "items": [], "error": policies.get("message")}

        active = [p for p in policies if p.get("status") == "ACTIVE"]
        other = [p for p in policies if p.get("status") != "ACTIVE"]

        return {
            "total": len(policies),
            "active_count": len(active),
            "active": [self._format_policy(p) for p in active],
            "other": [self._format_policy(p) for p in other[:5]]  # Limite
        }

    async def _fetch_claims(self, customer_id: str) -> dict:
        """Recupere les sinistres lies au client."""
        service = self.services.get("claims")
        policy_service = self.services.get("policy_admin")

        if not service:
            return {"total": 0, "items": []}

        # Recupere d'abord les polices pour avoir les policy_numbers
        all_claims = await service.list_claims()

        if isinstance(all_claims, dict) and all_claims.get("error"):
            return {"total": 0, "items": [], "error": all_claims.get("message")}

        # TODO: Filtrer par customer via les policies
        # Pour l'instant, retourne tous les claims (simplification)

        open_claims = [c for c in all_claims if c.get("status") in ["OPEN", "ASSESSED", "APPROVED"]]
        settled = [c for c in all_claims if c.get("status") == "SETTLED"]

        return {
            "total": len(all_claims),
            "open_count": len(open_claims),
            "open": [self._format_claim(c) for c in open_claims],
            "recent_settled": [self._format_claim(c) for c in settled[:3]]
        }

    async def _fetch_billing(self, customer_id: str) -> dict:
        """Recupere les infos de facturation."""
        service = self.services.get("billing")
        if not service:
            return {"available": False}

        # Recupere les factures
        invoices = await service.list_invoices()

        if isinstance(invoices, dict) and invoices.get("error"):
            return {"error": invoices.get("message")}

        pending = [i for i in invoices if i.get("status") in ["PENDING", "OVERDUE"]]
        paid = [i for i in invoices if i.get("status") == "PAID"]

        total_due = sum(i.get("amount", 0) - i.get("amount_paid", 0) for i in pending)

        return {
            "outstanding_balance": total_due,
            "pending_invoices": len(pending),
            "paid_invoices": len(paid),
            "recent_pending": [self._format_invoice(i) for i in pending[:3]]
        }

    async def _fetch_documents(self, customer_id: str) -> dict:
        """Recupere les documents du client."""
        service = self.services.get("document_mgmt")
        if not service:
            return {"total": 0}

        documents = await service.list_documents(entity_id=customer_id)

        if isinstance(documents, dict) and documents.get("error"):
            return {"total": 0, "error": documents.get("message")}

        by_category = {}
        for doc in documents:
            cat = doc.get("category", "AUTRE")
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "total": len(documents),
            "by_category": by_category
        }

    async def _fetch_risk_score(self, customer_id: str) -> dict:
        """Recupere le score de risque externe."""
        service = self.services.get("external_rating")
        if not service:
            return {"available": False}

        result = await service.get_risk_score(customer_id, {})

        if result.get("error"):
            return {"available": False, "error": result.get("message")}

        return {
            "score": result.get("score"),
            "category": result.get("category"),
            "factors": result.get("factors", {}),
            "calculated_at": result.get("calculated_at")
        }

    # Formatteurs

    def _format_policy(self, policy: dict) -> dict:
        """Formate une police pour l'affichage."""
        return {
            "number": policy.get("number"),
            "product": policy.get("product"),
            "status": policy.get("status"),
            "premium": policy.get("premium"),
            "coverages": policy.get("coverages", [])
        }

    def _format_claim(self, claim: dict) -> dict:
        """Formate un sinistre pour l'affichage."""
        return {
            "number": claim.get("number"),
            "type": claim.get("type"),
            "status": claim.get("status"),
            "incident_date": claim.get("incident_date", "")[:10],
            "estimated_amount": claim.get("estimated_amount"),
            "approved_amount": claim.get("approved_amount")
        }

    def _format_invoice(self, invoice: dict) -> dict:
        """Formate une facture pour l'affichage."""
        return {
            "number": invoice.get("number"),
            "amount": invoice.get("amount"),
            "amount_paid": invoice.get("amount_paid"),
            "status": invoice.get("status"),
            "due_date": invoice.get("due_date", "")[:10]
        }

    def _build_summary(self, sections: dict) -> dict:
        """Construit un resume a partir des sections."""
        summary = {}

        if sections.get("policies", {}).get("available"):
            summary["active_policies"] = sections["policies"]["data"].get("active_count", 0)

        if sections.get("claims", {}).get("available"):
            summary["open_claims"] = sections["claims"]["data"].get("open_count", 0)

        if sections.get("billing", {}).get("available"):
            summary["outstanding_balance"] = sections["billing"]["data"].get("outstanding_balance", 0)

        if sections.get("risk", {}).get("available"):
            summary["risk_category"] = sections["risk"]["data"].get("category")

        return summary

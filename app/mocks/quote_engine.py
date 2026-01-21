"""Service mock pour le Quote Engine - Calcul de devis."""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .base import MockService


class QuoteEngine(MockService):
    """
    Simule le moteur de tarification pour les devis d'assurance.

    Fonctionnalités:
    - Création de devis (auto, habitation)
    - Calcul de prime basique selon profil
    - Gestion de la validité des devis
    """

    def __init__(self, initial_data: List[Dict] = None):
        super().__init__("Quote Engine", default_latency=50)
        self.quotes: Dict[str, Dict] = {}

        # Charger les données initiales
        if initial_data:
            for quote in initial_data:
                self.quotes[quote["id"]] = quote

    def _generate_quote_id(self) -> str:
        """Génère un ID de devis unique."""
        seq = len(self.quotes) + 1
        return f"Q{seq:04d}"

    def _calculate_premium(self, product: str, risk_data: dict) -> float:
        """Calcule la prime selon le produit et les données de risque."""
        base_premium = {
            "AUTO": 500.0,
            "HABITATION": 300.0,
            "MRH": 350.0,
        }.get(product.upper(), 400.0)

        # Ajustements basiques
        age = risk_data.get("age", 30)
        if age < 25:
            base_premium *= 1.5  # Jeune conducteur
        elif age > 60:
            base_premium *= 1.2  # Senior

        # Bonus/Malus pour auto
        if product.upper() == "AUTO":
            bonus_malus = risk_data.get("bonus_malus", 1.0)
            base_premium *= bonus_malus

        # Valeur du bien pour habitation
        if product.upper() in ["HABITATION", "MRH"]:
            surface = risk_data.get("surface", 50)
            base_premium += surface * 2

        return round(base_premium, 2)

    async def create_quote(
        self,
        customer_id: str,
        product: str,
        risk_data: dict = None
    ) -> Dict[str, Any]:
        """
        Crée un nouveau devis.

        Args:
            customer_id: ID du client
            product: Type de produit (AUTO, HABITATION, MRH)
            risk_data: Données de risque pour le calcul

        Returns:
            Devis créé avec ID et prime calculée
        """
        async def _create():
            risk_data_clean = risk_data or {}
            quote_id = self._generate_quote_id()

            quote = {
                "id": quote_id,
                "customer_id": customer_id,
                "product": product.upper(),
                "risk_data": risk_data_clean,
                "premium": self._calculate_premium(product, risk_data_clean),
                "status": "PENDING",
                "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
                "created_at": datetime.now().isoformat(),
            }

            self.quotes[quote_id] = quote
            return quote

        return await self.execute("create_quote", _create)

    async def get_quote(self, quote_id: str) -> Optional[Dict]:
        """Récupère un devis par son ID."""
        async def _get():
            quote = self.quotes.get(quote_id)
            if not quote:
                return {"error": True, "code": "NOT_FOUND", "message": f"Quote {quote_id} not found"}

            # Vérifier la validité
            valid_until = datetime.fromisoformat(quote["valid_until"])
            if datetime.now() > valid_until and quote["status"] == "PENDING":
                quote["status"] = "EXPIRED"

            return quote

        return await self.execute("get_quote", _get)

    async def list_quotes(self, customer_id: str = None) -> List[Dict]:
        """Liste les devis, optionnellement filtrés par client."""
        async def _list():
            result = list(self.quotes.values())
            if customer_id:
                result = [q for q in result if q["customer_id"] == customer_id]
            return result

        return await self.execute("list_quotes", _list)

    async def accept_quote(self, quote_id: str) -> Dict:
        """Accepte un devis (le transforme en demande de police)."""
        async def _accept():
            quote = self.quotes.get(quote_id)
            if not quote:
                return {"error": True, "code": "NOT_FOUND", "message": f"Quote {quote_id} not found"}

            if quote["status"] == "EXPIRED":
                return {"error": True, "code": "EXPIRED", "message": "Quote is expired"}

            if quote["status"] == "ACCEPTED":
                return {"error": True, "code": "ALREADY_ACCEPTED", "message": "Quote already accepted"}

            quote["status"] = "ACCEPTED"
            quote["accepted_at"] = datetime.now().isoformat()
            return quote

        return await self.execute("accept_quote", _accept)

    async def reject_quote(self, quote_id: str, reason: str = None) -> Dict:
        """Rejette un devis."""
        async def _reject():
            quote = self.quotes.get(quote_id)
            if not quote:
                return {"error": True, "code": "NOT_FOUND", "message": f"Quote {quote_id} not found"}

            quote["status"] = "REJECTED"
            quote["rejection_reason"] = reason
            quote["rejected_at"] = datetime.now().isoformat()
            return quote

        return await self.execute("reject_quote", _reject)

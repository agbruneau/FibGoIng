"""Service mock pour l'API de tarification externe."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import MockService


class ExternalRating(MockService):
    """
    Simule une API de tarification externe (réassureur, comparateur).

    Ce service a une latence plus élevée (appel externe)
    et un taux d'erreur configurable pour simuler l'instabilité.
    """

    def __init__(self, initial_data: dict = None):
        super().__init__("External Rating", default_latency=200, failure_rate=0.05)
        self.rates = initial_data or {}

    def _generate_rate_id(self) -> str:
        """Génère un ID de tarif unique."""
        seq = len(self.rates) + 1
        return f"RATE-{seq:04d}"

    async def get_rate(self, product: str, risk_profile: dict) -> Dict[str, Any]:
        """
        Obtient un tarif externe pour un profil de risque.

        Args:
            product: Type de produit (AUTO, HABITATION, etc.)
            risk_profile: Profil de risque

        Returns:
            Tarif calculé avec détails
        """
        async def _rate():
            product_upper = product.upper()

            # Tarifs de base par produit
            base_rates = {
                "AUTO": {
                    "base": 450.0,
                    "rc_rate": 0.3,
                    "vol_rate": 0.15,
                    "bris_glace_rate": 0.05,
                },
                "HABITATION": {
                    "base": 280.0,
                    "incendie_rate": 0.2,
                    "degat_eau_rate": 0.15,
                    "vol_rate": 0.1,
                },
                "MRH": {
                    "base": 320.0,
                    "rc_rate": 0.25,
                    "mobilier_rate": 0.2,
                    "assistance_rate": 0.05,
                }
            }

            if product_upper not in base_rates:
                return {"error": True, "code": "UNSUPPORTED_PRODUCT", "message": f"Product not supported: {product}"}

            rates = base_rates[product_upper]

            # Calculer le tarif selon le profil
            premium = rates["base"]

            # Facteurs de risque
            age = risk_profile.get("age", 30)
            if age < 25:
                premium *= 1.4
            elif age > 65:
                premium *= 1.15

            # Historique sinistres
            claims_count = risk_profile.get("claims_history", 0)
            premium *= (1 + claims_count * 0.1)

            # Zone géographique
            zone = risk_profile.get("zone", "B")
            zone_factors = {"A": 1.3, "B": 1.0, "C": 0.85}
            premium *= zone_factors.get(zone.upper(), 1.0)

            # Détail des garanties
            coverages = {}
            for key, rate in rates.items():
                if key != "base" and key.endswith("_rate"):
                    coverage_name = key.replace("_rate", "").upper()
                    coverages[coverage_name] = round(premium * rate, 2)

            return {
                "product": product_upper,
                "base_premium": round(premium, 2),
                "coverages": coverages,
                "total_premium": round(premium + sum(coverages.values()), 2),
                "valid_until": datetime.now().isoformat(),
                "provider": "External Rating Service",
                "reference": self._generate_rate_id(),
                "risk_score": min(100, max(0, 50 + claims_count * 10 - (age - 30))),
            }

        return await self.execute("get_rate", _rate)

    async def get_bulk_rates(self, requests: list) -> List[Dict]:
        """
        Obtient plusieurs tarifs en une seule requête.

        Args:
            requests: Liste de {product, risk_profile}

        Returns:
            Liste des tarifs
        """
        async def _bulk():
            results = []
            for req in requests:
                rate = await self.get_rate(
                    product=req["product"],
                    risk_profile=req.get("risk_profile", {})
                )
                if rate.get("error"):
                    results.append({"success": False, "error": rate["message"]})
                else:
                    results.append({"success": True, "data": rate})
            return results

        return await self.execute("get_bulk_rates", _bulk)

    async def get_risk_score(self, customer_id: str, risk_data: dict) -> Dict:
        """
        Calcule un score de risque pour un client.

        Args:
            customer_id: ID du client
            risk_data: Données de risque

        Returns:
            Score de risque avec détails
        """
        async def _score():
            # Facteurs de scoring
            base_score = 50

            # Age
            age = risk_data.get("age", 30)
            if age < 25:
                base_score += 20
            elif age > 60:
                base_score += 10

            # Historique
            claims = risk_data.get("claims_count", 0)
            base_score += claims * 15

            # Ancienneté
            years_customer = risk_data.get("years_as_customer", 0)
            base_score -= min(20, years_customer * 2)

            # Normaliser entre 0 et 100
            final_score = max(0, min(100, base_score))

            # Catégoriser
            if final_score < 30:
                category = "LOW_RISK"
            elif final_score < 60:
                category = "MEDIUM_RISK"
            else:
                category = "HIGH_RISK"

            return {
                "customer_id": customer_id,
                "score": final_score,
                "category": category,
                "factors": {
                    "age_factor": "elevated" if age < 25 or age > 60 else "normal",
                    "claims_factor": "elevated" if claims > 0 else "normal",
                    "loyalty_factor": "positive" if years_customer > 3 else "neutral",
                },
                "calculated_at": datetime.now().isoformat(),
            }

        return await self.execute("get_risk_score", _score)

    async def get_market_rates(self, product: str) -> Dict:
        """Obtient les tarifs moyens du marché."""
        async def _market():
            market_data = {
                "AUTO": {
                    "avg_premium": 520.0,
                    "min_premium": 280.0,
                    "max_premium": 1200.0,
                    "trend": "+2.3%"
                },
                "HABITATION": {
                    "avg_premium": 340.0,
                    "min_premium": 150.0,
                    "max_premium": 800.0,
                    "trend": "+1.8%"
                },
                "MRH": {
                    "avg_premium": 380.0,
                    "min_premium": 180.0,
                    "max_premium": 900.0,
                    "trend": "+2.1%"
                }
            }

            product_upper = product.upper()
            if product_upper not in market_data:
                return {"error": True, "code": "NO_DATA", "message": f"No market data for {product}"}

            return {
                "product": product_upper,
                "market_data": market_data[product_upper],
                "updated_at": datetime.now().isoformat(),
                "source": "Market Analytics Service"
            }

        return await self.execute("get_market_rates", _market)

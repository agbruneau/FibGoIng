"""Service mock pour la gestion des sinistres."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import MockService


class ClaimsManagement(MockService):
    """
    Simule le système de gestion des sinistres.

    Fonctionnalités:
    - Déclaration de sinistres
    - Suivi du cycle de vie (OPEN -> ASSESSED -> APPROVED/REJECTED -> SETTLED)
    - Estimation et règlement
    """

    # Cycle de vie des sinistres
    VALID_TRANSITIONS = {
        "OPEN": ["ASSESSED", "REJECTED"],
        "ASSESSED": ["APPROVED", "REJECTED"],
        "APPROVED": ["SETTLED", "REJECTED"],
        "REJECTED": [],
        "SETTLED": [],
    }

    def __init__(self, initial_data: List[Dict] = None):
        super().__init__("Claims Management", default_latency=40)
        self.claims: Dict[str, Dict] = {}
        self.history: List[Dict] = []

        # Charger les données initiales
        if initial_data:
            for claim in initial_data:
                self.claims[claim["number"]] = claim

    def _generate_claim_number(self) -> str:
        """Génère un numéro de sinistre unique."""
        year = datetime.now().year
        seq = len(self.claims) + 1
        return f"CLM-{year}-{seq:04d}"

    def _record_history(self, claim_number: str, status: str, note: str):
        """Enregistre une action dans l'historique."""
        self.history.append({
            "claim_number": claim_number,
            "status": status,
            "note": note,
            "timestamp": datetime.now().isoformat()
        })

    async def create_claim(
        self,
        policy_number: str,
        claim_type: str,
        description: str,
        incident_date: str = None,
        estimated_amount: float = None
    ) -> Dict[str, Any]:
        """
        Déclare un nouveau sinistre.

        Args:
            policy_number: Numéro de la police concernée
            claim_type: Type de sinistre (ACCIDENT, VOL, DEGAT_EAU, INCENDIE)
            description: Description du sinistre
            incident_date: Date de l'incident
            estimated_amount: Montant estimé

        Returns:
            Sinistre créé
        """
        async def _create():
            now = datetime.now()
            claim_number = self._generate_claim_number()

            claim = {
                "number": claim_number,
                "policy_number": policy_number,
                "type": claim_type.upper(),
                "description": description,
                "incident_date": incident_date or now.isoformat(),
                "estimated_amount": estimated_amount,
                "approved_amount": None,
                "status": "OPEN",
                "reported_date": now.isoformat(),
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            self.claims[claim_number] = claim
            self._record_history(claim_number, "OPEN", "Sinistre déclaré")

            return claim

        return await self.execute("create_claim", _create)

    async def get_claim(self, claim_number: str) -> Optional[Dict]:
        """Récupère un sinistre par son numéro."""
        async def _get():
            claim = self.claims.get(claim_number)
            if not claim:
                return {"error": True, "code": "NOT_FOUND", "message": f"Claim {claim_number} not found"}
            return claim

        return await self.execute("get_claim", _get)

    async def list_claims(
        self,
        policy_number: str = None,
        status: str = None
    ) -> List[Dict]:
        """Liste les sinistres avec filtres optionnels."""
        async def _list():
            result = list(self.claims.values())

            if policy_number:
                result = [c for c in result if c["policy_number"] == policy_number]

            if status:
                result = [c for c in result if c["status"] == status.upper()]

            return result

        return await self.execute("list_claims", _list)

    async def update_status(
        self,
        claim_number: str,
        new_status: str,
        note: str = None,
        approved_amount: float = None
    ) -> Dict:
        """Met à jour le statut d'un sinistre."""
        async def _update():
            claim = self.claims.get(claim_number)
            if not claim:
                return {"error": True, "code": "NOT_FOUND", "message": f"Claim {claim_number} not found"}

            current_status = claim["status"]
            new_status_upper = new_status.upper()

            # Vérifier la transition
            if new_status_upper not in self.VALID_TRANSITIONS.get(current_status, []):
                return {
                    "error": True,
                    "code": "INVALID_TRANSITION",
                    "message": f"Cannot transition from {current_status} to {new_status_upper}"
                }

            claim["status"] = new_status_upper
            claim["updated_at"] = datetime.now().isoformat()

            if approved_amount is not None:
                claim["approved_amount"] = approved_amount

            self._record_history(claim_number, new_status_upper, note or f"Status changed to {new_status_upper}")

            return claim

        return await self.execute("update_status", _update)

    async def assess_claim(self, claim_number: str, assessment: dict) -> Dict:
        """Effectue l'expertise d'un sinistre."""
        async def _assess():
            claim = self.claims.get(claim_number)
            if not claim:
                return {"error": True, "code": "NOT_FOUND", "message": f"Claim {claim_number} not found"}

            if claim["status"] != "OPEN":
                return {"error": True, "code": "INVALID_STATUS", "message": "Only OPEN claims can be assessed"}

            claim["assessment"] = assessment
            claim["assessed_at"] = datetime.now().isoformat()
            claim["status"] = "ASSESSED"
            claim["updated_at"] = datetime.now().isoformat()

            self._record_history(claim_number, "ASSESSED", "Assessment completed")

            return claim

        return await self.execute("assess_claim", _assess)

    async def settle_claim(
        self,
        claim_number: str,
        settlement_amount: float,
        payment_reference: str = None
    ) -> Dict:
        """Règle un sinistre approuvé."""
        async def _settle():
            claim = self.claims.get(claim_number)
            if not claim:
                return {"error": True, "code": "NOT_FOUND", "message": f"Claim {claim_number} not found"}

            if claim["status"] != "APPROVED":
                return {"error": True, "code": "INVALID_STATUS", "message": "Only APPROVED claims can be settled"}

            claim["status"] = "SETTLED"
            claim["settlement_amount"] = settlement_amount
            claim["payment_reference"] = payment_reference
            claim["settled_at"] = datetime.now().isoformat()
            claim["updated_at"] = datetime.now().isoformat()

            self._record_history(claim_number, "SETTLED", f"Settled for {settlement_amount}€")

            return claim

        return await self.execute("settle_claim", _settle)

    async def get_history(self, claim_number: str) -> List[Dict]:
        """Récupère l'historique d'un sinistre."""
        async def _get_history():
            return [h for h in self.history if h["claim_number"] == claim_number]

        return await self.execute("get_history", _get_history)

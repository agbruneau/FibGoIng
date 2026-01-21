"""Service mock pour le Policy Admin System - Gestion des polices."""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
from .base import MockService


class PolicyAdmin(MockService):
    """
    Simule le système d'administration des polices (PAS).

    Fonctionnalités:
    - CRUD complet sur les polices
    - Gestion du cycle de vie (création, activation, renouvellement, résiliation)
    - Historique des modifications
    """

    # Statuts possibles d'une police
    STATUSES = ["DRAFT", "PENDING", "ACTIVE", "SUSPENDED", "CANCELLED", "EXPIRED"]

    def __init__(self, initial_data: List[Dict] = None):
        super().__init__("Policy Admin System", default_latency=30)
        self.policies: Dict[str, Dict] = {}
        self.history: List[Dict] = []

        # Charger les données initiales
        if initial_data:
            for policy in initial_data:
                self.policies[policy["number"]] = policy

    def _generate_policy_number(self) -> str:
        """Génère un numéro de police unique."""
        year = datetime.now().year
        seq = len(self.policies) + 1
        return f"POL-{year}-{seq:04d}"

    def _record_history(self, policy_number: str, action: str, details: Dict):
        """Enregistre une action dans l'historique."""
        self.history.append({
            "policy_number": policy_number,
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    async def create_policy(
        self,
        customer_id: str,
        product: str,
        quote_id: Optional[str] = None,
        coverages: List[str] = None,
        premium: float = 0.0
    ) -> Dict[str, Any]:
        """
        Crée une nouvelle police.

        Args:
            customer_id: ID du client
            product: Type de produit
            quote_id: ID du devis source (optionnel)
            coverages: Liste des garanties
            premium: Prime annuelle

        Returns:
            La police créée
        """
        async def _create():
            policy_number = self._generate_policy_number()

            policy = {
                "number": policy_number,
                "customer_id": customer_id,
                "product": product,
                "quote_id": quote_id,
                "coverages": coverages or ["RC"],  # Responsabilité Civile par défaut
                "premium": premium,
                "status": "DRAFT",
                "start_date": None,
                "end_date": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            self.policies[policy_number] = policy
            self._record_history(policy_number, "CREATED", {"customer_id": customer_id})

            return policy

        return await self.execute("create_policy", _create)

    async def get_policy(self, policy_number: str) -> Optional[Dict]:
        """Récupère une police par son numéro."""
        async def _get():
            policy = self.policies.get(policy_number)
            if not policy:
                return {"error": True, "code": "NOT_FOUND", "message": f"Policy {policy_number} not found"}
            return policy

        return await self.execute("get_policy", _get)

    async def list_policies(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        product: Optional[str] = None
    ) -> List[Dict]:
        """Liste les polices avec filtres optionnels."""
        async def _list():
            result = list(self.policies.values())

            if customer_id:
                result = [p for p in result if p["customer_id"] == customer_id]

            if status:
                result = [p for p in result if p["status"] == status]

            if product:
                result = [p for p in result if p["product"] == product]

            return result

        return await self.execute("list_policies", _list)

    async def activate_policy(
        self,
        policy_number: str,
        start_date: Optional[str] = None
    ) -> Dict:
        """Active une police."""
        async def _activate():
            policy = self.policies.get(policy_number)
            if not policy:
                return {"error": True, "code": "NOT_FOUND", "message": f"Policy {policy_number} not found"}

            if policy["status"] not in ["DRAFT", "PENDING"]:
                return {"error": True, "code": "INVALID_STATUS", "message": f"Cannot activate policy with status {policy['status']}"}

            start = datetime.fromisoformat(start_date) if start_date else datetime.now()
            end = start + timedelta(days=365)

            policy["status"] = "ACTIVE"
            policy["start_date"] = start.isoformat()
            policy["end_date"] = end.isoformat()
            policy["updated_at"] = datetime.now().isoformat()

            self._record_history(policy_number, "ACTIVATED", {
                "start_date": policy["start_date"],
                "end_date": policy["end_date"]
            })

            return policy

        return await self.execute("activate_policy", _activate)

    async def suspend_policy(self, policy_number: str, reason: str) -> Dict:
        """Suspend une police."""
        async def _suspend():
            policy = self.policies.get(policy_number)
            if not policy:
                return {"error": True, "code": "NOT_FOUND", "message": f"Policy {policy_number} not found"}

            if policy["status"] != "ACTIVE":
                return {"error": True, "code": "INVALID_STATUS", "message": "Only active policies can be suspended"}

            policy["status"] = "SUSPENDED"
            policy["suspension_reason"] = reason
            policy["updated_at"] = datetime.now().isoformat()

            self._record_history(policy_number, "SUSPENDED", {"reason": reason})

            return policy

        return await self.execute("suspend_policy", _suspend)

    async def cancel_policy(self, policy_number: str, reason: str) -> Dict:
        """Résilie une police."""
        async def _cancel():
            policy = self.policies.get(policy_number)
            if not policy:
                return {"error": True, "code": "NOT_FOUND", "message": f"Policy {policy_number} not found"}

            if policy["status"] in ["CANCELLED", "EXPIRED"]:
                return {"error": True, "code": "INVALID_STATUS", "message": "Policy is already terminated"}

            policy["status"] = "CANCELLED"
            policy["cancellation_reason"] = reason
            policy["cancellation_date"] = datetime.now().isoformat()
            policy["updated_at"] = datetime.now().isoformat()

            self._record_history(policy_number, "CANCELLED", {"reason": reason})

            return policy

        return await self.execute("cancel_policy", _cancel)

    async def renew_policy(self, policy_number: str) -> Dict:
        """Renouvelle une police."""
        async def _renew():
            policy = self.policies.get(policy_number)
            if not policy:
                return {"error": True, "code": "NOT_FOUND", "message": f"Policy {policy_number} not found"}

            if policy["status"] not in ["ACTIVE", "EXPIRED"]:
                return {"error": True, "code": "INVALID_STATUS", "message": "Only active or expired policies can be renewed"}

            # Créer une nouvelle police basée sur l'ancienne
            new_number = self._generate_policy_number()
            old_end = datetime.fromisoformat(policy["end_date"]) if policy["end_date"] else datetime.now()
            new_start = old_end
            new_end = new_start + timedelta(days=365)

            new_policy = {
                **policy,
                "number": new_number,
                "previous_policy": policy_number,
                "status": "ACTIVE",
                "start_date": new_start.isoformat(),
                "end_date": new_end.isoformat(),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            # Marquer l'ancienne comme expirée
            policy["status"] = "EXPIRED"
            policy["renewed_by"] = new_number
            policy["updated_at"] = datetime.now().isoformat()

            self.policies[new_number] = new_policy
            self._record_history(policy_number, "RENEWED", {"new_policy": new_number})
            self._record_history(new_number, "CREATED_FROM_RENEWAL", {"previous_policy": policy_number})

            return new_policy

        return await self.execute("renew_policy", _renew)

    async def update_policy(self, policy_number: str, updates: Dict) -> Dict:
        """Met à jour une police."""
        async def _update():
            policy = self.policies.get(policy_number)
            if not policy:
                return {"error": True, "code": "NOT_FOUND", "message": f"Policy {policy_number} not found"}

            # Champs modifiables
            allowed_updates = ["coverages", "premium"]
            for key, value in updates.items():
                if key in allowed_updates:
                    policy[key] = value

            policy["updated_at"] = datetime.now().isoformat()
            self._record_history(policy_number, "UPDATED", updates)

            return policy

        return await self.execute("update_policy", _update)

    async def delete_policy(self, policy_number: str) -> Dict:
        """Supprime une police (soft delete via status CANCELLED)."""
        return await self.cancel_policy(policy_number, "Deleted by user")

    async def get_history(self, policy_number: str) -> List[Dict]:
        """Récupère l'historique d'une police."""
        async def _get_history():
            return [h for h in self.history if h["policy_number"] == policy_number]

        return await self.execute("get_history", _get_history)

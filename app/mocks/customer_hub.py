"""Service mock pour le référentiel clients."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import MockService


class CustomerHub(MockService):
    """
    Simule le référentiel client centralisé.

    Fonctionnalités:
    - CRUD complet sur les clients
    - Recherche et filtrage
    - Fusion de clients (MDM)
    """

    def __init__(self, initial_data: List[Dict] = None):
        super().__init__("Customer Hub", default_latency=25)
        self.customers: Dict[str, Dict] = {}

        # Charger les données initiales
        if initial_data:
            for customer in initial_data:
                self.customers[customer["id"]] = customer

    def _generate_customer_id(self) -> str:
        """Génère un ID client unique."""
        seq = len(self.customers) + 1
        return f"C{seq:04d}"

    async def create_customer(
        self,
        name: str,
        email: str,
        phone: str = None,
        address: dict = None,
        birth_date: str = None
    ) -> Dict[str, Any]:
        """
        Crée un nouveau client.

        Args:
            name: Nom complet
            email: Adresse email
            phone: Numéro de téléphone
            address: Adresse
            birth_date: Date de naissance

        Returns:
            Client créé
        """
        async def _create():
            # Vérifier l'unicité de l'email
            for c in self.customers.values():
                if c["email"].lower() == email.lower():
                    return {"error": True, "code": "DUPLICATE_EMAIL", "message": f"Email {email} already exists"}

            now = datetime.now()
            customer_id = self._generate_customer_id()

            customer = {
                "id": customer_id,
                "name": name,
                "email": email.lower(),
                "phone": phone,
                "address": address or {},
                "birth_date": birth_date,
                "status": "ACTIVE",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            self.customers[customer_id] = customer
            return customer

        return await self.execute("create_customer", _create)

    async def get_customer(self, customer_id: str) -> Optional[Dict]:
        """Récupère un client par son ID."""
        async def _get():
            customer = self.customers.get(customer_id)
            if not customer:
                return {"error": True, "code": "NOT_FOUND", "message": f"Customer {customer_id} not found"}
            return customer

        return await self.execute("get_customer", _get)

    async def list_customers(
        self,
        status: str = None,
        search: str = None
    ) -> List[Dict]:
        """
        Liste les clients avec filtres.

        Args:
            status: Filtre par statut (ACTIVE, INACTIVE)
            search: Recherche dans nom ou email

        Returns:
            Liste des clients
        """
        async def _list():
            result = list(self.customers.values())

            if status:
                result = [c for c in result if c["status"] == status.upper()]

            if search:
                search_lower = search.lower()
                result = [c for c in result
                         if search_lower in c["name"].lower()
                         or search_lower in c["email"].lower()]

            return result

        return await self.execute("list_customers", _list)

    async def update_customer(self, customer_id: str, **updates) -> Dict:
        """
        Met à jour un client.

        Args:
            customer_id: ID du client
            **updates: Champs à mettre à jour

        Returns:
            Client mis à jour
        """
        async def _update():
            customer = self.customers.get(customer_id)
            if not customer:
                return {"error": True, "code": "NOT_FOUND", "message": f"Customer {customer_id} not found"}

            # Vérifier unicité email si modifié
            if "email" in updates:
                new_email = updates["email"].lower()
                for c in self.customers.values():
                    if c["id"] != customer_id and c["email"].lower() == new_email:
                        return {"error": True, "code": "DUPLICATE_EMAIL", "message": f"Email {new_email} already exists"}
                updates["email"] = new_email

            # Champs modifiables
            allowed = ["name", "email", "phone", "address", "birth_date", "status"]
            for key, value in updates.items():
                if key in allowed:
                    customer[key] = value

            customer["updated_at"] = datetime.now().isoformat()
            return customer

        return await self.execute("update_customer", _update)

    async def delete_customer(self, customer_id: str) -> Dict:
        """Désactive un client (soft delete)."""
        async def _delete():
            customer = self.customers.get(customer_id)
            if not customer:
                return {"error": True, "code": "NOT_FOUND", "message": f"Customer {customer_id} not found"}

            customer["status"] = "INACTIVE"
            customer["deactivated_at"] = datetime.now().isoformat()
            customer["updated_at"] = datetime.now().isoformat()
            return {"success": True, "customer_id": customer_id}

        return await self.execute("delete_customer", _delete)

    async def get_customer_by_email(self, email: str) -> Optional[Dict]:
        """Recherche un client par email."""
        async def _get():
            email_lower = email.lower()
            for customer in self.customers.values():
                if customer["email"].lower() == email_lower:
                    return customer
            return {"error": True, "code": "NOT_FOUND", "message": f"No customer with email {email}"}

        return await self.execute("get_customer_by_email", _get)

    async def merge_customers(self, primary_id: str, secondary_id: str) -> Dict:
        """
        Fusionne deux clients (golden record MDM).

        Args:
            primary_id: ID du client principal (sera conservé)
            secondary_id: ID du client secondaire (sera fusionné)

        Returns:
            Client fusionné
        """
        async def _merge():
            primary = self.customers.get(primary_id)
            secondary = self.customers.get(secondary_id)

            if not primary:
                return {"error": True, "code": "NOT_FOUND", "message": f"Primary customer {primary_id} not found"}
            if not secondary:
                return {"error": True, "code": "NOT_FOUND", "message": f"Secondary customer {secondary_id} not found"}

            # Fusionner les données (garder primary, compléter avec secondary)
            if not primary.get("phone") and secondary.get("phone"):
                primary["phone"] = secondary["phone"]

            if not primary.get("address") and secondary.get("address"):
                primary["address"] = secondary["address"]

            # Marquer le secondaire comme fusionné
            secondary["status"] = "MERGED"
            secondary["merged_into"] = primary_id
            secondary["merged_at"] = datetime.now().isoformat()

            primary["updated_at"] = datetime.now().isoformat()
            primary["merged_from"] = primary.get("merged_from", []) + [secondary_id]

            return primary

        return await self.execute("merge_customers", _merge)

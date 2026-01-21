"""Service mock pour le système de facturation."""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .base import MockService


class BillingSystem(MockService):
    """
    Simule le système de facturation des primes d'assurance.

    Fonctionnalités:
    - Génération de factures
    - Suivi des paiements
    - Gestion des échéances
    """

    def __init__(self, initial_data: List[Dict] = None):
        super().__init__("Billing System", default_latency=35)
        self.invoices: Dict[str, Dict] = {}

        # Charger les données initiales
        if initial_data:
            for invoice in initial_data:
                self.invoices[invoice["number"]] = invoice

    def _generate_invoice_number(self) -> str:
        """Génère un numéro de facture unique."""
        year = datetime.now().year
        seq = len(self.invoices) + 1
        return f"INV-{year}-{seq:04d}"

    def _update_overdue_status(self, invoice: dict):
        """Met à jour le statut si la facture est en retard."""
        if invoice["status"] == "PENDING":
            due_date = datetime.fromisoformat(invoice["due_date"])
            if datetime.now() > due_date:
                invoice["status"] = "OVERDUE"

    async def create_invoice(
        self,
        policy_number: str,
        amount: float,
        due_date: str = None,
        description: str = None
    ) -> Dict[str, Any]:
        """
        Crée une nouvelle facture.

        Args:
            policy_number: Numéro de la police
            amount: Montant de la facture
            due_date: Date d'échéance
            description: Description

        Returns:
            Facture créée
        """
        async def _create():
            now = datetime.now()
            invoice_number = self._generate_invoice_number()

            invoice = {
                "number": invoice_number,
                "policy_number": policy_number,
                "amount": amount,
                "amount_paid": 0.0,
                "status": "PENDING",
                "due_date": due_date or (now + timedelta(days=30)).isoformat(),
                "description": description or "Prime d'assurance",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "payments": []
            }

            self.invoices[invoice_number] = invoice
            return invoice

        return await self.execute("create_invoice", _create)

    async def get_invoice(self, invoice_number: str) -> Optional[Dict]:
        """Récupère une facture par son numéro."""
        async def _get():
            invoice = self.invoices.get(invoice_number)
            if not invoice:
                return {"error": True, "code": "NOT_FOUND", "message": f"Invoice {invoice_number} not found"}

            self._update_overdue_status(invoice)
            return invoice

        return await self.execute("get_invoice", _get)

    async def list_invoices(
        self,
        policy_number: str = None,
        status: str = None
    ) -> List[Dict]:
        """Liste les factures avec filtres optionnels."""
        async def _list():
            result = list(self.invoices.values())

            if policy_number:
                result = [i for i in result if i["policy_number"] == policy_number]

            if status:
                result = [i for i in result if i["status"] == status.upper()]

            # Mettre à jour les statuts de retard
            for invoice in result:
                self._update_overdue_status(invoice)

            return result

        return await self.execute("list_invoices", _list)

    async def record_payment(
        self,
        invoice_number: str,
        amount: float,
        payment_method: str = "VIREMENT",
        reference: str = None
    ) -> Dict:
        """
        Enregistre un paiement sur une facture.

        Args:
            invoice_number: Numéro de la facture
            amount: Montant payé
            payment_method: Mode de paiement
            reference: Référence du paiement

        Returns:
            Facture mise à jour
        """
        async def _pay():
            invoice = self.invoices.get(invoice_number)
            if not invoice:
                return {"error": True, "code": "NOT_FOUND", "message": f"Invoice {invoice_number} not found"}

            if invoice["status"] == "PAID":
                return {"error": True, "code": "ALREADY_PAID", "message": "Invoice already paid"}

            now = datetime.now()
            payment = {
                "amount": amount,
                "method": payment_method,
                "reference": reference or f"PAY-{len(invoice['payments']) + 1:04d}",
                "date": now.isoformat()
            }

            invoice["payments"].append(payment)
            invoice["amount_paid"] += amount
            invoice["updated_at"] = now.isoformat()

            # Vérifier si complètement payée
            if invoice["amount_paid"] >= invoice["amount"]:
                invoice["status"] = "PAID"
                invoice["paid_at"] = now.isoformat()
            elif invoice["amount_paid"] > 0:
                invoice["status"] = "PARTIAL"

            return invoice

        return await self.execute("record_payment", _pay)

    async def cancel_invoice(self, invoice_number: str, reason: str = None) -> Dict:
        """Annule une facture."""
        async def _cancel():
            invoice = self.invoices.get(invoice_number)
            if not invoice:
                return {"error": True, "code": "NOT_FOUND", "message": f"Invoice {invoice_number} not found"}

            if invoice["status"] == "PAID":
                return {"error": True, "code": "CANNOT_CANCEL", "message": "Cannot cancel paid invoice"}

            invoice["status"] = "CANCELLED"
            invoice["cancellation_reason"] = reason
            invoice["cancelled_at"] = datetime.now().isoformat()
            invoice["updated_at"] = datetime.now().isoformat()
            return invoice

        return await self.execute("cancel_invoice", _cancel)

    async def generate_policy_invoices(
        self,
        policy_number: str,
        premium: float,
        frequency: str = "ANNUAL"
    ) -> List[Dict]:
        """
        Génère les factures pour une police selon la fréquence.

        Args:
            policy_number: Numéro de la police
            premium: Prime annuelle
            frequency: Fréquence (ANNUAL, SEMI, QUARTERLY, MONTHLY)

        Returns:
            Liste des factures générées
        """
        async def _generate():
            frequencies = {
                "ANNUAL": (1, 12),
                "SEMI": (2, 6),
                "QUARTERLY": (4, 3),
                "MONTHLY": (12, 1)
            }

            if frequency.upper() not in frequencies:
                return {"error": True, "code": "INVALID_FREQUENCY", "message": f"Invalid frequency: {frequency}"}

            num_invoices, months_interval = frequencies[frequency.upper()]
            amount_per_invoice = round(premium / num_invoices, 2)

            invoices = []
            now = datetime.now()

            for i in range(num_invoices):
                due_date = now + timedelta(days=30 + (i * months_interval * 30))
                invoice_number = self._generate_invoice_number()

                invoice = {
                    "number": invoice_number,
                    "policy_number": policy_number,
                    "amount": amount_per_invoice,
                    "amount_paid": 0.0,
                    "status": "PENDING",
                    "due_date": due_date.isoformat(),
                    "description": f"Prime {frequency} - Échéance {i + 1}/{num_invoices}",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "payments": []
                }
                self.invoices[invoice_number] = invoice
                invoices.append(invoice)

            return invoices

        return await self.execute("generate_policy_invoices", _generate)

    async def get_outstanding_balance(self, policy_number: str) -> Dict:
        """Calcule le solde restant dû pour une police."""
        async def _balance():
            invoices = [i for i in self.invoices.values() if i["policy_number"] == policy_number]

            total_due = sum(i["amount"] for i in invoices if i["status"] not in ["PAID", "CANCELLED"])
            total_paid = sum(i["amount_paid"] for i in invoices)

            return {
                "policy_number": policy_number,
                "total_invoiced": sum(i["amount"] for i in invoices if i["status"] != "CANCELLED"),
                "total_paid": total_paid,
                "outstanding_balance": total_due - total_paid,
                "invoices_count": len(invoices)
            }

        return await self.execute("get_outstanding_balance", _balance)

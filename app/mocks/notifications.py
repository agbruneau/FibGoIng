"""Service mock pour les notifications multi-canal."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from .base import MockService


class NotificationChannel(Enum):
    """Canaux de notification disponibles."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    LETTER = "letter"


class NotificationService(MockService):
    """
    Simule le service de notifications multi-canal.

    Fonctionnalités:
    - Envoi email, SMS, push, courrier
    - Templates de notifications
    - Suivi des envois
    """

    # Templates de notifications prédéfinis
    TEMPLATES = {
        "POLICY_CREATED": {
            "subject": "Votre police d'assurance a été créée",
            "body": "Bonjour {customer_name}, votre police {policy_number} est maintenant active."
        },
        "POLICY_RENEWED": {
            "subject": "Renouvellement de votre police",
            "body": "Votre police {policy_number} a été renouvelée jusqu'au {end_date}."
        },
        "CLAIM_OPENED": {
            "subject": "Déclaration de sinistre enregistrée",
            "body": "Votre déclaration {claim_number} a été enregistrée. Nous la traitons dans les plus brefs délais."
        },
        "CLAIM_SETTLED": {
            "subject": "Règlement de votre sinistre",
            "body": "Votre sinistre {claim_number} a été réglé. Montant: {amount}€"
        },
        "INVOICE_CREATED": {
            "subject": "Nouvelle facture disponible",
            "body": "Une facture de {amount}€ est disponible. Échéance: {due_date}"
        },
        "PAYMENT_RECEIVED": {
            "subject": "Paiement reçu",
            "body": "Nous avons bien reçu votre paiement de {amount}€. Merci!"
        },
        "PAYMENT_REMINDER": {
            "subject": "Rappel de paiement",
            "body": "Votre facture {invoice_number} arrive à échéance le {due_date}."
        },
    }

    def __init__(self, initial_data: List[Dict] = None):
        super().__init__("Notification Service", default_latency=20)
        self.notifications: Dict[str, Dict] = {}

        # Charger les données initiales
        if initial_data:
            for notif in initial_data:
                self.notifications[notif["id"]] = notif

    def _generate_notification_id(self) -> str:
        """Génère un ID de notification unique."""
        seq = len(self.notifications) + 1
        return f"NOTIF-{seq:04d}"

    async def send_notification(
        self,
        recipient: str,
        channel: str,
        template: str = None,
        subject: str = None,
        body: str = None,
        data: dict = None
    ) -> Dict[str, Any]:
        """
        Envoie une notification.

        Args:
            recipient: Destinataire (email, numéro, device_id)
            channel: Canal (email, sms, push, letter)
            template: ID du template (optionnel)
            subject: Sujet (si pas de template)
            body: Corps (si pas de template)
            data: Données pour remplir le template

        Returns:
            Notification envoyée
        """
        async def _send():
            # Valider le canal
            try:
                NotificationChannel(channel.lower())
            except ValueError:
                return {"error": True, "code": "INVALID_CHANNEL", "message": f"Invalid channel: {channel}"}

            # Résoudre le template ou utiliser subject/body
            final_subject = subject
            final_body = body

            if template:
                if template.upper() not in self.TEMPLATES:
                    return {"error": True, "code": "UNKNOWN_TEMPLATE", "message": f"Unknown template: {template}"}

                tpl = self.TEMPLATES[template.upper()]
                final_subject = tpl["subject"]
                final_body = tpl["body"]

                # Remplacer les placeholders
                if data:
                    for key, value in data.items():
                        final_subject = final_subject.replace(f"{{{key}}}", str(value))
                        final_body = final_body.replace(f"{{{key}}}", str(value))

            if not final_subject or not final_body:
                return {"error": True, "code": "MISSING_CONTENT", "message": "Subject and body are required"}

            now = datetime.now()
            notif_id = self._generate_notification_id()

            notification = {
                "id": notif_id,
                "recipient": recipient,
                "channel": channel.lower(),
                "template": template,
                "subject": final_subject,
                "body": final_body,
                "data": data or {},
                "status": "SENT",
                "sent_at": now.isoformat(),
                "created_at": now.isoformat(),
            }

            self.notifications[notif_id] = notification
            return notification

        return await self.execute("send_notification", _send)

    async def send_email(
        self,
        email: str,
        subject: str,
        body: str,
        template: str = None,
        data: dict = None
    ) -> Dict:
        """Raccourci pour envoyer un email."""
        return await self.send_notification(
            recipient=email,
            channel="email",
            template=template,
            subject=subject,
            body=body,
            data=data
        )

    async def send_sms(
        self,
        phone: str,
        body: str,
        template: str = None,
        data: dict = None
    ) -> Dict:
        """Raccourci pour envoyer un SMS."""
        return await self.send_notification(
            recipient=phone,
            channel="sms",
            template=template,
            subject="SMS",
            body=body,
            data=data
        )

    async def get_notification(self, notification_id: str) -> Optional[Dict]:
        """Récupère une notification par son ID."""
        async def _get():
            notif = self.notifications.get(notification_id)
            if not notif:
                return {"error": True, "code": "NOT_FOUND", "message": f"Notification {notification_id} not found"}
            return notif

        return await self.execute("get_notification", _get)

    async def list_notifications(
        self,
        recipient: str = None,
        channel: str = None,
        status: str = None
    ) -> List[Dict]:
        """Liste les notifications avec filtres."""
        async def _list():
            result = list(self.notifications.values())

            if recipient:
                result = [n for n in result if n["recipient"] == recipient]

            if channel:
                result = [n for n in result if n["channel"] == channel.lower()]

            if status:
                result = [n for n in result if n["status"] == status.upper()]

            return result

        return await self.execute("list_notifications", _list)

    async def get_templates(self) -> Dict:
        """Retourne la liste des templates disponibles."""
        async def _templates():
            return self.TEMPLATES

        return await self.execute("get_templates", _templates)

    async def bulk_send(
        self,
        recipients: List[str],
        channel: str,
        template: str,
        data: dict = None
    ) -> List[Dict]:
        """Envoie une notification à plusieurs destinataires."""
        async def _bulk():
            notifications = []
            for recipient in recipients:
                notif = await self.send_notification(
                    recipient=recipient,
                    channel=channel,
                    template=template,
                    data=data
                )
                notifications.append(notif)
            return notifications

        return await self.execute("bulk_send", _bulk)

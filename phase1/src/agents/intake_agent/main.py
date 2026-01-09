#!/usr/bin/env python3
"""
Phase 1 - Intake Agent avec Kafka
==================================
Agent de validation qui publie dans Kafka.
"""

import os
import uuid
from datetime import datetime
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv

from src.shared.kafka_client import KafkaProducerClient
from src.shared.models import LoanApplication, EmploymentStatus
from src.shared.prompts import INTAKE_AGENT_SYSTEM_PROMPT

load_dotenv()


class IntakeAgent:
    """
    Agent Intake - Le Contrôleur
    
    Valide les demandes et publie dans Kafka.
    """
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-haiku-20241022"
        self.producer = KafkaProducerClient(topic="finance.loan.application.v1")
        print("✅ Intake Agent initialisé")
    
    def validate_request(self, raw_data: dict[str, Any]) -> LoanApplication | None:
        """Valide et normalise une demande de prêt brute."""
        try:
            application = LoanApplication(
                application_id=raw_data.get("application_id", str(uuid.uuid4())),
                applicant_id=raw_data["applicant_id"],
                amount_requested=float(raw_data["amount_requested"]),
                currency=raw_data.get("currency", "USD"),
                declared_monthly_income=float(raw_data["declared_monthly_income"]),
                employment_status=EmploymentStatus(raw_data["employment_status"]),
                existing_debts=float(raw_data.get("existing_debts", 0.0)),
                loan_purpose=raw_data.get("loan_purpose"),
            )
            
            # Validation sémantique via LLM
            if not self._semantic_validation(application):
                return None
            
            return application
            
        except Exception as e:
            print(f"❌ Erreur de validation: {e}")
            return None
    
    def _semantic_validation(self, application: LoanApplication) -> bool:
        """Validation sémantique via LLM."""
        prompt = f"""{INTAKE_AGENT_SYSTEM_PROMPT}

Valide cette demande de prêt:
- Montant demandé: {application.amount_requested} {application.currency}
- Revenu mensuel: {application.declared_monthly_income}
- Statut emploi: {application.employment_status.value}
- Dettes existantes: {application.existing_debts}

Réponds UNIQUEMENT par JSON: {{"is_valid": true/false, "reason": "..."}}"""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            response_text = message.content[0].text
            result = json.loads(response_text)
            
            if not result.get("is_valid", False):
                print(f"⚠️ Validation échouée: {result.get('reason', 'Raison inconnue')}")
                return False
            
            return True
        except Exception as e:
            print(f"⚠️ Erreur validation sémantique: {e}")
            return True
    
    def process_and_publish(self, raw_data: dict[str, Any]) -> bool:
        """Traite une demande et publie dans Kafka si valide."""
        application = self.validate_request(raw_data)
        
        if application is None:
            print("❌ Demande rejetée, non publiée")
            return False
        
        # Publier dans Kafka
        success = self.producer.produce(
            key=application.application_id,
            value=application.model_dump(),
        )
        
        if success:
            print(f"✅ Application publiée: {application.application_id}")
        
        return success
    
    def run(self):
        """Boucle principale - consomme depuis une source externe."""
        print("🚀 Intake Agent démarré - En attente de demandes...")
        print("💡 Pour tester, utilisez: python scripts/send_test_request.py")
        
        # Pour cette phase, on attend des demandes manuelles
        # En production, cela pourrait être une API REST ou un autre consumer
        try:
            while True:
                import time
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n🛑 Arrêt de l'Intake Agent...")
        finally:
            self.close()
    
    def close(self):
        """Ferme les connexions."""
        self.producer.close()


def main():
    """Point d'entrée CLI."""
    agent = IntakeAgent()
    agent.run()


if __name__ == "__main__":
    main()

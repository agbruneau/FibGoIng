"""
Phase 0 - Agent Intake
=======================
Agent de validation et normalisation des demandes de prêt.
Version simplifiée sans Kafka.
"""

import os
import uuid
from typing import Any, Optional

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from ..models import LoanApplication, EmploymentStatus

load_dotenv()


class IntakeAgent:
    """
    Agent Intake - Le Contrôleur
    
    Responsabilités:
    - Valider la structure des demandes entrantes
    - Normaliser les montants en USD
    - Rejeter les demandes incomplètes ou incohérentes
    """
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-haiku-20241022"
    
    def process(self, raw_data: dict[str, Any]) -> Optional[LoanApplication]:
        """
        Valide et normalise une demande de prêt brute.
        
        Args:
            raw_data: Données brutes de la demande
            
        Returns:
            LoanApplication validé ou None si invalide
        """
        try:
            # Validation structurelle via Pydantic
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
            
            # Validation sémantique via LLM (vérifications logiques)
            if not self._semantic_validation(application):
                return None
            
            print(f"✅ Demande validée: {application.application_id}")
            return application
            
        except ValidationError as e:
            print(f"❌ Erreur de validation: {e}")
            return None
        except KeyError as e:
            print(f"❌ Champ manquant: {e}")
            return None
    
    def _semantic_validation(self, application: LoanApplication) -> bool:
        """Validation sémantique via LLM."""
        prompt = f"""Valide cette demande de prêt:
- Montant demandé: {application.amount_requested} {application.currency}
- Revenu mensuel: {application.declared_monthly_income}
- Statut emploi: {application.employment_status.value}
- Dettes existantes: {application.existing_debts}

Règles:
- Rejette si montant > 10x revenu mensuel (anomalie évidente)
- Rejette si revenu <= 0

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
                print(f"⚠️ Validation sémantique échouée: {result.get('reason', 'Raison inconnue')}")
                return False
            
            return True
        except Exception as e:
            print(f"⚠️ Erreur lors de la validation sémantique: {e}")
            # Par défaut, on accepte si la validation structurelle passe
            return True

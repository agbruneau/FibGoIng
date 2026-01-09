#!/usr/bin/env python3
"""
Intake Agent - Point d'entrée principal
========================================
Agent de validation et normalisation des demandes de prêt.

Usage:
    python -m src.agents.intake_agent.main
"""

import os
import uuid
from datetime import datetime
from typing import Any

import structlog
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError

from src.shared.kafka_client import KafkaProducerClient
from src.shared.models import LoanApplication, EmploymentStatus
from src.shared.prompts import INTAKE_AGENT_SYSTEM_PROMPT

load_dotenv()
logger = structlog.get_logger()


class IntakeAgent:
    """
    Agent Intake - Le Contrôleur
    
    Responsabilités:
    - Valider la structure des demandes entrantes
    - Normaliser les montants en USD
    - Rejeter les demandes incomplètes ou incohérentes
    
    Ne fait PAS d'évaluation de risque (ce n'est pas son rôle).
    """
    
    def __init__(self):
        self.model = ChatAnthropic(
            model=os.getenv("INTAKE_AGENT_MODEL", "claude-3-5-haiku-20241022"),
            temperature=float(os.getenv("INTAKE_AGENT_TEMPERATURE", "0.0")),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        self.producer = KafkaProducerClient(
            topic="finance.loan.application.v1",
            schema_subject="finance.loan.application.v1-value",
        )
        self.agent_id = "agent-intake-service"
        logger.info("IntakeAgent initialized", agent_id=self.agent_id)
    
    def validate_request(self, raw_data: dict[str, Any]) -> LoanApplication | None:
        """
        Valide et normalise une demande de prêt brute.
        
        Args:
            raw_data: Données brutes de la demande
            
        Returns:
            LoanApplication validé ou None si invalide
        """
        logger.info("Validating loan request", data=raw_data)
        
        try:
            # Validation structurelle via Pydantic
            application = LoanApplication(
                application_id=raw_data.get("application_id", str(uuid.uuid4())),
                timestamp=int(datetime.now().timestamp() * 1000),
                applicant_id=raw_data["applicant_id"],
                amount_requested=float(raw_data["amount_requested"]),
                currency=raw_data.get("currency", "USD"),
                declared_monthly_income=float(raw_data["declared_monthly_income"]),
                employment_status=EmploymentStatus(raw_data["employment_status"]),
                existing_debts=float(raw_data.get("existing_debts", 0.0)),
                loan_purpose=raw_data.get("loan_purpose"),
                metadata={"source": "intake_agent", "trace_id": str(uuid.uuid4())},
            )
            
            # Validation sémantique via LLM (vérifications logiques)
            validation_result = self._semantic_validation(application)
            
            if not validation_result["is_valid"]:
                logger.warning(
                    "Semantic validation failed",
                    reason=validation_result["reason"],
                    application_id=application.application_id,
                )
                return None
            
            logger.info(
                "Loan request validated",
                application_id=application.application_id,
            )
            return application
            
        except ValidationError as e:
            logger.error("Structural validation failed", errors=e.errors())
            return None
        except KeyError as e:
            logger.error("Missing required field", field=str(e))
            return None
    
    def _semantic_validation(self, application: LoanApplication) -> dict:
        """Validation sémantique via LLM."""
        messages = [
            SystemMessage(content=INTAKE_AGENT_SYSTEM_PROMPT),
            HumanMessage(content=f"""
Valide cette demande de prêt:
- Montant demandé: {application.amount_requested} {application.currency}
- Revenu mensuel: {application.declared_monthly_income}
- Statut emploi: {application.employment_status.value}
- Dettes existantes: {application.existing_debts}

Réponds UNIQUEMENT par JSON: {{"is_valid": true/false, "reason": "..."}}
"""),
        ]
        
        response = self.model.invoke(messages)
        
        # Parse la réponse (simplifié pour le squelette)
        # En production, utiliser un output parser LangChain
        try:
            import json
            return json.loads(response.content)
        except:
            return {"is_valid": True, "reason": "Default pass"}
    
    def process_and_publish(self, raw_data: dict[str, Any]) -> bool:
        """
        Traite une demande et publie dans Kafka si valide.
        
        Args:
            raw_data: Données brutes de la demande
            
        Returns:
            True si publié avec succès, False sinon
        """
        application = self.validate_request(raw_data)
        
        if application is None:
            logger.warning("Request rejected, not publishing")
            return False
        
        # Publier dans Kafka
        success = self.producer.produce(
            key=application.application_id,
            value=application.model_dump(),
        )
        
        if success:
            logger.info(
                "Application published to Kafka",
                application_id=application.application_id,
                topic="finance.loan.application.v1",
            )
        
        return success
    
    def close(self):
        """Ferme les connexions."""
        self.producer.close()


def main():
    """Point d'entrée CLI."""
    logger.info("Starting Intake Agent...")
    
    agent = IntakeAgent()
    
    # Exemple de traitement (en production: API REST ou Consumer)
    sample_request = {
        "applicant_id": "CUST-12345",
        "amount_requested": 50000,
        "currency": "USD",
        "declared_monthly_income": 5000,
        "employment_status": "FULL_TIME",
        "existing_debts": 10000,
        "loan_purpose": "Home renovation",
    }
    
    success = agent.process_and_publish(sample_request)
    logger.info("Processing complete", success=success)
    
    agent.close()


if __name__ == "__main__":
    main()

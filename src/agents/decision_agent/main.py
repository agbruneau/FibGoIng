#!/usr/bin/env python3
"""
Decision Agent - Point d'entrée principal
==========================================
Agent de décision finale pour les demandes de prêt.

Usage:
    python -m src.agents.decision_agent.main
"""

import os
import uuid
from datetime import datetime

import structlog
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.shared.kafka_client import KafkaConsumerClient, KafkaProducerClient
from src.shared.models import RiskAssessment, LoanDecision, DecisionStatus
from src.shared.prompts import DECISION_AGENT_SYSTEM_PROMPT

load_dotenv()
logger = structlog.get_logger()


class DecisionAgent:
    """
    Agent Loan Officer - Le Décideur Final
    
    Critères de décision (voir docs/03-AgentSpecs.md):
    - Risk Score < 20: APPROBATION AUTOMATIQUE
    - Risk Score > 80: REJET AUTOMATIQUE
    - Entre 20 et 80: Analyse de la rationale
    
    Pour les transactions à haut risque, génère MANUAL_REVIEW_REQUIRED.
    """
    
    # Seuils de décision (configurable)
    THRESHOLD_AUTO_APPROVE = 20
    THRESHOLD_AUTO_REJECT = 80
    THRESHOLD_HIGH_VALUE = 100000  # Montant nécessitant revue humaine
    
    def __init__(self):
        self.model = ChatAnthropic(
            model=os.getenv("DECISION_AGENT_MODEL", "claude-3-5-sonnet-20241022"),
            temperature=float(os.getenv("DECISION_AGENT_TEMPERATURE", "0.1")),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        
        self.consumer = KafkaConsumerClient(
            topic="risk.scoring.result.v1",
            group_id=os.getenv("DECISION_CONSUMER_GROUP", "agent-loan-officer"),
        )
        
        self.producer = KafkaProducerClient(
            topic="finance.loan.decision.v1",
            schema_subject="finance.loan.decision.v1-value",
        )
        
        self.agent_id = "agent-loan-officer"
        logger.info("DecisionAgent initialized", agent_id=self.agent_id)
    
    # -------------------------------------------------------------------------
    # Outils (Tools) - Voir docs/03-AgentSpecs.md Section 4.2
    # -------------------------------------------------------------------------
    
    def tool_check_bank_liquidity(self, amount: float) -> bool:
        """
        Vérifie si la banque a les fonds disponibles (simulé).
        
        Args:
            amount: Montant du prêt
            
        Returns:
            True si fonds disponibles
        """
        # TODO: Connecter au système bancaire réel
        logger.info("Checking bank liquidity", amount=amount)
        return amount < 500000  # Simulation: approuve jusqu'à 500k
    
    # -------------------------------------------------------------------------
    # Logique de décision
    # -------------------------------------------------------------------------
    
    def make_decision(self, assessment: RiskAssessment) -> LoanDecision:
        """
        Prend la décision finale basée sur l'évaluation de risque.
        
        Implémente les règles définies dans docs/03-AgentSpecs.md.
        """
        logger.info(
            "Making decision",
            application_id=assessment.application_id,
            risk_score=assessment.risk_score,
        )
        
        # Initialisation
        status = DecisionStatus.MANUAL_REVIEW_REQUIRED
        approved_amount = None
        interest_rate = None
        rejection_reasons = []
        requires_human = False
        
        # Règle 1: Approbation automatique pour risque très faible
        if assessment.risk_score < self.THRESHOLD_AUTO_APPROVE:
            status = DecisionStatus.APPROVED
            approved_amount = self._calculate_approved_amount(assessment)
            interest_rate = self._calculate_interest_rate(assessment.risk_score)
            
        # Règle 2: Rejet automatique pour risque critique
        elif assessment.risk_score > self.THRESHOLD_AUTO_REJECT:
            status = DecisionStatus.REJECTED
            rejection_reasons = self._determine_rejection_reasons(assessment)
            
        # Règle 3: Zone grise - analyse détaillée
        else:
            decision = self._analyze_gray_zone(assessment)
            status = decision["status"]
            approved_amount = decision.get("approved_amount")
            interest_rate = decision.get("interest_rate")
            rejection_reasons = decision.get("rejection_reasons", [])
            requires_human = decision.get("requires_human", False)
        
        # Générer la justification
        rationale = self._generate_decision_rationale(
            assessment, status, rejection_reasons
        )
        
        decision = LoanDecision(
            application_id=assessment.application_id,
            decision_id=str(uuid.uuid4()),
            assessment_id=assessment.assessment_id,
            decision_timestamp=int(datetime.now().timestamp() * 1000),
            status=status,
            approved_amount=approved_amount,
            interest_rate=interest_rate,
            decision_rationale=rationale,
            rejection_reasons=rejection_reasons,
            risk_score_at_decision=assessment.risk_score,
            decided_by=self.agent_id,
            requires_human_approval=requires_human,
        )
        
        logger.info(
            "Decision made",
            application_id=assessment.application_id,
            status=status.value,
            approved_amount=approved_amount,
        )
        
        return decision
    
    def _calculate_approved_amount(self, assessment: RiskAssessment) -> float:
        """Calcule le montant approuvé (peut être inférieur au demandé)."""
        # Pour l'instant, approuve le montant total si risque faible
        # TODO: Récupérer amount_requested depuis l'application originale
        return 50000.0  # Placeholder
    
    def _calculate_interest_rate(self, risk_score: int) -> float:
        """Calcule le taux d'intérêt basé sur le risque."""
        base_rate = 5.0
        risk_premium = (risk_score / 100) * 10  # 0-10% de prime de risque
        return round(base_rate + risk_premium, 2)
    
    def _determine_rejection_reasons(self, assessment: RiskAssessment) -> list[str]:
        """Détermine les raisons de rejet."""
        reasons = []
        
        if assessment.risk_score > 80:
            reasons.append("Score de risque trop élevé")
        
        if assessment.debt_to_income_ratio > 50:
            reasons.append(f"Ratio dette/revenu excessif ({assessment.debt_to_income_ratio}%)")
        
        if assessment.risk_category.value == "CRITICAL":
            reasons.append("Catégorie de risque critique")
        
        return reasons or ["Évaluation globale défavorable"]
    
    def _analyze_gray_zone(self, assessment: RiskAssessment) -> dict:
        """
        Analyse détaillée pour les cas en zone grise (score 20-80).
        
        Utilise le LLM pour interpréter la rationale de l'analyste risque.
        """
        messages = [
            SystemMessage(content=DECISION_AGENT_SYSTEM_PROMPT),
            HumanMessage(content=f"""
Analyse cette évaluation de risque et décide:

Score de risque: {assessment.risk_score}/100
Catégorie: {assessment.risk_category.value}
DTI: {assessment.debt_to_income_ratio}%
Justification analyste: {assessment.rationale}
Politiques vérifiées: {', '.join(assessment.checked_policies)}

Réponds en JSON:
{{
  "decision": "APPROVED" ou "REJECTED" ou "MANUAL_REVIEW_REQUIRED",
  "confidence": 0.0-1.0,
  "key_factor": "raison principale"
}}
"""),
        ]
        
        response = self.model.invoke(messages)
        
        # Parse la réponse (simplifié)
        try:
            import json
            result = json.loads(response.content)
            
            status_map = {
                "APPROVED": DecisionStatus.APPROVED,
                "REJECTED": DecisionStatus.REJECTED,
                "MANUAL_REVIEW_REQUIRED": DecisionStatus.MANUAL_REVIEW_REQUIRED,
            }
            
            status = status_map.get(result["decision"], DecisionStatus.MANUAL_REVIEW_REQUIRED)
            
            return {
                "status": status,
                "approved_amount": 50000.0 if status == DecisionStatus.APPROVED else None,
                "interest_rate": self._calculate_interest_rate(assessment.risk_score) if status == DecisionStatus.APPROVED else None,
                "rejection_reasons": [result.get("key_factor", "")] if status == DecisionStatus.REJECTED else [],
                "requires_human": status == DecisionStatus.MANUAL_REVIEW_REQUIRED,
            }
        except:
            # Par défaut: revue humaine
            return {
                "status": DecisionStatus.MANUAL_REVIEW_REQUIRED,
                "requires_human": True,
            }
    
    def _generate_decision_rationale(
        self, 
        assessment: RiskAssessment, 
        status: DecisionStatus,
        rejection_reasons: list[str]
    ) -> str:
        """Génère une explication de la décision pour le client."""
        if status == DecisionStatus.APPROVED:
            return f"Votre demande de prêt a été approuvée. Score de risque: {assessment.risk_score}/100."
        elif status == DecisionStatus.REJECTED:
            reasons = "; ".join(rejection_reasons)
            return f"Nous regrettons de vous informer que votre demande n'a pas été retenue. Raisons: {reasons}"
        else:
            return "Votre demande nécessite une analyse complémentaire par nos équipes. Nous vous contacterons sous 48h."
    
    def run(self):
        """Boucle principale de consommation Kafka."""
        logger.info("Starting Decision Agent consumer loop...")
        
        try:
            for message in self.consumer.consume():
                if message is None:
                    continue
                
                try:
                    # Désérialiser l'évaluation
                    assessment = RiskAssessment(**message.value())
                    
                    # Prendre la décision
                    decision = self.make_decision(assessment)
                    
                    # Publier la décision
                    self.producer.produce(
                        key=decision.application_id,
                        value=decision.model_dump(),
                    )
                    
                except Exception as e:
                    logger.error("Error processing message", error=str(e))
                    # TODO: Publier dans Dead Letter Queue
                    
        except KeyboardInterrupt:
            logger.info("Shutting down Decision Agent...")
        finally:
            self.close()
    
    def close(self):
        """Ferme les connexions."""
        self.consumer.close()
        self.producer.close()


def main():
    """Point d'entrée CLI."""
    agent = DecisionAgent()
    agent.run()


if __name__ == "__main__":
    main()

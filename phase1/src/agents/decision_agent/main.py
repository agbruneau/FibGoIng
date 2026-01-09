#!/usr/bin/env python3
"""
Phase 1 - Decision Agent avec Kafka
====================================
Agent de décision finale qui consomme et produit dans Kafka.
"""

import os
import uuid
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

from src.shared.kafka_client import KafkaConsumerClient, KafkaProducerClient
from src.shared.models import RiskAssessment, LoanDecision, DecisionStatus
from src.shared.prompts import DECISION_AGENT_SYSTEM_PROMPT

load_dotenv()


class DecisionAgent:
    """
    Agent Loan Officer - Le Décideur Final
    
    Consomme les évaluations de risque et produit les décisions finales.
    """
    
    THRESHOLD_AUTO_APPROVE = 20
    THRESHOLD_AUTO_REJECT = 80
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-20241022"
        
        self.consumer = KafkaConsumerClient(
            topic="risk.scoring.result.v1",
            group_id="agent-loan-officer",
        )
        
        self.producer = KafkaProducerClient(topic="finance.loan.decision.v1")
        print("✅ Decision Agent initialisé")
    
    def _calculate_interest_rate(self, risk_score: int) -> float:
        """Calcule le taux d'intérêt basé sur le risque."""
        base_rate = 5.0
        risk_premium = (risk_score / 100) * 10
        return round(base_rate + risk_premium, 2)
    
    def _analyze_gray_zone(self, assessment: RiskAssessment) -> dict:
        """Analyse détaillée pour les cas en zone grise."""
        prompt = f"""{DECISION_AGENT_SYSTEM_PROMPT}

Analyse cette évaluation de risque et décide:

Score de risque: {assessment.risk_score}/100
Catégorie: {assessment.risk_category.value}
DTI: {assessment.debt_to_income_ratio}%
Justification analyste: {assessment.rationale}

Réponds UNIQUEMENT en JSON:
{{"decision": "APPROVED" ou "REJECTED" ou "MANUAL_REVIEW_REQUIRED", "confidence": 0.0-1.0}}"""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            response_text = message.content[0].text
            result = json.loads(response_text)
            
            decision_str = result.get("decision", "MANUAL_REVIEW_REQUIRED")
            status_map = {
                "APPROVED": DecisionStatus.APPROVED,
                "REJECTED": DecisionStatus.REJECTED,
                "MANUAL_REVIEW_REQUIRED": DecisionStatus.MANUAL_REVIEW_REQUIRED,
            }
            
            status = status_map.get(decision_str, DecisionStatus.MANUAL_REVIEW_REQUIRED)
            
            return {
                "status": status,
                "approved_amount": 50000.0 if status == DecisionStatus.APPROVED else None,
                "interest_rate": self._calculate_interest_rate(assessment.risk_score) if status == DecisionStatus.APPROVED else None,
            }
        except Exception as e:
            print(f"⚠️ Erreur lors de l'analyse: {e}")
            return {"status": DecisionStatus.MANUAL_REVIEW_REQUIRED}
    
    def _generate_decision_rationale(
        self, 
        assessment: RiskAssessment, 
        status: DecisionStatus
    ) -> str:
        """Génère une explication de la décision."""
        if status == DecisionStatus.APPROVED:
            return f"Votre demande de prêt a été approuvée. Score de risque: {assessment.risk_score}/100."
        elif status == DecisionStatus.REJECTED:
            return f"Nous regrettons de vous informer que votre demande n'a pas été retenue. Score de risque: {assessment.risk_score}/100."
        else:
            return "Votre demande nécessite une analyse complémentaire par nos équipes. Nous vous contacterons sous 48h."
    
    def make_decision(self, assessment: RiskAssessment) -> LoanDecision:
        """Prend la décision finale basée sur l'évaluation de risque."""
        print(f"⚖️  Prise de décision pour: {assessment.application_id}")
        
        status = DecisionStatus.MANUAL_REVIEW_REQUIRED
        approved_amount = None
        interest_rate = None
        
        if assessment.risk_score < self.THRESHOLD_AUTO_APPROVE:
            status = DecisionStatus.APPROVED
            approved_amount = 50000.0
            interest_rate = self._calculate_interest_rate(assessment.risk_score)
        elif assessment.risk_score > self.THRESHOLD_AUTO_REJECT:
            status = DecisionStatus.REJECTED
        else:
            decision = self._analyze_gray_zone(assessment)
            status = decision["status"]
            approved_amount = decision.get("approved_amount")
            interest_rate = decision.get("interest_rate")
        
        rationale = self._generate_decision_rationale(assessment, status)
        
        decision = LoanDecision(
            application_id=assessment.application_id,
            decision_id=str(uuid.uuid4()),
            status=status,
            approved_amount=approved_amount,
            interest_rate=interest_rate,
            decision_rationale=rationale,
            risk_score_at_decision=assessment.risk_score,
        )
        
        status_emoji = "✅" if status == DecisionStatus.APPROVED else "❌" if status == DecisionStatus.REJECTED else "⚠️"
        print(f"{status_emoji} Décision: {status.value}")
        
        return decision
    
    def run(self):
        """Boucle principale de consommation Kafka."""
        print("🚀 Decision Agent démarré - En attente d'évaluations...")
        
        try:
            for message in self.consumer.consume():
                if message is None:
                    continue
                
                try:
                    assessment = RiskAssessment(**message.value())
                    decision = self.make_decision(assessment)
                    
                    self.producer.produce(
                        key=decision.application_id,
                        value=decision.model_dump(),
                    )
                    
                except Exception as e:
                    print(f"❌ Erreur de traitement: {e}")
                    
        except KeyboardInterrupt:
            print("\n🛑 Arrêt du Decision Agent...")
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

#!/usr/bin/env python3
"""
Phase 1 - Risk Agent avec Kafka
================================
Agent d'analyse de risque qui consomme et produit dans Kafka.
"""

import os
import uuid
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

from src.shared.kafka_client import KafkaConsumerClient, KafkaProducerClient
from src.shared.models import LoanApplication, RiskAssessment, RiskLevel
from src.shared.prompts import RISK_AGENT_SYSTEM_PROMPT

load_dotenv()


class RiskAgent:
    """
    Agent Risk Analyst - Le Cœur Cognitif
    
    Consomme les demandes validées et produit les évaluations de risque.
    """
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-20241022"
        
        self.consumer = KafkaConsumerClient(
            topic="finance.loan.application.v1",
            group_id="agent-risk-analyst",
        )
        
        self.producer = KafkaProducerClient(topic="risk.scoring.result.v1")
        print("✅ Risk Agent initialisé")
    
    def _calculate_debt_ratio(
        self, 
        income: float, 
        existing_debts: float, 
        new_loan_amount: float
    ) -> float:
        """Calcule le ratio dette/revenu (DTI)."""
        if income <= 0:
            return 100.0
        
        estimated_monthly_payment = new_loan_amount * 0.01
        total_monthly_debt = existing_debts + estimated_monthly_payment
        dti = (total_monthly_debt / income) * 100
        return round(dti, 2)
    
    def _fetch_credit_history(self, applicant_id: str) -> dict:
        """Récupère l'historique de crédit externe (simulé)."""
        return {
            "credit_score": 720,
            "accounts_in_good_standing": 5,
            "late_payments_last_year": 0,
            "bankruptcies": 0,
        }
    
    def _calculate_risk_score(
        self, 
        application: LoanApplication, 
        dti: float,
        credit_history: dict
    ) -> int:
        """Calcule le score de risque."""
        score = 50
        
        if dti > 50:
            score += 40
        elif dti > 40:
            score += 25
        elif dti > 30:
            score += 10
        else:
            score -= 10
        
        if application.employment_status.value == "UNEMPLOYED":
            score += 30
        elif application.employment_status.value == "SELF_EMPLOYED":
            score += 15
        elif application.employment_status.value == "PART_TIME":
            score += 10
        
        credit_score = credit_history["credit_score"]
        if credit_score >= 750:
            score -= 20
        elif credit_score >= 700:
            score -= 10
        elif credit_score < 600:
            score += 20
        
        return max(0, min(100, score))
    
    def _categorize_risk(self, score: int) -> RiskLevel:
        """Catégorise le score de risque."""
        if score < 20:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.MEDIUM
        elif score < 80:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _generate_rationale(
        self, 
        application: LoanApplication, 
        dti: float, 
        risk_score: int
    ) -> str:
        """Génère une justification via LLM."""
        prompt = f"""{RISK_AGENT_SYSTEM_PROMPT}

Génère une justification concise (2-3 phrases) pour cette évaluation:
- Montant: {application.amount_requested} USD
- Statut emploi: {application.employment_status.value}
- DTI calculé: {dti}%
- Score de risque: {risk_score}/100"""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            return f"Score de risque: {risk_score}/100 basé sur DTI de {dti}%"
    
    def analyze_application(self, application: LoanApplication) -> RiskAssessment:
        """Analyse une demande et génère une évaluation de risque."""
        print(f"📊 Analyse de l'application: {application.application_id}")
        
        dti = self._calculate_debt_ratio(
            income=application.declared_monthly_income,
            existing_debts=application.existing_debts,
            new_loan_amount=application.amount_requested,
        )
        
        credit_history = self._fetch_credit_history(application.applicant_id)
        risk_score = self._calculate_risk_score(application, dti, credit_history)
        risk_category = self._categorize_risk(risk_score)
        rationale = self._generate_rationale(application, dti, risk_score)
        
        assessment = RiskAssessment(
            application_id=application.application_id,
            assessment_id=str(uuid.uuid4()),
            risk_score=risk_score,
            risk_category=risk_category,
            debt_to_income_ratio=dti,
            rationale=rationale,
        )
        
        print(f"✅ Évaluation complétée: score={risk_score}/100 ({risk_category.value})")
        return assessment
    
    def run(self):
        """Boucle principale de consommation Kafka."""
        print("🚀 Risk Agent démarré - En attente de demandes...")
        
        try:
            for message in self.consumer.consume():
                if message is None:
                    continue
                
                try:
                    application = LoanApplication(**message.value())
                    assessment = self.analyze_application(application)
                    
                    self.producer.produce(
                        key=assessment.application_id,
                        value=assessment.model_dump(),
                    )
                    
                except Exception as e:
                    print(f"❌ Erreur de traitement: {e}")
                    
        except KeyboardInterrupt:
            print("\n🛑 Arrêt du Risk Agent...")
        finally:
            self.close()
    
    def close(self):
        """Ferme les connexions."""
        self.consumer.close()
        self.producer.close()


def main():
    """Point d'entrée CLI."""
    agent = RiskAgent()
    agent.run()


if __name__ == "__main__":
    main()

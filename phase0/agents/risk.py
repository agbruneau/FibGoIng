"""
Phase 0 - Agent Risk
====================
Agent d'analyse de risque.
Version simplifiée sans RAG ni Kafka.
"""

import os
import uuid
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv

from ..models import LoanApplication, RiskAssessment, RiskLevel

load_dotenv()


class RiskAgent:
    """
    Agent Risk Analyst - Le Cœur Cognitif
    
    Calcule un score de risque basé sur:
    - Ratio dette/revenu (DTI)
    - Statut d'emploi
    - Historique de crédit simulé
    """
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-20241022"
    
    def analyze(self, application: LoanApplication) -> Optional[RiskAssessment]:
        """
        Analyse une demande de prêt et génère une évaluation de risque.
        
        Args:
            application: Demande validée
            
        Returns:
            RiskAssessment ou None si erreur
        """
        if application is None:
            return None
        
        # Calcul du ratio dette/revenu (DTI)
        dti = self._calculate_debt_ratio(
            income=application.declared_monthly_income,
            existing_debts=application.existing_debts,
            new_loan_amount=application.amount_requested,
        )
        
        # Récupération de l'historique de crédit (simulé)
        credit_history = self._fetch_credit_history(application.applicant_id)
        
        # Calcul du score de risque
        risk_score = self._calculate_risk_score(application, dti, credit_history)
        risk_category = self._categorize_risk(risk_score)
        
        # Génération de la justification via LLM
        rationale = self._generate_rationale(application, dti, risk_score)
        
        assessment = RiskAssessment(
            application_id=application.application_id,
            assessment_id=str(uuid.uuid4()),
            risk_score=risk_score,
            risk_category=risk_category,
            debt_to_income_ratio=dti,
            rationale=rationale,
        )
        
        print(f"📊 Score de risque: {risk_score}/100 ({risk_category.value})")
        return assessment
    
    def _calculate_debt_ratio(
        self, 
        income: float, 
        existing_debts: float, 
        new_loan_amount: float
    ) -> float:
        """Calcule le ratio dette/revenu (DTI)."""
        if income <= 0:
            return 100.0  # Risque maximum
        
        # Estimation mensualité du nouveau prêt (simplifié: 1% du montant)
        estimated_monthly_payment = new_loan_amount * 0.01
        total_monthly_debt = existing_debts + estimated_monthly_payment
        
        dti = (total_monthly_debt / income) * 100
        return round(dti, 2)
    
    def _fetch_credit_history(self, applicant_id: str) -> dict:
        """Récupère l'historique de crédit externe (simulé)."""
        # Simulation: retourne un historique fictif
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
        """Calcule le score de risque basé sur les règles métier."""
        score = 50  # Score de base
        
        # Ajustement basé sur le DTI
        if dti > 50:
            score += 40
        elif dti > 40:
            score += 25
        elif dti > 30:
            score += 10
        else:
            score -= 10
        
        # Ajustement basé sur le statut d'emploi
        if application.employment_status.value == "UNEMPLOYED":
            score += 30
        elif application.employment_status.value == "SELF_EMPLOYED":
            score += 15
        elif application.employment_status.value == "PART_TIME":
            score += 10
        
        # Ajustement basé sur l'historique de crédit
        credit_score = credit_history["credit_score"]
        if credit_score >= 750:
            score -= 20
        elif credit_score >= 700:
            score -= 10
        elif credit_score < 600:
            score += 20
        
        # Limiter entre 0 et 100
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
        """Génère une justification en langage naturel via LLM."""
        prompt = f"""Génère une justification concise (2-3 phrases) pour cette évaluation:
- Montant: {application.amount_requested} USD
- Statut emploi: {application.employment_status.value}
- DTI calculé: {dti}%
- Score de risque: {risk_score}/100

Sois professionnel et factuel."""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            return f"Score de risque: {risk_score}/100 basé sur DTI de {dti}% et statut {application.employment_status.value}"

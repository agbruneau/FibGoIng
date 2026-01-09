"""
Phase 0 - Agent Decision
========================
Agent de décision finale pour les demandes de prêt.
Version simplifiée sans Kafka.
"""

import os
import uuid
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv

from ..models import RiskAssessment, LoanDecision, DecisionStatus

load_dotenv()


class DecisionAgent:
    """
    Agent Loan Officer - Le Décideur Final
    
    Critères de décision:
    - Risk Score < 20: APPROBATION AUTOMATIQUE
    - Risk Score > 80: REJET AUTOMATIQUE
    - Entre 20 et 80: Analyse de la rationale
    """
    
    THRESHOLD_AUTO_APPROVE = 20
    THRESHOLD_AUTO_REJECT = 80
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-20241022"
    
    def decide(self, assessment: RiskAssessment) -> Optional[LoanDecision]:
        """
        Prend la décision finale basée sur l'évaluation de risque.
        
        Args:
            assessment: Évaluation de risque
            
        Returns:
            LoanDecision ou None si erreur
        """
        if assessment is None:
            return None
        
        # Initialisation
        status = DecisionStatus.MANUAL_REVIEW_REQUIRED
        approved_amount = None
        interest_rate = None
        
        # Règle 1: Approbation automatique pour risque très faible
        if assessment.risk_score < self.THRESHOLD_AUTO_APPROVE:
            status = DecisionStatus.APPROVED
            approved_amount = 50000.0  # Simplifié: approuve le montant demandé
            interest_rate = self._calculate_interest_rate(assessment.risk_score)
        
        # Règle 2: Rejet automatique pour risque critique
        elif assessment.risk_score > self.THRESHOLD_AUTO_REJECT:
            status = DecisionStatus.REJECTED
        
        # Règle 3: Zone grise - analyse détaillée
        else:
            decision = self._analyze_gray_zone(assessment)
            status = decision["status"]
            approved_amount = decision.get("approved_amount")
            interest_rate = decision.get("interest_rate")
        
        # Générer la justification
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
        print(f"{status_emoji} Décision: {status.value}", end="")
        if approved_amount:
            print(f" - Montant approuvé: {approved_amount} USD", end="")
        if interest_rate:
            print(f" - Taux: {interest_rate}%", end="")
        print()
        
        return decision
    
    def _calculate_interest_rate(self, risk_score: int) -> float:
        """Calcule le taux d'intérêt basé sur le risque."""
        base_rate = 5.0
        risk_premium = (risk_score / 100) * 10  # 0-10% de prime de risque
        return round(base_rate + risk_premium, 2)
    
    def _analyze_gray_zone(self, assessment: RiskAssessment) -> dict:
        """
        Analyse détaillée pour les cas en zone grise (score 20-80).
        
        Utilise le LLM pour interpréter la rationale de l'analyste risque.
        """
        prompt = f"""Analyse cette évaluation de risque et décide:

Score de risque: {assessment.risk_score}/100
Catégorie: {assessment.risk_category.value}
DTI: {assessment.debt_to_income_ratio}%
Justification analyste: {assessment.rationale}

Règles:
- Si score 20-50 et DTI < 40%: APPROVED
- Si score 50-80 ou DTI > 40%: REJECTED
- Si incertitude: MANUAL_REVIEW_REQUIRED

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
            # Par défaut: revue humaine
            return {
                "status": DecisionStatus.MANUAL_REVIEW_REQUIRED,
            }
    
    def _generate_decision_rationale(
        self, 
        assessment: RiskAssessment, 
        status: DecisionStatus
    ) -> str:
        """Génère une explication de la décision pour le client."""
        if status == DecisionStatus.APPROVED:
            return f"Votre demande de prêt a été approuvée. Score de risque: {assessment.risk_score}/100."
        elif status == DecisionStatus.REJECTED:
            return f"Nous regrettons de vous informer que votre demande n'a pas été retenue. Score de risque: {assessment.risk_score}/100."
        else:
            return "Votre demande nécessite une analyse complémentaire par nos équipes. Nous vous contacterons sous 48h."

#!/usr/bin/env python3
"""
Phase 2 - Risk Agent avec Kafka + RAG
======================================
Agent d'analyse de risque avec RAG sur les politiques de crédit.
"""

import os
import uuid
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

from src.shared.kafka_client import KafkaConsumerClient, KafkaProducerClient
from src.shared.models import LoanApplication, RiskAssessment, RiskLevel
from src.shared.prompts import RISK_AGENT_SYSTEM_PROMPT
from src.shared.rag_client import RAGClient

load_dotenv()


class RiskAgent:
    """
    Agent Risk Analyst - Le Cœur Cognitif avec RAG
    
    Consomme les demandes validées, consulte les politiques via RAG,
    et produit les évaluations de risque.
    """
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-20241022"
        
        # RAG Client pour consulter les politiques
        self.rag_client = RAGClient()
        
        self.consumer = KafkaConsumerClient(
            topic="finance.loan.application.v1",
            group_id="agent-risk-analyst",
        )
        
        self.producer = KafkaProducerClient(topic="risk.scoring.result.v1")
        print("✅ Risk Agent initialisé (avec RAG)")
    
    def _search_credit_policy(self, query: str) -> str:
        """
        Recherche sémantique dans la base de politiques.
        
        Args:
            query: Requête de recherche
            
        Returns:
            Documents pertinents trouvés
        """
        results = self.rag_client.search(query, n_results=3)
        if results:
            return "\n\n".join(results)
        return "Aucune politique trouvée."
    
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
        credit_history: dict,
        policies: str
    ) -> int:
        """Calcule le score de risque en tenant compte des politiques."""
        score = 50
        
        # Ajustement basé sur le DTI et les politiques
        if dti > 50:
            score += 40
        elif dti > 40:
            # Vérifier les exceptions dans les politiques
            if "travailleurs indépendants" in policies.lower() and application.employment_status.value == "SELF_EMPLOYED":
                score += 30  # DTI max 40% pour indépendants
            else:
                score += 25
        elif dti > 30:
            score += 10
        else:
            score -= 10
        
        # Ajustement basé sur le statut d'emploi
        if application.employment_status.value == "UNEMPLOYED":
            score += 30
        elif application.employment_status.value == "SELF_EMPLOYED":
            score += 15  # Majoration selon politiques
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
    
    def _extract_policy_references(self, policies: str) -> list[str]:
        """Extrait les références de politiques depuis le texte."""
        references = []
        if "Politique 4.2" in policies or "4.2" in policies:
            references.append("Policy-4.2-SelfEmployed")
        if "Section 2" in policies or "2.1" in policies or "2.2" in policies or "2.3" in policies:
            references.append("Policy-2.1-DTI-Limits")
        if "Section 1" in policies or "1.1" in policies:
            references.append("Policy-1.1-DTI-General")
        return references or ["Policy-General"]
    
    def _generate_rationale(
        self, 
        application: LoanApplication, 
        dti: float, 
        risk_score: int,
        policies: str
    ) -> str:
        """Génère une justification via LLM en utilisant les politiques."""
        prompt = f"""{RISK_AGENT_SYSTEM_PROMPT}

Politiques de crédit pertinentes:
{policies}

Génère une justification concise (2-3 phrases) pour cette évaluation:
- Montant: {application.amount_requested} USD
- Statut emploi: {application.employment_status.value}
- DTI calculé: {dti}%
- Score de risque: {risk_score}/100

Cite les politiques utilisées."""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            return f"Score de risque: {risk_score}/100 basé sur DTI de {dti}% et statut {application.employment_status.value}"
    
    def analyze_application(self, application: LoanApplication) -> RiskAssessment:
        """Analyse une demande et génère une évaluation de risque avec RAG."""
        print(f"📊 Analyse de l'application: {application.application_id}")
        
        # Recherche dans les politiques
        policy_query = f"règles {application.employment_status.value.lower()} ratio endettement DTI"
        policies = self._search_credit_policy(policy_query)
        policy_refs = self._extract_policy_references(policies)
        
        if policies and "Aucune politique trouvée" not in policies:
            print(f"📚 Politiques consultées: {', '.join(policy_refs)}")
        
        dti = self._calculate_debt_ratio(
            income=application.declared_monthly_income,
            existing_debts=application.existing_debts,
            new_loan_amount=application.amount_requested,
        )
        
        credit_history = self._fetch_credit_history(application.applicant_id)
        risk_score = self._calculate_risk_score(application, dti, credit_history, policies)
        risk_category = self._categorize_risk(risk_score)
        rationale = self._generate_rationale(application, dti, risk_score, policies)
        
        assessment = RiskAssessment(
            application_id=application.application_id,
            assessment_id=str(uuid.uuid4()),
            risk_score=risk_score,
            risk_category=risk_category,
            debt_to_income_ratio=dti,
            rationale=rationale,
            checked_policies=policy_refs,
        )
        
        print(f"✅ Évaluation complétée: score={risk_score}/100 ({risk_category.value})")
        return assessment
    
    def run(self):
        """Boucle principale de consommation Kafka."""
        print("🚀 Risk Agent démarré (avec RAG) - En attente de demandes...")
        
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

#!/usr/bin/env python3
"""
Phase 0 - Script Orchestrateur Principal
==========================================
Exécute le pipeline complet: Intake → Risk → Decision

Usage:
    python main.py
"""

import os
from dotenv import load_dotenv

from agents.intake import IntakeAgent
from agents.risk import RiskAgent
from agents.decision import DecisionAgent

load_dotenv()


def main():
    """Point d'entrée principal."""
    
    # Vérifier la clé API
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Erreur: ANTHROPIC_API_KEY non trouvée dans .env")
        print("   Créez un fichier .env avec: ANTHROPIC_API_KEY=votre_clé_ici")
        return
    
    print("🚀 Démarrage du pipeline AgentMeshKafka (Phase 0)")
    print("=" * 60)
    
    # Exemple de demande de prêt
    sample_request = {
        "applicant_id": "CUST-12345",
        "amount_requested": 50000,
        "currency": "USD",
        "declared_monthly_income": 5000,
        "employment_status": "FULL_TIME",
        "existing_debts": 10000,
        "loan_purpose": "Home renovation",
    }
    
    print(f"\n📝 Demande reçue:")
    print(f"   Demandeur: {sample_request['applicant_id']}")
    print(f"   Montant: {sample_request['amount_requested']} {sample_request['currency']}")
    print(f"   Revenu mensuel: {sample_request['declared_monthly_income']}")
    print()
    
    # Étape 1: Agent Intake
    print("🔍 Étape 1: Validation (Agent Intake)")
    intake_agent = IntakeAgent()
    validated_application = intake_agent.process(sample_request)
    
    if validated_application is None:
        print("❌ La demande a été rejetée par l'Agent Intake")
        return
    
    print()
    
    # Étape 2: Agent Risk
    print("📊 Étape 2: Évaluation de risque (Agent Risk)")
    risk_agent = RiskAgent()
    assessment = risk_agent.analyze(validated_application)
    
    if assessment is None:
        print("❌ Erreur lors de l'évaluation de risque")
        return
    
    print()
    
    # Étape 3: Agent Decision
    print("⚖️  Étape 3: Décision finale (Agent Decision)")
    decision_agent = DecisionAgent()
    decision = decision_agent.decide(assessment)
    
    if decision is None:
        print("❌ Erreur lors de la prise de décision")
        return
    
    print()
    print("=" * 60)
    print("✅ Pipeline terminé avec succès!")
    print()
    print("📋 Résumé:")
    print(f"   Application ID: {validated_application.application_id}")
    print(f"   Score de risque: {assessment.risk_score}/100 ({assessment.risk_category.value})")
    print(f"   Décision: {decision.status.value}")
    if decision.approved_amount:
        print(f"   Montant approuvé: {decision.approved_amount} USD")
    if decision.interest_rate:
        print(f"   Taux d'intérêt: {decision.interest_rate}%")
    print(f"   Justification: {decision.decision_rationale}")


if __name__ == "__main__":
    main()

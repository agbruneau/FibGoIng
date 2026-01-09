#!/usr/bin/env python3
"""
Exemple 3 : Flux Complet
=========================
Démonstration du pipeline complet Intake → Risk → Decision.

Usage:
    python examples/03-full-flow.py
    
Prérequis:
    - Phase 0 complète (agents fonctionnels)
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin de phase0
sys.path.insert(0, str(Path(__file__).parent.parent / "phase0"))

from agents.intake import IntakeAgent
from agents.risk import RiskAgent
from agents.decision import DecisionAgent
from dotenv import load_dotenv

load_dotenv()


def main():
    """Exemple du flux complet."""
    print("🚀 Exemple 3 : Flux Complet")
    print("=" * 50)
    
    # Demande initiale
    request = {
        "applicant_id": "CUST-FULL-001",
        "amount_requested": 100000,
        "currency": "USD",
        "declared_monthly_income": 8000,
        "employment_status": "FULL_TIME",
        "existing_debts": 20000,
        "loan_purpose": "Expansion entreprise"
    }
    
    print(f"\n📝 Demande initiale:")
    print(f"   Demandeur: {request['applicant_id']}")
    print(f"   Montant: {request['amount_requested']} {request['currency']}")
    print(f"   Revenu: {request['declared_monthly_income']}/mois")
    
    # Étape 1 : Intake
    print(f"\n{'='*50}")
    print("🔍 Étape 1 : Agent Intake (Validation)")
    print("=" * 50)
    intake_agent = IntakeAgent()
    validated = intake_agent.process(request)
    
    if not validated:
        print("❌ Demande rejetée par l'Agent Intake")
        return
    
    print(f"✅ Demande validée: {validated.application_id}")
    
    # Étape 2 : Risk
    print(f"\n{'='*50}")
    print("📊 Étape 2 : Agent Risk (Évaluation)")
    print("=" * 50)
    risk_agent = RiskAgent()
    assessment = risk_agent.analyze(validated)
    
    print(f"✅ Évaluation complétée:")
    print(f"   Score: {assessment.risk_score}/100")
    print(f"   Catégorie: {assessment.risk_category.value}")
    print(f"   DTI: {assessment.debt_to_income_ratio}%")
    
    # Étape 3 : Decision
    print(f"\n{'='*50}")
    print("⚖️  Étape 3 : Agent Decision (Décision finale)")
    print("=" * 50)
    decision_agent = DecisionAgent()
    decision = decision_agent.decide(assessment)
    
    print(f"✅ Décision prise:")
    print(f"   Statut: {decision.status.value}")
    if decision.approved_amount:
        print(f"   Montant approuvé: {decision.approved_amount} USD")
    if decision.interest_rate:
        print(f"   Taux d'intérêt: {decision.interest_rate}%")
    
    # Résumé
    print(f"\n{'='*50}")
    print("📋 Résumé du Pipeline")
    print("=" * 50)
    print(f"   Application ID: {validated.application_id}")
    print(f"   Score de risque: {assessment.risk_score}/100 ({assessment.risk_category.value})")
    print(f"   Décision: {decision.status.value}")
    print(f"   Justification: {decision.decision_rationale}")
    
    print("\n" + "=" * 50)
    print("💡 Ce flux complet fonctionne sans infrastructure (Phase 0)")
    print("   Pour Kafka, consultez phase1/ et les exemples précédents")


if __name__ == "__main__":
    main()

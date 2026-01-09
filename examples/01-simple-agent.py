#!/usr/bin/env python3
"""
Exemple 1 : Agent Simple
=========================
Démonstration d'un agent minimal sans infrastructure.

Usage:
    python examples/01-simple-agent.py
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin de phase0
sys.path.insert(0, str(Path(__file__).parent.parent / "phase0"))

from agents.intake import IntakeAgent
from dotenv import load_dotenv

load_dotenv()


def main():
    """Exemple d'utilisation d'un agent simple."""
    print("🚀 Exemple 1 : Agent Simple")
    print("=" * 50)
    
    # Créer l'agent
    agent = IntakeAgent()
    
    # Exemple de demande
    request = {
        "applicant_id": "CUST-EXAMPLE-001",
        "amount_requested": 30000,
        "currency": "USD",
        "declared_monthly_income": 4000,
        "employment_status": "FULL_TIME",
        "existing_debts": 5000,
        "loan_purpose": "Achat véhicule"
    }
    
    print(f"\n📝 Demande reçue:")
    print(f"   Demandeur: {request['applicant_id']}")
    print(f"   Montant: {request['amount_requested']} {request['currency']}")
    
    # Traiter la demande
    print(f"\n🔍 Traitement par l'Agent Intake...")
    validated = agent.process(request)
    
    if validated:
        print(f"\n✅ Résultat:")
        print(f"   Application ID: {validated.application_id}")
        print(f"   Statut: Validé")
    else:
        print(f"\n❌ Résultat: Demande rejetée")
    
    print("\n" + "=" * 50)
    print("💡 Cet agent fonctionne sans infrastructure (Phase 0)")


if __name__ == "__main__":
    main()

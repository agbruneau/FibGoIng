#!/usr/bin/env python3
"""
Exemple 2 : Agent avec Kafka
=============================
Démonstration d'un agent qui publie dans Kafka.

Usage:
    python examples/02-agent-with-kafka.py
    
Prérequis:
    - Kafka démarré (docker-compose up -d dans phase1/)
    - Topics créés (python phase1/scripts/init_kafka.py)
"""

import os
import sys
import uuid
from pathlib import Path

# Ajouter le chemin de phase1
sys.path.insert(0, str(Path(__file__).parent.parent / "phase1"))

from src.shared.kafka_client import KafkaProducerClient
from src.shared.models import LoanApplication, EmploymentStatus
from dotenv import load_dotenv

load_dotenv()


def main():
    """Exemple d'agent qui publie dans Kafka."""
    print("🚀 Exemple 2 : Agent avec Kafka")
    print("=" * 50)
    
    # Créer le producer
    producer = KafkaProducerClient(topic="finance.loan.application.v1")
    
    # Créer une demande
    application = LoanApplication(
        application_id=str(uuid.uuid4()),
        applicant_id="CUST-KAFKA-001",
        amount_requested=75000,
        currency="USD",
        declared_monthly_income=6000,
        employment_status=EmploymentStatus.FULL_TIME,
        existing_debts=15000,
        loan_purpose="Achat immobilier"
    )
    
    print(f"\n📝 Demande créée:")
    print(f"   Application ID: {application.application_id}")
    print(f"   Montant: {application.amount_requested} {application.currency}")
    
    # Publier dans Kafka
    print(f"\n📤 Publication dans Kafka...")
    success = producer.produce(
        key=application.application_id,
        value=application.model_dump()
    )
    
    if success:
        print(f"\n✅ Demande publiée avec succès!")
        print(f"   Topic: finance.loan.application.v1")
        print(f"   Key: {application.application_id}")
        print(f"\n💡 Un Agent Risk peut maintenant consommer ce message")
    else:
        print(f"\n❌ Échec de publication")
    
    producer.close()
    print("\n" + "=" * 50)
    print("💡 Cet exemple nécessite Kafka (Phase 1+)")


if __name__ == "__main__":
    main()

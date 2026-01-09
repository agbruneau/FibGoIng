#!/usr/bin/env python3
"""
Phase 1 - Script de Test
=========================
Envoie une demande de test dans Kafka pour tester le pipeline.
"""

import os
import uuid
from dotenv import load_dotenv

from src.shared.kafka_client import KafkaProducerClient

load_dotenv()


def send_test_request():
    """Envoie une demande de test."""
    producer = KafkaProducerClient(topic="finance.loan.application.v1")
    
    test_request = {
        "application_id": str(uuid.uuid4()),
        "applicant_id": "CUST-TEST-001",
        "amount_requested": 50000,
        "currency": "USD",
        "declared_monthly_income": 5000,
        "employment_status": "FULL_TIME",
        "existing_debts": 10000,
        "loan_purpose": "Home renovation",
    }
    
    print("📤 Envoi d'une demande de test...")
    print(f"   Application ID: {test_request['application_id']}")
    print(f"   Montant: {test_request['amount_requested']} {test_request['currency']}")
    
    success = producer.produce(
        key=test_request["application_id"],
        value=test_request,
    )
    
    if success:
        print("✅ Demande envoyée avec succès!")
        print("💡 Vérifiez les logs des agents pour voir le traitement")
    else:
        print("❌ Échec de l'envoi")
    
    producer.close()


if __name__ == "__main__":
    send_test_request()

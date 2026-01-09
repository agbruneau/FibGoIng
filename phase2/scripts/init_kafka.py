#!/usr/bin/env python3
"""
Phase 2 - Initialisation des Topics Kafka
===========================================
Crée les topics nécessaires pour le système.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaException
import os
from dotenv import load_dotenv

load_dotenv()


def create_topics():
    """Crée les topics Kafka nécessaires."""
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    admin_client = AdminClient({"bootstrap.servers": bootstrap_servers})
    
    topics = [
        NewTopic(
            "finance.loan.application.v1",
            num_partitions=1,
            replication_factor=1,
        ),
        NewTopic(
            "risk.scoring.result.v1",
            num_partitions=1,
            replication_factor=1,
        ),
        NewTopic(
            "finance.loan.decision.v1",
            num_partitions=1,
            replication_factor=1,
        ),
    ]
    
    print("📝 Création des topics Kafka...")
    
    futures = admin_client.create_topics(topics)
    
    for topic, future in futures.items():
        try:
            future.result()  # Attendre la création
            print(f"✅ Topic créé: {topic}")
        except KafkaException as e:
            if "already exists" in str(e).lower():
                print(f"ℹ️  Topic existe déjà: {topic}")
            else:
                print(f"❌ Erreur pour {topic}: {e}")


if __name__ == "__main__":
    create_topics()

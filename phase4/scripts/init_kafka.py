#!/usr/bin/env python3
"""
AgentMeshKafka - Kafka Topics Initialization Script (Phase 4)
==============================================================
Crée les topics Kafka avec les configurations appropriées.
Voir docs/02-DataContracts.md pour la topologie complète.

Usage:
    python scripts/init_kafka.py
"""

import os
import sys
from confluent_kafka.admin import AdminClient, NewTopic
from dotenv import load_dotenv

load_dotenv()

# Configuration des topics (voir docs/02-DataContracts.md)
TOPICS_CONFIG = [
    {
        "name": "finance.loan.application.v1",
        "partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(7 * 24 * 60 * 60 * 1000),  # 7 jours
            "cleanup.policy": "delete",
        },
        "description": "Demandes de prêt brutes initiées par les clients",
    },
    {
        "name": "risk.scoring.result.v1",
        "partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(-1),  # Permanent (Log)
            "cleanup.policy": "compact",
        },
        "description": "Évaluation des risques et justification cognitive",
    },
    {
        "name": "finance.loan.decision.v1",
        "partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(-1),  # Permanent (Log)
            "cleanup.policy": "compact",
        },
        "description": "Décision finale (Approbation/Refus) notifiée",
    },
    {
        "name": "sys.deadletter.queue.v1",
        "partitions": 1,
        "replication_factor": 1,
        "config": {
            "retention.ms": str(30 * 24 * 60 * 60 * 1000),  # 30 jours
            "cleanup.policy": "delete",
        },
        "description": "Messages en erreur pour analyse humaine",
    },
]


def create_topics():
    """Crée les topics Kafka définis dans TOPICS_CONFIG."""
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    print(f"🔌 Connexion à Kafka: {bootstrap_servers}")
    
    admin_client = AdminClient({"bootstrap.servers": bootstrap_servers})
    
    # Vérifier les topics existants
    existing_topics = admin_client.list_topics(timeout=10).topics.keys()
    
    new_topics = []
    for topic_config in TOPICS_CONFIG:
        topic_name = topic_config["name"]
        
        if topic_name in existing_topics:
            print(f"⏭️  Topic '{topic_name}' existe déjà - ignoré")
            continue
        
        new_topic = NewTopic(
            topic=topic_name,
            num_partitions=topic_config["partitions"],
            replication_factor=topic_config["replication_factor"],
            config=topic_config["config"],
        )
        new_topics.append(new_topic)
        print(f"📝 Topic à créer: {topic_name} ({topic_config['description']})")
    
    if not new_topics:
        print("\n✅ Tous les topics existent déjà!")
        return
    
    # Créer les nouveaux topics
    print(f"\n🚀 Création de {len(new_topics)} topic(s)...")
    futures = admin_client.create_topics(new_topics)
    
    for topic_name, future in futures.items():
        try:
            future.result()  # Attendre la création
            print(f"✅ Topic '{topic_name}' créé avec succès")
        except Exception as e:
            print(f"❌ Erreur création '{topic_name}': {e}")
            sys.exit(1)
    
    print("\n🎉 Initialisation Kafka terminée!")


if __name__ == "__main__":
    create_topics()

"""
AgentMeshKafka - Shared Utilities Package
==========================================
Utilitaires partagés entre tous les agents:
- kafka_client: Wrappers Producer/Consumer Kafka
- models: Modèles Pydantic (générés depuis Avro)
- prompts: System Prompts et Constitutions
"""

from .models import (
    LoanApplication,
    RiskAssessment,
    LoanDecision,
    EmploymentStatus,
    RiskLevel,
    DecisionStatus,
)
from .kafka_client import KafkaProducerClient, KafkaConsumerClient

__all__ = [
    "LoanApplication",
    "RiskAssessment",
    "LoanDecision",
    "EmploymentStatus",
    "RiskLevel",
    "DecisionStatus",
    "KafkaProducerClient",
    "KafkaConsumerClient",
]

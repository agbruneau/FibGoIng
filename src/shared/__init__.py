"""
AgentMeshKafka - Shared Utilities Package
==========================================
Utilitaires partagés entre tous les agents:
- kafka_client: Wrappers Producer/Consumer Kafka
- models: Modèles Pydantic (générés depuis Avro)
- prompts: System Prompts et Constitutions
- metrics: Métriques Prometheus
- logging_config: Logging JSON structuré
- config_loader: Chargement configuration YAML
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
from .config_loader import load_config, get_agent_config, get_thresholds

# Lazy imports pour éviter les dépendances circulaires
# from .metrics import start_metrics_server, record_decision, record_risk_score
# from .logging_config import configure_logging, get_logger

__all__ = [
    # Models
    "LoanApplication",
    "RiskAssessment",
    "LoanDecision",
    "EmploymentStatus",
    "RiskLevel",
    "DecisionStatus",
    # Kafka
    "KafkaProducerClient",
    "KafkaConsumerClient",
    # Config
    "load_config",
    "get_agent_config",
    "get_thresholds",
]


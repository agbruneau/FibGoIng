"""
AgentMeshKafka - Prometheus Metrics
====================================
Module de métriques Prometheus pour le monitoring des agents.

Expose les métriques suivantes:
- agent_decisions_total: Nombre de décisions par statut
- agent_risk_score_distribution: Distribution des scores de risque
- kafka_messages_processed_total: Messages Kafka traités
- agent_processing_duration_seconds: Durée de traitement

Usage:
    from src.shared.metrics import (
        start_metrics_server,
        record_decision,
        record_risk_score,
        record_processing_time,
    )
    
    # Démarrer le serveur de métriques
    start_metrics_server(port=9090)
    
    # Enregistrer une décision
    record_decision(status="APPROVED", agent_id="agent-loan-officer")
    
    # Enregistrer un score de risque
    record_risk_score(score=45, agent_id="agent-risk-analyst")

Configuration:
    METRICS_PORT: Port du serveur HTTP (défaut: 9090)
    METRICS_ENABLED: Activer/désactiver les métriques (défaut: true)
"""

import os
import threading
from typing import Optional

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    start_http_server,
    REGISTRY,
)


# =============================================================================
# Configuration
# =============================================================================

METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"
METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))


# =============================================================================
# Métriques
# =============================================================================

# Counter: Nombre total de décisions prises
DECISIONS_TOTAL = Counter(
    "agent_decisions_total",
    "Total number of loan decisions made",
    ["status", "agent_id"],
)

# Counter: Messages Kafka traités
KAFKA_MESSAGES_PROCESSED = Counter(
    "kafka_messages_processed_total",
    "Total number of Kafka messages processed",
    ["topic", "agent_id", "status"],
)

# Histogram: Distribution des scores de risque
RISK_SCORE_DISTRIBUTION = Histogram(
    "agent_risk_score_distribution",
    "Distribution of risk scores",
    ["agent_id"],
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)

# Histogram: Durée de traitement des opérations
PROCESSING_DURATION = Histogram(
    "agent_processing_duration_seconds",
    "Time spent processing operations",
    ["agent_id", "operation"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

# Gauge: Lag du consumer Kafka
KAFKA_CONSUMER_LAG = Gauge(
    "kafka_consumer_lag",
    "Current consumer lag",
    ["topic", "group_id", "partition"],
)

# Gauge: Dernier temps de traitement
LAST_PROCESSING_TIME = Gauge(
    "agent_last_processing_time_seconds",
    "Last processing time in seconds",
    ["agent_id", "operation"],
)

# Info: Informations sur l'agent
AGENT_INFO = Info(
    "agent",
    "Agent information",
)


# =============================================================================
# Fonctions d'enregistrement des métriques
# =============================================================================

def record_decision(
    status: str,
    agent_id: str = "agent-loan-officer",
) -> None:
    """
    Enregistre une décision de prêt.
    
    Args:
        status: Statut de la décision (APPROVED, REJECTED, MANUAL_REVIEW_REQUIRED)
        agent_id: Identifiant de l'agent
    """
    if not METRICS_ENABLED:
        return
    DECISIONS_TOTAL.labels(status=status, agent_id=agent_id).inc()


def record_risk_score(
    score: int,
    agent_id: str = "agent-risk-analyst",
) -> None:
    """
    Enregistre un score de risque dans l'histogramme.
    
    Args:
        score: Score de risque (0-100)
        agent_id: Identifiant de l'agent
    """
    if not METRICS_ENABLED:
        return
    RISK_SCORE_DISTRIBUTION.labels(agent_id=agent_id).observe(score)


def record_kafka_message(
    topic: str,
    agent_id: str,
    status: str = "success",
) -> None:
    """
    Enregistre un message Kafka traité.
    
    Args:
        topic: Nom du topic Kafka
        agent_id: Identifiant de l'agent
        status: Statut du traitement (success, error)
    """
    if not METRICS_ENABLED:
        return
    KAFKA_MESSAGES_PROCESSED.labels(
        topic=topic,
        agent_id=agent_id,
        status=status,
    ).inc()


def record_processing_time(
    duration_seconds: float,
    agent_id: str,
    operation: str = "analyze",
) -> None:
    """
    Enregistre la durée d'une opération.
    
    Args:
        duration_seconds: Durée en secondes
        agent_id: Identifiant de l'agent
        operation: Type d'opération (analyze, decide, validate)
    """
    if not METRICS_ENABLED:
        return
    PROCESSING_DURATION.labels(
        agent_id=agent_id,
        operation=operation,
    ).observe(duration_seconds)
    LAST_PROCESSING_TIME.labels(
        agent_id=agent_id,
        operation=operation,
    ).set(duration_seconds)


def update_consumer_lag(
    topic: str,
    group_id: str,
    partition: int,
    lag: int,
) -> None:
    """
    Met à jour le lag du consumer Kafka.
    
    Args:
        topic: Nom du topic
        group_id: ID du consumer group
        partition: Numéro de partition
        lag: Lag actuel (highwater - committed offset)
    """
    if not METRICS_ENABLED:
        return
    KAFKA_CONSUMER_LAG.labels(
        topic=topic,
        group_id=group_id,
        partition=str(partition),
    ).set(lag)


def set_agent_info(
    agent_id: str,
    version: str = "1.0.0",
    model: str = "unknown",
) -> None:
    """
    Définit les informations de l'agent.
    
    Args:
        agent_id: Identifiant de l'agent
        version: Version de l'agent
        model: Modèle LLM utilisé
    """
    if not METRICS_ENABLED:
        return
    AGENT_INFO.info({
        "agent_id": agent_id,
        "version": version,
        "model": model,
    })


# =============================================================================
# Context Manager pour mesurer la durée
# =============================================================================

class TimingContext:
    """
    Context manager pour mesurer et enregistrer la durée d'une opération.
    
    Usage:
        with TimingContext("agent-risk-analyst", "analyze"):
            # Opération à mesurer
            result = analyze_application(app)
    """
    
    def __init__(self, agent_id: str, operation: str):
        self.agent_id = agent_id
        self.operation = operation
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        import time
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        if self.start_time is not None:
            duration = time.perf_counter() - self.start_time
            record_processing_time(duration, self.agent_id, self.operation)
        return False


# =============================================================================
# Serveur HTTP pour l'endpoint /metrics
# =============================================================================

_metrics_server_started = False
_metrics_lock = threading.Lock()


def start_metrics_server(port: Optional[int] = None) -> bool:
    """
    Démarre le serveur HTTP Prometheus sur le port spécifié.
    
    Le serveur est démarré dans un thread daemon et expose l'endpoint /metrics.
    
    Args:
        port: Port HTTP (défaut: METRICS_PORT env var ou 9090)
        
    Returns:
        True si le serveur a été démarré, False s'il était déjà actif
    """
    global _metrics_server_started
    
    if not METRICS_ENABLED:
        return False
    
    with _metrics_lock:
        if _metrics_server_started:
            return False
        
        actual_port = port or METRICS_PORT
        
        try:
            start_http_server(actual_port)
            _metrics_server_started = True
            
            import structlog
            logger = structlog.get_logger()
            logger.info(
                "Prometheus metrics server started",
                port=actual_port,
                endpoint=f"http://localhost:{actual_port}/metrics",
            )
            
            return True
            
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("Failed to start metrics server", error=str(e), port=actual_port)
            return False


def is_metrics_server_running() -> bool:
    """Vérifie si le serveur de métriques est actif."""
    return _metrics_server_started

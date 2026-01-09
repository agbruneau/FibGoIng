"""
AgentMeshKafka - Structured Logging Configuration
===================================================
Configuration centralisée pour le logging JSON structuré avec correlation_id.

Ce module configure structlog pour produire des logs JSON enrichis avec:
- correlation_id: ID unique propagé à travers le pipeline
- agent_id: Identifiant de l'agent
- timestamp: Horodatage ISO 8601
- caller_info: Fichier, fonction, ligne

Usage:
    from src.shared.logging_config import (
        configure_logging,
        get_logger,
        set_correlation_id,
        get_correlation_id,
        bind_context,
    )
    
    # Configurer le logging au démarrage
    configure_logging(agent_id="agent-risk-analyst")
    
    # Obtenir un logger
    logger = get_logger()
    
    # Définir le correlation_id pour une requête
    set_correlation_id("req-12345")
    
    # Logger avec contexte enrichi automatiquement
    logger.info("Processing application", application_id="APP-001")

Output JSON:
    {
        "timestamp": "2026-01-09T14:20:00.000Z",
        "level": "info",
        "event": "Processing application",
        "correlation_id": "req-12345",
        "agent_id": "agent-risk-analyst",
        "application_id": "APP-001",
        "caller": "main.py:analyze_application:145"
    }
"""

import os
import sys
import uuid
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from structlog.types import EventDict, WrappedLogger


# =============================================================================
# Context Variables pour le tracing
# =============================================================================

# Correlation ID pour tracer les requêtes à travers le pipeline
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Application ID pour tracer une demande de prêt spécifique
_application_id: ContextVar[Optional[str]] = ContextVar("application_id", default=None)

# Agent ID (défini au démarrage)
_agent_id: ContextVar[str] = ContextVar("agent_id", default="unknown")


# =============================================================================
# Accesseurs Context Variables
# =============================================================================

def set_correlation_id(correlation_id: str) -> None:
    """
    Définit le correlation_id pour le contexte actuel.
    
    Args:
        correlation_id: ID unique de corrélation
    """
    _correlation_id.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """
    Récupère le correlation_id du contexte actuel.
    
    Returns:
        Correlation ID ou None si non défini
    """
    return _correlation_id.get()


def generate_correlation_id() -> str:
    """
    Génère un nouveau correlation_id unique.
    
    Returns:
        Nouveau UUID comme correlation_id
    """
    return str(uuid.uuid4())


def set_application_id(application_id: str) -> None:
    """
    Définit l'application_id pour le contexte actuel.
    
    Args:
        application_id: ID de la demande de prêt
    """
    _application_id.set(application_id)


def get_application_id() -> Optional[str]:
    """
    Récupère l'application_id du contexte actuel.
    
    Returns:
        Application ID ou None si non défini
    """
    return _application_id.get()


def set_agent_id(agent_id: str) -> None:
    """
    Définit l'agent_id pour le contexte actuel.
    
    Args:
        agent_id: Identifiant de l'agent
    """
    _agent_id.set(agent_id)


def get_agent_id() -> str:
    """
    Récupère l'agent_id du contexte actuel.
    
    Returns:
        Agent ID
    """
    return _agent_id.get()


# =============================================================================
# Processeurs Structlog
# =============================================================================

def add_correlation_id(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Ajoute le correlation_id au log s'il existe.
    
    Si aucun correlation_id n'est défini, en génère un nouveau.
    """
    correlation_id = get_correlation_id()
    if correlation_id is None:
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)
    event_dict["correlation_id"] = correlation_id
    return event_dict


def add_application_id(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Ajoute l'application_id au log s'il existe."""
    application_id = get_application_id()
    if application_id is not None:
        event_dict["application_id"] = application_id
    return event_dict


def add_agent_context(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Ajoute le contexte de l'agent (agent_id)."""
    event_dict["agent_id"] = get_agent_id()
    return event_dict


def add_timestamp(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Ajoute un timestamp ISO 8601 UTC."""
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def add_caller_info(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Ajoute les informations de l'appelant (fichier:fonction:ligne).
    
    Ignore les frames de structlog et logging pour trouver le vrai appelant.
    """
    import traceback
    
    # Trouver la frame de l'appelant (ignorer structlog, logging, ce module)
    ignore_modules = {"structlog", "logging", "logging_config"}
    
    for frame_info in traceback.extract_stack():
        filename = frame_info.filename
        # Ignorer les modules internes
        if any(mod in filename for mod in ignore_modules):
            continue
        # Ignorer les fichiers de la bibliothèque standard
        if "site-packages" in filename or "lib/python" in filename:
            continue
        
        # Extraire le nom de fichier court
        short_filename = os.path.basename(filename)
        event_dict["caller"] = f"{short_filename}:{frame_info.name}:{frame_info.lineno}"
        break
    
    return event_dict


def rename_event_key(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Renomme 'event' en 'message' pour compatibilité avec certains outils."""
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict


# =============================================================================
# Configuration du Logging
# =============================================================================

_logging_configured = False


def configure_logging(
    agent_id: str = "unknown",
    log_level: str = "INFO",
    json_format: bool = True,
    include_caller_info: bool = True,
) -> None:
    """
    Configure le logging structuré pour l'application.
    
    Args:
        agent_id: Identifiant de l'agent (sera inclus dans tous les logs)
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
        json_format: True pour JSON, False pour format console lisible
        include_caller_info: Inclure fichier:fonction:ligne dans les logs
    
    Example:
        configure_logging(
            agent_id="agent-risk-analyst",
            log_level="INFO",
            json_format=True,
        )
    """
    global _logging_configured
    
    if _logging_configured:
        return
    
    # Définir l'agent_id dans le contexte
    set_agent_id(agent_id)
    
    # Récupérer le niveau de log depuis l'environnement ou l'argument
    level_str = os.getenv("LOG_LEVEL", log_level).upper()
    log_level_num = getattr(logging, level_str, logging.INFO)
    
    # Configurer le logging standard Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level_num,
    )
    
    # Construire la chaîne de processeurs
    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        add_timestamp,
        add_correlation_id,
        add_application_id,
        add_agent_context,
    ]
    
    if include_caller_info:
        processors.append(add_caller_info)
    
    # Processeur final selon le format désiré
    if json_format or os.getenv("LOG_FORMAT", "json").lower() == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    # Configurer structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    _logging_configured = True


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Obtient un logger configuré.
    
    Args:
        name: Nom optionnel du logger
        
    Returns:
        Logger structlog configuré
    """
    if not _logging_configured:
        configure_logging()
    
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """
    Lie des variables au contexte du logger pour tous les logs suivants.
    
    Args:
        **kwargs: Clés-valeurs à ajouter au contexte
        
    Example:
        bind_context(request_id="req-123", user_id="user-456")
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """
    Efface toutes les variables de contexte du logger.
    
    Utile entre les requêtes pour éviter la pollution du contexte.
    """
    structlog.contextvars.clear_contextvars()
    _correlation_id.set(None)
    _application_id.set(None)


# =============================================================================
# Context Manager pour le tracing
# =============================================================================

class LoggingContext:
    """
    Context manager pour définir le contexte de logging.
    
    Usage:
        with LoggingContext(correlation_id="req-123", application_id="APP-001"):
            logger.info("Processing...")
            # correlation_id et application_id sont automatiquement inclus
    """
    
    def __init__(
        self,
        correlation_id: Optional[str] = None,
        application_id: Optional[str] = None,
        **extra_context: Any,
    ):
        self.correlation_id = correlation_id or generate_correlation_id()
        self.application_id = application_id
        self.extra_context = extra_context
        self._old_correlation_id: Optional[str] = None
        self._old_application_id: Optional[str] = None
    
    def __enter__(self):
        # Sauvegarder le contexte précédent
        self._old_correlation_id = get_correlation_id()
        self._old_application_id = get_application_id()
        
        # Définir le nouveau contexte
        set_correlation_id(self.correlation_id)
        if self.application_id:
            set_application_id(self.application_id)
        
        if self.extra_context:
            bind_context(**self.extra_context)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restaurer le contexte précédent
        if self._old_correlation_id:
            set_correlation_id(self._old_correlation_id)
        if self._old_application_id:
            set_application_id(self._old_application_id)
        
        return False

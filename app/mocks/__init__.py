"""Module des services mock pour la simulation de l'écosystème assurance."""
from .base import MockService, MockServiceRegistry, MockServiceError
from .quote_engine import QuoteEngine
from .policy_admin import PolicyAdmin
from .claims import ClaimsManagement
from .billing import BillingSystem
from .customer_hub import CustomerHub
from .document_mgmt import DocumentManagement
from .notifications import NotificationService
from .external_rating import ExternalRating

import json
from pathlib import Path
from app.config import DATA_DIR

# Registre global des services
registry = MockServiceRegistry()


def get_mock_data():
    """Charge toutes les données mock depuis les fichiers JSON."""
    mock_data_dir = DATA_DIR / "mock_data"
    data = {}

    for file_path in mock_data_dir.glob("*.json"):
        key = file_path.stem  # nom du fichier sans extension
        with open(file_path, "r", encoding="utf-8") as f:
            data[key] = json.load(f)

    return data


def init_mock_services():
    """Initialise tous les services mock avec les données."""
    data = get_mock_data()

    # Enregistrer chaque service
    registry.register("quote_engine", QuoteEngine(data.get("quotes", [])))
    registry.register("policy_admin", PolicyAdmin(data.get("policies", [])))
    registry.register("claims", ClaimsManagement(data.get("claims", [])))
    registry.register("billing", BillingSystem(data.get("invoices", [])))
    registry.register("customer_hub", CustomerHub(data.get("customers", [])))
    registry.register("document_mgmt", DocumentManagement(data.get("documents", [])))
    registry.register("notifications", NotificationService())
    registry.register("external_rating", ExternalRating(data.get("rates", {})))

    return registry


def get_service(service_id: str):
    """Récupère un service mock par son ID."""
    return registry.get(service_id)


__all__ = [
    "MockService",
    "MockServiceRegistry",
    "MockServiceError",
    "QuoteEngine",
    "PolicyAdmin",
    "ClaimsManagement",
    "BillingSystem",
    "CustomerHub",
    "DocumentManagement",
    "NotificationService",
    "ExternalRating",
    "get_mock_data",
    "init_mock_services",
    "get_service",
    "registry"
]

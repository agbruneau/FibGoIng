"""Configuration de l'application Interop Learning."""
from pathlib import Path

# Application
APP_NAME = "Interop Learning"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Plateforme d'apprentissage de l'interopérabilité en écosystème d'entreprise"

# Chemins
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "learning.db"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Contenu théorique
THEORY_CONTENT_DIR = Path(__file__).parent / "theory" / "content"

# Modules - définition des 16 modules du parcours
MODULES = [
    {"id": 1, "title": "Introduction à l'Interopérabilité", "level": 1, "pillar": None},
    {"id": 2, "title": "Domaine Métier - Assurance Dommage", "level": 1, "pillar": None},
    {"id": 3, "title": "Design d'API REST", "level": 2, "pillar": "applications"},
    {"id": 4, "title": "API Gateway et Patterns de Façade", "level": 2, "pillar": "applications"},
    {"id": 5, "title": "Patterns Avancés d'Intégration Applicative", "level": 2, "pillar": "applications"},
    {"id": 6, "title": "Fondamentaux du Messaging", "level": 3, "pillar": "events"},
    {"id": 7, "title": "Architecture Event-Driven", "level": 3, "pillar": "events"},
    {"id": 8, "title": "Transactions Distribuées et Saga", "level": 3, "pillar": "events"},
    {"id": 9, "title": "ETL et Traitement Batch", "level": 4, "pillar": "data"},
    {"id": 10, "title": "CDC et Streaming de Données", "level": 4, "pillar": "data"},
    {"id": 11, "title": "Qualité et Gouvernance des Données", "level": 4, "pillar": "data"},
    {"id": 12, "title": "Résilience et Tolérance aux Pannes", "level": 5, "pillar": "cross_cutting"},
    {"id": 13, "title": "Observabilité", "level": 5, "pillar": "cross_cutting"},
    {"id": 14, "title": "Sécurité des Intégrations", "level": 5, "pillar": "cross_cutting"},
    {"id": 15, "title": "Décisions d'Architecture", "level": 6, "pillar": None},
    {"id": 16, "title": "Projet Final - Écosystème Complet", "level": 6, "pillar": None},
]

# Niveaux
LEVELS = [
    {"id": 1, "title": "Fondations"},
    {"id": 2, "title": "Intégration Applications", "icon": "🔗"},
    {"id": 3, "title": "Intégration Événements", "icon": "⚡"},
    {"id": 4, "title": "Intégration Données", "icon": "📊"},
    {"id": 5, "title": "Patterns Transversaux"},
    {"id": 6, "title": "Synthèse et Architecture"},
]

# Sandbox
SANDBOX_DEFAULT_LATENCY = 50  # ms
SANDBOX_FAILURE_PROBABILITY = 0.0  # 0-1

# Mock services
MOCK_SERVICES = [
    {"id": "quote_engine", "name": "Quote Engine", "latency": 50},
    {"id": "policy_admin", "name": "Policy Admin System", "latency": 30},
    {"id": "claims", "name": "Claims Management", "latency": 40},
    {"id": "billing", "name": "Billing System", "latency": 30},
    {"id": "customer_hub", "name": "Customer Hub", "latency": 20},
    {"id": "document_mgmt", "name": "Document Management", "latency": 60},
    {"id": "notifications", "name": "Notification Service", "latency": 20},
    {"id": "external_rating", "name": "External Rating API", "latency": 200},
]

# Couleurs des piliers
PILLAR_COLORS = {
    "applications": {"primary": "#3B82F6", "name": "Bleu"},  # Bleu
    "events": {"primary": "#F97316", "name": "Orange"},       # Orange
    "data": {"primary": "#22C55E", "name": "Vert"},           # Vert
    "cross_cutting": {"primary": "#8B5CF6", "name": "Violet"}, # Violet
}

"""Module d'intégration applicative - Gateway, BFF et patterns avancés."""

from app.integration.applications.gateway import APIGateway
from app.integration.applications.bff import BFFMobile, BFFCourtier
from app.integration.applications.composition import Customer360Composer
from app.integration.applications.acl import LegacyPASAdapter

__all__ = [
    "APIGateway",
    "BFFMobile",
    "BFFCourtier",
    "Customer360Composer",
    "LegacyPASAdapter"
]

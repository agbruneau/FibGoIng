"""Configuration pytest."""
import pytest
import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Crée un event loop pour la session de tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Initialise la base de données de test."""
    from app.database import init_db
    await init_db()

"""Tests pour Feature 1.6 - Module 2 Domaine Assurance."""
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport


def test_module2_content_files():
    """Vérifie que les fichiers de contenu du module 2 existent."""
    base = Path("app/theory/content/02_domaine_assurance")
    assert base.is_dir(), "Le dossier 02_domaine_assurance n'existe pas"
    assert (base / "01_processus.md").exists()
    assert (base / "02_entites.md").exists()
    assert (base / "03_systemes.md").exists()
    assert (base / "04_integration.md").exists()


@pytest.mark.asyncio
async def test_module2_entities():
    """Vérifie que le contenu du module 2 mentionne les entités."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/theory/modules/2")
        assert r.status_code == 200
        content = r.json()["content"].lower()
        for entity in ["quote", "policy", "claim", "invoice", "customer"]:
            assert entity in content, f"Entity {entity} not found in content"


@pytest.mark.asyncio
async def test_module2_systems():
    """Vérifie que le contenu du module 2 mentionne les systèmes."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/theory/modules/2")
        content = r.json()["content"].lower()
        assert "quote engine" in content
        assert "policy" in content
        assert "billing" in content

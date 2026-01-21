"""Tests pour Feature 1.5 - Module 1 Introduction."""
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport


def test_content_files():
    """Vérifie que les fichiers de contenu existent."""
    base = Path("app/theory/content/01_introduction")
    assert base.is_dir(), "Le dossier 01_introduction n'existe pas"
    assert (base / "01_definition.md").exists(), "01_definition.md manquant"
    assert (base / "02_trois_piliers.md").exists(), "02_trois_piliers.md manquant"
    assert (base / "03_enjeux.md").exists(), "03_enjeux.md manquant"
    assert (base / "04_patterns_overview.md").exists(), "04_patterns_overview.md manquant"


def test_renderer():
    """Vérifie que le renderer Markdown fonctionne."""
    from app.theory.renderer import render_markdown
    html = render_markdown("# Test\n**bold**")
    assert "<h1" in html  # h1 peut avoir des attributs
    assert "</h1>" in html
    assert "<strong>" in html or "<b>" in html


@pytest.mark.asyncio
async def test_module1_content():
    """Vérifie que le contenu du module 1 contient les termes clés."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/theory/modules/1")
        assert r.status_code == 200
        content = r.json()["content"].lower()
        assert "interopérabilité" in content or "interoperabilite" in content


@pytest.mark.asyncio
async def test_module1_has_pillars():
    """Vérifie que le module 1 mentionne les trois piliers."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/theory/modules/1")
        content = r.json()["content"].lower()
        assert "application" in content
        assert "événement" in content or "evenement" in content
        assert "données" in content or "donnees" in content

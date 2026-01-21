"""Tests pour Feature 1.4 - API Progression."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_get_progress():
    """Vérifie que l'API de progression retourne les données attendues."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/progress")
        assert r.status_code == 200
        data = r.json()
        assert "completed_modules" in data
        assert "total_modules" in data
        assert data["total_modules"] == 16


@pytest.mark.asyncio
async def test_get_modules():
    """Vérifie que la liste des modules est retournée."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/theory/modules")
        assert r.status_code == 200
        modules = r.json()
        assert len(modules) == 16


@pytest.mark.asyncio
async def test_get_single_module():
    """Vérifie qu'un module individuel peut être récupéré."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/theory/modules/1")
        assert r.status_code == 200
        module = r.json()
        assert "title" in module
        assert "content" in module


@pytest.mark.asyncio
async def test_complete_module():
    """Vérifie qu'un module peut être marqué comme complété."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/theory/modules/1/complete")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_module_not_found():
    """Vérifie qu'un module inexistant retourne 404."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/theory/modules/999")
        assert r.status_code == 404

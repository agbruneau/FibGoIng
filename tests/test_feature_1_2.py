"""Tests pour Feature 1.2 - Application FastAPI."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_app_responds():
    """Vérifie que l'application répond sur /."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/")
        assert r.status_code == 200


def test_config():
    """Vérifie que la configuration est accessible."""
    from app.config import APP_NAME, DATABASE_PATH
    assert APP_NAME == "Interop Learning"
    assert DATABASE_PATH is not None


@pytest.mark.asyncio
async def test_database_tables():
    """Vérifie que les tables SQLite sont créées."""
    from app.database import init_db, get_connection
    await init_db()
    async with get_connection() as db:
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in await cursor.fetchall()]
        assert "learner_progress" in tables
        assert "sandbox_sessions" in tables


@pytest.mark.asyncio
async def test_health_endpoint():
    """Vérifie l'endpoint de santé."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert "version" in data

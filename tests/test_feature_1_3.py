"""Tests pour Feature 1.3 - Interface Utilisateur Base."""
import pytest
from httpx import AsyncClient, ASGITransport
from bs4 import BeautifulSoup


@pytest.mark.asyncio
async def test_dark_theme():
    """Vérifie que le thème sombre est appliqué."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/")
        assert "dark" in r.text or "bg-gray-900" in r.text


@pytest.mark.asyncio
async def test_sidebar_exists():
    """Vérifie que la sidebar existe."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/")
        soup = BeautifulSoup(r.text, "html.parser")
        sidebar = soup.find(id="sidebar") or soup.find(class_="sidebar")
        assert sidebar is not None


@pytest.mark.asyncio
async def test_htmx_loaded():
    """Vérifie que HTMX est chargé."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/")
        assert "htmx" in r.text.lower()


@pytest.mark.asyncio
async def test_tailwind_loaded():
    """Vérifie que Tailwind CSS est chargé."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/")
        assert "tailwind" in r.text.lower()

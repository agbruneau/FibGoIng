"""Tests pour Feature 2.3 : Module 4 - Gateway & BFF."""
import pytest
from pathlib import Path


class TestModule4Content:
    """Tests du contenu théorique Module 4."""

    def test_module4_directory_exists(self):
        """Le répertoire du module 4 existe."""
        path = Path("app/theory/content/04_api_gateway")
        assert path.exists(), "Le répertoire 04_api_gateway doit exister"

    def test_gateway_intro_exists(self):
        """Le contenu d'introduction au gateway existe."""
        files = list(Path("app/theory/content/04_api_gateway").glob("*.md"))
        assert len(files) >= 3, "Le module 4 doit avoir au moins 3 fichiers MD"

    def test_bff_content_exists(self):
        """Le contenu sur le BFF existe."""
        path = Path("app/theory/content/04_api_gateway")
        files = list(path.glob("*bff*.md"))
        assert len(files) >= 1, "Un fichier sur le BFF doit exister"


class TestGatewayImplementation:
    """Tests de l'implémentation du Gateway."""

    def test_gateway_module_exists(self):
        """Le module gateway existe."""
        path = Path("app/integration/applications/gateway.py")
        assert path.exists(), "gateway.py doit exister"

    def test_gateway_class_importable(self):
        """La classe APIGateway peut être importée."""
        from app.integration.applications.gateway import APIGateway
        assert APIGateway is not None

    def test_gateway_has_routing(self):
        """Le gateway a la fonctionnalité de routing."""
        path = Path("app/integration/applications/gateway.py")
        content = path.read_text(encoding="utf-8")
        assert "route" in content.lower(), "Le gateway doit avoir du routing"

    def test_gateway_has_rate_limiting(self):
        """Le gateway a le rate limiting."""
        path = Path("app/integration/applications/gateway.py")
        content = path.read_text(encoding="utf-8")
        assert "rate" in content.lower(), "Le gateway doit avoir du rate limiting"


class TestBFFImplementation:
    """Tests de l'implémentation du BFF."""

    def test_bff_module_exists(self):
        """Le module BFF existe."""
        path = Path("app/integration/applications/bff.py")
        assert path.exists(), "bff.py doit exister"

    def test_bff_mobile_class_exists(self):
        """La classe BFFMobile existe."""
        from app.integration.applications.bff import BFFMobile
        assert BFFMobile is not None

    def test_bff_courtier_class_exists(self):
        """La classe BFFCourtier existe."""
        from app.integration.applications.bff import BFFCourtier
        assert BFFCourtier is not None


class TestGatewayScenarios:
    """Tests des scénarios Gateway."""

    def test_app02_scenario_exists(self):
        """Le scénario APP-02 (Gateway) existe."""
        from app.sandbox.scenarios import get_scenario

        scenario = get_scenario("APP-02")
        assert scenario is not None, "Le scénario APP-02 doit exister"
        assert "gateway" in scenario["title"].lower() or "Gateway" in scenario["title"]

    def test_app03_scenario_exists(self):
        """Le scénario APP-03 (BFF) existe."""
        from app.sandbox.scenarios import get_scenario

        scenario = get_scenario("APP-03")
        assert scenario is not None, "Le scénario APP-03 doit exister"
        assert "bff" in scenario["title"].lower() or "mobile" in scenario["title"].lower()


class TestModule4Renderer:
    """Tests du rendu du Module 4."""

    @pytest.mark.asyncio
    async def test_render_module4_content(self):
        """Le contenu du module 4 peut être rendu."""
        from app.theory.renderer import render_module_content

        html = await render_module_content(4)
        assert html is not None
        assert len(html) > 100, "Le HTML rendu doit avoir du contenu"

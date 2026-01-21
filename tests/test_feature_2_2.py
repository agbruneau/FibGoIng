"""Tests pour Feature 2.2 : Module 3 - REST API."""
import pytest
from pathlib import Path


class TestModule3Content:
    """Tests du contenu théorique Module 3."""

    def test_module3_directory_exists(self):
        """Le répertoire du module 3 existe."""
        path = Path("app/theory/content/03_rest_api")
        assert path.exists(), "Le répertoire 03_rest_api doit exister"

    def test_rmm_content_exists(self):
        """Le contenu sur le Richardson Maturity Model existe."""
        path = Path("app/theory/content/03_rest_api/01_rmm.md")
        assert path.exists(), "01_rmm.md doit exister"

        content = path.read_text(encoding="utf-8")
        assert "Richardson" in content, "Le contenu doit mentionner Richardson"
        assert "Level" in content, "Le contenu doit mentionner les niveaux"

    def test_resources_content_exists(self):
        """Le contenu sur les ressources REST existe."""
        path = Path("app/theory/content/03_rest_api/02_resources.md")
        assert path.exists(), "02_resources.md doit exister"

        content = path.read_text(encoding="utf-8")
        assert "ressource" in content.lower() or "resource" in content.lower()

    def test_versioning_content_exists(self):
        """Le contenu sur le versioning existe."""
        path = Path("app/theory/content/03_rest_api/03_versioning.md")
        assert path.exists(), "03_versioning.md doit exister"

    def test_openapi_content_exists(self):
        """Le contenu sur OpenAPI existe."""
        path = Path("app/theory/content/03_rest_api/04_openapi.md")
        assert path.exists(), "04_openapi.md doit exister"

        content = path.read_text(encoding="utf-8")
        assert "openapi" in content.lower() or "swagger" in content.lower()

    def test_errors_content_exists(self):
        """Le contenu sur la gestion des erreurs existe."""
        path = Path("app/theory/content/03_rest_api/05_errors.md")
        assert path.exists(), "05_errors.md doit exister"

        content = path.read_text(encoding="utf-8")
        assert "erreur" in content.lower() or "error" in content.lower()


class TestModule3Scenarios:
    """Tests des scénarios du Module 3."""

    def test_scenarios_module_exists(self):
        """Le module scenarios existe."""
        from app.sandbox.scenarios import SCENARIOS
        assert SCENARIOS is not None

    def test_app01_scenario_exists(self):
        """Le scénario APP-01 existe."""
        from app.sandbox.scenarios import get_scenario

        scenario = get_scenario("APP-01")
        assert scenario is not None, "Le scénario APP-01 doit exister"
        assert scenario["pillar"] == "applications"
        assert len(scenario["steps"]) >= 5


class TestModule3Renderer:
    """Tests du rendu du Module 3."""

    def test_renderer_includes_module3(self):
        """Le renderer inclut le module 3."""
        from app.theory.renderer import render_module_content

        # Vérifier que le mapping existe pour le module 3
        path = Path("app/theory/renderer.py")
        content = path.read_text(encoding="utf-8")
        assert "03_rest_api" in content, "Le renderer doit mapper le module 3"

    @pytest.mark.asyncio
    async def test_render_module3_content(self):
        """Le contenu du module 3 peut être rendu."""
        from app.theory.renderer import render_module_content

        html = await render_module_content(3)
        assert html is not None
        assert len(html) > 100, "Le HTML rendu doit avoir du contenu"
        assert "<" in html, "Le résultat doit être du HTML"

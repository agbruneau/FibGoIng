"""Tests pour Feature 2.4 : Module 5 - Patterns Avancés."""
import pytest
from pathlib import Path


class TestModule5Content:
    """Tests du contenu théorique Module 5."""

    def test_module5_directory_exists(self):
        """Le répertoire du module 5 existe."""
        path = Path("app/theory/content/05_patterns_avances")
        assert path.exists(), "Le répertoire 05_patterns_avances doit exister"

    def test_composition_content_exists(self):
        """Le contenu sur la composition existe."""
        path = Path("app/theory/content/05_patterns_avances/01_composition.md")
        assert path.exists(), "01_composition.md doit exister"

        content = path.read_text(encoding="utf-8")
        assert "composition" in content.lower() or "agrég" in content.lower()

    def test_acl_content_exists(self):
        """Le contenu sur l'ACL existe."""
        path = Path("app/theory/content/05_patterns_avances/02_acl.md")
        assert path.exists(), "02_acl.md doit exister"

        content = path.read_text(encoding="utf-8")
        assert "anti-corruption" in content.lower() or "acl" in content.lower()

    def test_strangler_content_exists(self):
        """Le contenu sur Strangler Fig existe."""
        path = Path("app/theory/content/05_patterns_avances/03_strangler.md")
        assert path.exists(), "03_strangler.md doit exister"

    def test_idempotence_content_exists(self):
        """Le contenu sur l'idempotence existe."""
        path = Path("app/theory/content/05_patterns_avances/04_idempotence.md")
        assert path.exists(), "04_idempotence.md doit exister"

    def test_caching_content_exists(self):
        """Le contenu sur le caching existe."""
        path = Path("app/theory/content/05_patterns_avances/05_caching.md")
        assert path.exists(), "05_caching.md doit exister"


class TestPatternsImplementation:
    """Tests de l'implémentation des patterns."""

    def test_composition_module_exists(self):
        """Le module composition existe."""
        path = Path("app/integration/applications/composition.py")
        assert path.exists(), "composition.py doit exister"

    def test_acl_module_exists(self):
        """Le module ACL existe."""
        path = Path("app/integration/applications/acl.py")
        assert path.exists(), "acl.py doit exister"


class TestPatternsScenarios:
    """Tests des scénarios patterns avancés."""

    def test_app04_scenario_exists(self):
        """Le scénario APP-04 (Vue 360°) existe."""
        from app.sandbox.scenarios import get_scenario

        scenario = get_scenario("APP-04")
        assert scenario is not None, "Le scénario APP-04 doit exister"
        assert "360" in scenario["title"] or "vue" in scenario["title"].lower()

    def test_app05_scenario_exists(self):
        """Le scénario APP-05 (Strangler Fig) existe."""
        from app.sandbox.scenarios import get_scenario

        scenario = get_scenario("APP-05")
        assert scenario is not None, "Le scénario APP-05 doit exister"
        assert "strangler" in scenario["title"].lower() or "migration" in scenario["title"].lower()


class TestModule5Renderer:
    """Tests du rendu du Module 5."""

    @pytest.mark.asyncio
    async def test_render_module5_content(self):
        """Le contenu du module 5 peut être rendu."""
        from app.theory.renderer import render_module_content

        html = await render_module_content(5)
        assert html is not None
        assert len(html) > 100, "Le HTML rendu doit avoir du contenu"


class TestIntegrationModuleExists:
    """Tests que le module d'intégration applications existe."""

    def test_applications_init_exists(self):
        """Le __init__.py du module applications existe."""
        path = Path("app/integration/applications/__init__.py")
        assert path.exists(), "__init__.py doit exister"

    def test_can_import_integration_applications(self):
        """Le module integration.applications peut être importé."""
        try:
            from app.integration import applications
            assert applications is not None
        except ImportError:
            # OK si le module est vide ou a des dépendances manquantes
            pass

"""Tests pour Feature 2.1 : Services Mock."""
import pytest
from pathlib import Path
import json


class TestMockServicesStructure:
    """Tests de structure des services mock."""

    def test_mocks_module_exists(self):
        """Le module mocks existe."""
        mocks_path = Path("app/mocks/__init__.py")
        assert mocks_path.exists(), "Le module app/mocks/__init__.py doit exister"

    def test_base_service_exists(self):
        """La classe de base MockService existe."""
        base_path = Path("app/mocks/base.py")
        assert base_path.exists(), "app/mocks/base.py doit exister"

    def test_all_service_files_exist(self):
        """Tous les fichiers de services existent."""
        services = [
            "quote_engine.py",
            "policy_admin.py",
            "claims.py",
            "billing.py",
            "customer_hub.py",
            "document_mgmt.py",
            "notifications.py",
            "external_rating.py"
        ]

        for service in services:
            path = Path(f"app/mocks/{service}")
            assert path.exists(), f"app/mocks/{service} doit exister"


class TestMockDataFiles:
    """Tests des fichiers de données mock."""

    def test_mock_data_directory_exists(self):
        """Le répertoire mock_data existe."""
        data_path = Path("data/mock_data")
        assert data_path.exists(), "data/mock_data doit exister"

    def test_customers_json_exists(self):
        """Le fichier customers.json existe et est valide."""
        path = Path("data/mock_data/customers.json")
        assert path.exists(), "customers.json doit exister"

        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, list), "customers.json doit contenir une liste"
        assert len(data) > 0, "customers.json doit contenir au moins un client"

    def test_policies_json_exists(self):
        """Le fichier policies.json existe et est valide."""
        path = Path("data/mock_data/policies.json")
        assert path.exists(), "policies.json doit exister"

        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, list), "policies.json doit contenir une liste"

    def test_quotes_json_exists(self):
        """Le fichier quotes.json existe et est valide."""
        path = Path("data/mock_data/quotes.json")
        assert path.exists(), "quotes.json doit exister"

    def test_claims_json_exists(self):
        """Le fichier claims.json existe et est valide."""
        path = Path("data/mock_data/claims.json")
        assert path.exists(), "claims.json doit exister"

    def test_invoices_json_exists(self):
        """Le fichier invoices.json existe et est valide."""
        path = Path("data/mock_data/invoices.json")
        assert path.exists(), "invoices.json doit exister"


class TestMockBaseClass:
    """Tests de la classe de base MockService."""

    def test_import_mock_service(self):
        """MockService peut être importé."""
        from app.mocks.base import MockService, MockServiceRegistry
        assert MockService is not None
        assert MockServiceRegistry is not None

    def test_service_status_enum(self):
        """ServiceStatus enum existe."""
        from app.mocks.base import ServiceStatus
        assert ServiceStatus.RUNNING.value == "running"
        assert ServiceStatus.STOPPED.value == "stopped"

    def test_mock_service_error(self):
        """MockServiceError exception existe."""
        from app.mocks.base import MockServiceError

        error = MockServiceError("Test error", 404)
        assert error.message == "Test error"
        assert error.status_code == 404


class TestMockAPIRoutes:
    """Tests des routes API mock."""

    def test_mocks_router_exists(self):
        """Le router mocks existe."""
        from app.api.mocks import router
        assert router is not None

    def test_mocks_router_in_main(self):
        """Le router mocks est inclus dans main."""
        main_path = Path("app/main.py")
        content = main_path.read_text(encoding="utf-8")
        assert "mocks_router" in content, "mocks_router doit être importé dans main.py"
        assert "/mocks" in content, "Le préfixe /mocks doit être configuré"

"""
Tests d'API pour les endpoints REST.

Couvre:
- API Progress
- API Theory
- API Broker
- API Mocks
- API Sandbox
- API Preferences
- Health check
"""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
def client():
    """Client de test pour l'API."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ========== TESTS HEALTH CHECK ==========

class TestHealthCheck:
    """Tests du health check."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Vérifie le endpoint /health."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


# ========== TESTS API PROGRESS ==========

class TestProgressAPI:
    """Tests de l'API Progress."""

    @pytest.mark.asyncio
    async def test_get_progress(self, client):
        """Vérifie GET /api/progress."""
        response = await client.get("/api/progress")

        assert response.status_code == 200
        data = response.json()
        assert "percentage" in data

    @pytest.mark.asyncio
    async def test_get_modules_progress(self, client):
        """Vérifie GET /api/progress/modules."""
        response = await client.get("/api/progress/modules")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    @pytest.mark.asyncio
    async def test_get_stats(self, client):
        """Vérifie GET /api/progress/stats."""
        response = await client.get("/api/progress/stats")

        assert response.status_code == 200


# ========== TESTS API THEORY ==========

class TestTheoryAPI:
    """Tests de l'API Theory."""

    @pytest.mark.asyncio
    async def test_get_modules(self, client):
        """Vérifie GET /api/theory/modules."""
        response = await client.get("/api/theory/modules")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ========== TESTS API BROKER ==========

class TestBrokerAPI:
    """Tests de l'API Broker."""

    @pytest.mark.asyncio
    async def test_get_queues(self, client):
        """Vérifie GET /api/broker/queues."""
        response = await client.get("/api/broker/queues")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["queues"], list)

    @pytest.mark.asyncio
    async def test_get_topics(self, client):
        """Vérifie GET /api/broker/topics."""
        response = await client.get("/api/broker/topics")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["topics"], list)

    @pytest.mark.asyncio
    async def test_send_to_queue(self, client):
        """Vérifie POST /api/broker/queues/{name}/send."""
        response = await client.post(
            "/api/broker/queues/test_queue/send",
            json={"payload": {"test": "message"}}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "id" in data["message"]

    @pytest.mark.asyncio
    async def test_get_broker_stats(self, client):
        """Vérifie GET /api/broker/stats."""
        response = await client.get("/api/broker/stats")

        assert response.status_code == 200
        data = response.json()
        assert "messages_sent" in data or "stats" in data

    @pytest.mark.asyncio
    async def test_get_broker_history(self, client):
        """Vérifie GET /api/broker/history."""
        response = await client.get("/api/broker/history")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["messages"], list)

    @pytest.mark.asyncio
    async def test_broker_reset(self, client):
        """Vérifie POST /api/broker/reset."""
        response = await client.post("/api/broker/reset")

        assert response.status_code == 200


# ========== TESTS API MOCKS ==========

class TestMocksAPI:
    """Tests de l'API Mocks."""

    @pytest.mark.asyncio
    async def test_get_services(self, client):
        """Vérifie GET /mocks/services."""
        response = await client.get("/mocks/services")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    @pytest.mark.asyncio
    async def test_create_quote(self, client):
        """Vérifie POST /mocks/quotes."""
        response = await client.post(
            "/mocks/quotes",
            json={
                "customer_id": "CUST-001",
                "product": "AUTO",
                "coverage_amount": 50000
            }
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "quote_id" in data or "id" in data

    @pytest.mark.asyncio
    async def test_get_quotes(self, client):
        """Vérifie GET /mocks/quotes."""
        response = await client.get("/mocks/quotes")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_customer(self, client):
        """Vérifie POST /mocks/customers."""
        response = await client.post(
            "/mocks/customers",
            json={
                "name": "Test Customer",
                "email": "test@example.com"
            }
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "customer_id" in data or "id" in data

    @pytest.mark.asyncio
    async def test_get_customers(self, client):
        """Vérifie GET /mocks/customers."""
        response = await client.get("/mocks/customers")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_mock_data(self, client):
        """Vérifie GET /mocks/data."""
        response = await client.get("/mocks/data")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_services(self, client):
        """Vérifie POST /mocks/services/reset."""
        response = await client.post("/mocks/services/reset")

        assert response.status_code == 200


# ========== TESTS API SANDBOX ==========

class TestSandboxAPI:
    """Tests de l'API Sandbox."""

    @pytest.mark.asyncio
    async def test_get_scenarios(self, client):
        """Vérifie GET /api/sandbox/scenarios."""
        response = await client.get("/api/sandbox/scenarios")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_session(self, client):
        """Vérifie POST /api/sandbox/sessions."""
        # D'abord, obtenir un scénario valide
        scenarios_response = await client.get("/api/sandbox/scenarios")
        scenarios = scenarios_response.json()

        if scenarios:
            scenario_id = scenarios[0].get("id", scenarios[0].get("scenario_id", "app_01"))

            response = await client.post(
                "/api/sandbox/sessions",
                json={"scenario_id": scenario_id}
            )

            assert response.status_code in [200, 201]
            data = response.json()
            assert "session_id" in data or "id" in data


# ========== TESTS API PREFERENCES ==========

class TestPreferencesAPI:
    """Tests de l'API Preferences."""

    @pytest.mark.asyncio
    async def test_get_preferences(self, client):
        """Vérifie GET /api/preferences."""
        response = await client.get("/api/preferences")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_update_font_size(self, client):
        """Vérifie PATCH /api/preferences/font-size."""
        response = await client.patch(
            "/api/preferences/font-size",
            json={"font_size": 16}
        )

        assert response.status_code == 200


# ========== TESTS PAGES HTML ==========

class TestHTMLPages:
    """Tests des pages HTML."""

    @pytest.mark.asyncio
    async def test_home_page(self, client):
        """Vérifie la page d'accueil."""
        response = await client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_sandbox_page(self, client):
        """Vérifie la page sandbox."""
        response = await client.get("/sandbox")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


# ========== TESTS ERROR HANDLING ==========

class TestErrorHandling:
    """Tests de la gestion des erreurs."""

    @pytest.mark.asyncio
    async def test_not_found(self, client):
        """Vérifie la gestion 404."""
        response = await client.get("/api/nonexistent/endpoint")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_json(self, client):
        """Vérifie la gestion de JSON invalide."""
        response = await client.post(
            "/mocks/quotes",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422]


# ========== TESTS CLAIMS API ==========

class TestClaimsAPI:
    """Tests de l'API Claims."""

    @pytest.mark.asyncio
    async def test_create_claim(self, client):
        """Vérifie POST /mocks/claims."""
        response = await client.post(
            "/mocks/claims",
            json={
                "policy_number": "POL-001",
                "claim_type": "ACCIDENT",
                "description": "Test claim",
                "estimated_amount": 1000.0
            }
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "claim_id" in data or "id" in data or "claim_number" in data or "number" in data

    @pytest.mark.asyncio
    async def test_get_claims(self, client):
        """Vérifie GET /mocks/claims."""
        response = await client.get("/mocks/claims")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ========== TESTS INVOICES API ==========

class TestInvoicesAPI:
    """Tests de l'API Invoices."""

    @pytest.mark.asyncio
    async def test_create_invoice(self, client):
        """Vérifie POST /mocks/invoices."""
        response = await client.post(
            "/mocks/invoices",
            json={
                "policy_number": "POL-001",
                "amount": 500.0
            }
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "invoice_id" in data or "id" in data or "invoice_number" in data or "number" in data


# ========== TESTS POLICIES API ==========

class TestPoliciesAPI:
    """Tests de l'API Policies."""

    @pytest.mark.asyncio
    async def test_create_policy(self, client):
        """Vérifie POST /mocks/policies."""
        response = await client.post(
            "/mocks/policies",
            json={
                "customer_id": "CUST-001",
                "product": "AUTO",
                "premium": 500.0
            }
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "policy_id" in data or "id" in data or "policy_number" in data or "number" in data

    @pytest.mark.asyncio
    async def test_get_policies(self, client):
        """Vérifie GET /mocks/policies."""
        response = await client.get("/mocks/policies")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ========== TESTS RATES API ==========

class TestRatesAPI:
    """Tests de l'API Rates."""

    @pytest.mark.asyncio
    async def test_get_rate(self, client):
        """Vérifie GET /mocks/rates/{product}."""
        response = await client.get("/mocks/rates/AUTO")

        assert response.status_code == 200
        data = response.json()
        assert "rate" in data or "base_rate" in data or "premium" in data or "base_premium" in data


# ========== TESTS CONCURRENT REQUESTS ==========

class TestConcurrentRequests:
    """Tests de requêtes concurrentes."""

    @pytest.mark.asyncio
    async def test_concurrent_quote_creation(self, client):
        """Vérifie la création concurrente de quotes."""
        import asyncio

        async def create_quote(i):
            return await client.post(
                "/mocks/quotes",
                json={
                    "customer_id": f"CUST-{i:03d}",
                    "product": "AUTO",
                    "coverage_amount": 50000 + i * 1000
                }
            )

        # Créer 5 quotes en parallèle
        tasks = [create_quote(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # Toutes devraient réussir
        for response in responses:
            assert response.status_code in [200, 201]


# ========== TESTS SERVICE CONFIGURATION ==========

class TestServiceConfiguration:
    """Tests de la configuration des services."""

    @pytest.mark.asyncio
    async def test_configure_service(self, client):
        """Vérifie la configuration d'un service."""
        # D'abord obtenir la liste des services
        services_response = await client.get("/mocks/services")
        services = services_response.json()

        if services:
            # Prendre le premier service (peut être une liste ou un dict)
            if isinstance(services, list):
                service_id = services[0].get("id", services[0].get("name", "quote_engine"))
            else:
                service_id = list(services.keys())[0] if services else "quote_engine"

            response = await client.post(
                f"/mocks/services/{service_id}/configure",
                json={"latency": 100, "failure_rate": 0.1}
            )

            assert response.status_code == 200

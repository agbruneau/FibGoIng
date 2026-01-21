"""
Tests d'intégration end-to-end.

Couvre:
- Flux complet de souscription d'assurance
- Intégration Broker + Event Store
- Intégration Circuit Breaker + Services
- Pipeline ETL complet
- Scénarios de résilience
"""
import pytest
import asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.integration.events.broker import MessageBroker, get_broker, reset_broker
from app.integration.events.event_store import EventStore, get_event_store, reset_event_store
from app.integration.events.saga import SubscriptionSaga
from app.integration.cross_cutting.circuit_breaker import CircuitBreaker, reset_all_circuit_breakers
from app.integration.cross_cutting.retry import RetryPolicy, Fallback, ResilientCall
from app.integration.data.etl_pipeline import ETLPipeline, reset_etl_pipeline
from app.mocks.base import MockService, MockServiceRegistry, ServiceStatus


@pytest.fixture
def client():
    """Client de test pour l'API."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def reset_all_singletons():
    """Réinitialise tous les singletons avant chaque test."""
    reset_broker()
    reset_event_store()
    reset_all_circuit_breakers()
    reset_etl_pipeline()
    yield
    reset_broker()
    reset_event_store()
    reset_all_circuit_breakers()
    reset_etl_pipeline()


# ========== TESTS FLUX SOUSCRIPTION COMPLET ==========

class TestSubscriptionFlow:
    """Tests du flux complet de souscription."""

    @pytest.mark.asyncio
    async def test_full_subscription_saga(self):
        """Test du flux complet: devis -> police -> facture -> docs -> notification."""
        saga = SubscriptionSaga()

        result = await saga.execute({
            "quote_id": "QUO-001",
            "customer_id": "CUST-001",
            "product": "AUTO",
            "premium": 500.0
        })

        assert result["status"] == "COMPLETED"
        assert "policy_id" in result["context"]
        assert "invoice_id" in result["context"]
        assert "document_ids" in result["context"]
        assert result["context"]["notifications_sent"] is True

    @pytest.mark.asyncio
    async def test_subscription_with_event_sourcing(self):
        """Test de souscription avec event sourcing."""
        event_store = get_event_store()
        saga = SubscriptionSaga()

        # Exécuter la saga
        result = await saga.execute({"quote_id": "QUO-002"})
        policy_id = result["context"]["policy_id"]

        # Enregistrer les événements dans l'event store
        await event_store.append(policy_id, {
            "type": "PolicyCreated",
            "data": {
                "policy_number": policy_id,
                "customer_id": "CUST-001",
                "product": "AUTO",
                "premium": 500.0
            }
        })

        await event_store.append(policy_id, {
            "type": "PolicyActivated",
            "data": {
                "start_date": "2024-01-01",
                "end_date": "2025-01-01"
            }
        })

        # Vérifier les événements
        events = await event_store.get_events(policy_id)
        assert len(events) == 2
        assert events[0].type == "PolicyCreated"
        assert events[1].type == "PolicyActivated"


# ========== TESTS BROKER + EVENT STORE ==========

class TestBrokerEventStoreIntegration:
    """Tests d'intégration Broker et Event Store."""

    @pytest.mark.asyncio
    async def test_event_from_broker_to_store(self):
        """Test: message du broker déclenche événement dans le store."""
        broker = get_broker()
        event_store = get_event_store()
        processed_events = []

        async def event_handler(payload):
            # Quand un message arrive, l'enregistrer dans l'event store
            await event_store.append(
                payload["aggregate_id"],
                {
                    "type": payload["event_type"],
                    "data": payload["data"]
                }
            )
            processed_events.append(payload)

        # S'abonner au topic
        await broker.subscribe("policy.events", event_handler)

        # Publier un événement
        await broker.publish("policy.events", {
            "aggregate_id": "POL-INTEGRATION-001",
            "event_type": "PolicyCreated",
            "data": {"premium": 500}
        })

        # Attendre le traitement
        await asyncio.sleep(0.2)

        # Vérifier que l'événement est dans le store
        events = await event_store.get_events("POL-INTEGRATION-001")
        assert len(events) == 1
        assert events[0].type == "PolicyCreated"

    @pytest.mark.asyncio
    async def test_queue_processing_with_event_sourcing(self):
        """Test: traitement de queue avec event sourcing."""
        broker = get_broker()
        event_store = get_event_store()

        # Envoyer plusieurs commandes
        for i in range(3):
            await broker.send_to_queue("commands", {
                "command": "CreatePolicy",
                "aggregate_id": f"POL-BATCH-{i:03d}",
                "data": {"premium": 100 * (i + 1)}
            })

        # Traiter les commandes
        for _ in range(3):
            message = await broker.receive_from_queue("commands", timeout=1.0)
            if message:
                await event_store.append(
                    message.payload["aggregate_id"],
                    {
                        "type": "PolicyCreated",
                        "data": message.payload["data"]
                    }
                )

        # Vérifier les statistiques
        stats = event_store.get_stats()
        assert stats["total_events"] == 3
        assert stats["aggregates_count"] == 3


# ========== TESTS CIRCUIT BREAKER + SERVICES ==========

class TestCircuitBreakerServiceIntegration:
    """Tests d'intégration Circuit Breaker et Services."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_protects_service_calls(self):
        """Test: circuit breaker protège les appels de service."""
        service = MockService(name="protected_service", default_latency=10)
        cb = CircuitBreaker(
            name="protected_service_cb",
            failure_threshold=3,
            reset_timeout=0.5
        )

        async def call_service():
            async with cb:
                return await service.execute("get_data", lambda: {"data": "value"})

        # Appels réussis
        for _ in range(5):
            result = await call_service()
            assert result == {"data": "value"}

        # Injecter des pannes
        service.inject_failure(1.0)

        # Les appels échouent et ouvrent le circuit
        from app.integration.cross_cutting.circuit_breaker import CircuitBreakerError
        failures = 0
        for _ in range(5):
            try:
                await call_service()
            except (CircuitBreakerError, Exception):
                failures += 1

        assert failures >= 3
        assert cb.state == "OPEN"

    @pytest.mark.asyncio
    async def test_resilient_service_call(self):
        """Test: appel de service avec retry, timeout et fallback."""
        service = MockService(name="unreliable", default_latency=10)
        call_count = 0

        async def unreliable_call():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Service temporary failure")
            return await service.execute("get", lambda: {"success": True})

        resilient = ResilientCall(
            timeout=1.0,
            max_retries=5,
            initial_delay=0.01,
            fallback_value={"fallback": True}
        )

        result = await resilient.execute(unreliable_call)

        assert result == {"success": True}
        assert call_count == 3


# ========== TESTS ETL COMPLET ==========

class TestETLIntegration:
    """Tests d'intégration ETL complet."""

    @pytest.mark.asyncio
    async def test_etl_claims_to_dwh(self):
        """Test: ETL des sinistres vers le DWH."""
        pipeline = ETLPipeline(latency_ms=10)

        result = await pipeline.run({
            "source": "claims",
            "destination": "dwh",
            "transforms": ["calculate_totals", "normalize_dates"]
        })

        assert result["status"] == "completed"
        assert result["processed_records"] == 5

        # Vérifier les données transformées
        data = pipeline.get_destination_data("dwh")
        assert len(data) == 5
        assert "amount_with_tax" in data[0]
        assert "date_normalized" in data[0]

    @pytest.mark.asyncio
    async def test_etl_multiple_sources_aggregation(self):
        """Test: ETL de plusieurs sources vers une destination."""
        pipeline = ETLPipeline(latency_ms=10)

        # ETL Claims
        await pipeline.run({
            "source": "claims",
            "destination": "analytics_lake"
        })

        # ETL Policies
        await pipeline.run({
            "source": "policies",
            "destination": "analytics_lake"
        })

        # ETL Customers
        await pipeline.run({
            "source": "customers",
            "destination": "analytics_lake"
        })

        # Vérifier l'agrégation
        data = pipeline.get_destination_data("analytics_lake")
        assert len(data) == 12  # 5 claims + 4 policies + 3 customers

        stats = pipeline.get_stats()
        assert stats["jobs_completed"] == 3

    @pytest.mark.asyncio
    async def test_etl_with_filtering(self):
        """Test: ETL avec filtrage des données."""
        pipeline = ETLPipeline(latency_ms=10)

        # Extraire seulement les polices actives
        result = await pipeline.run({
            "source": "policies",
            "destination": "active_policies",
            "filters": {"status": "ACTIVE"}
        })

        assert result["status"] == "completed"
        assert result["processed_records"] == 3  # 3 polices ACTIVE sur 4


# ========== TESTS RÉSILIENCE ==========

class TestResilienceScenarios:
    """Tests de scénarios de résilience."""

    @pytest.mark.asyncio
    async def test_saga_compensation_on_failure(self):
        """Test: compensation de saga sur échec."""
        saga = SubscriptionSaga()
        compensated = []

        # Modifier une étape pour échouer
        async def failing_generate_docs(ctx):
            raise ValueError("Document generation failed")

        # Remplacer l'action dans la définition des étapes
        for step in saga.steps:
            if step.name == "generate_documents":
                step.action = failing_generate_docs
                break

        result = await saga.execute({"quote_id": "QUO-FAIL"})

        assert result["status"] == "COMPENSATED"
        # Les étapes précédentes devraient être compensées
        assert "create_invoice" in result["compensated_steps"]
        assert "create_policy" in result["compensated_steps"]

    @pytest.mark.asyncio
    async def test_message_retry_and_dlq(self):
        """Test: retry de message et DLQ."""
        broker = get_broker()
        failed_messages = []

        async def failing_handler(payload):
            failed_messages.append(payload)
            raise ValueError("Always fails")

        await broker.subscribe("fail_topic", failing_handler, max_retries=2)
        await broker.publish("fail_topic", {"data": "will fail"})

        # Attendre les retries et le passage en DLQ
        await asyncio.sleep(1.0)

        # Vérifier la DLQ
        dlq_message = await broker.receive_from_dlq("fail_topic")
        assert dlq_message is not None
        assert dlq_message.payload == {"data": "will fail"}

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test: récupération du circuit breaker."""
        cb = CircuitBreaker(
            name="recovery_test",
            failure_threshold=2,
            success_threshold=2,
            reset_timeout=0.3
        )
        failures = 0
        successes = 0

        # Phase 1: Provoquer des échecs pour ouvrir le circuit
        for _ in range(3):
            try:
                async with cb:
                    raise ValueError("Failure")
            except Exception:
                failures += 1

        assert cb.state == "OPEN"

        # Phase 2: Attendre le timeout de reset
        await asyncio.sleep(0.4)
        assert cb.state == "HALF_OPEN"

        # Phase 3: Succès pour fermer le circuit
        for _ in range(2):
            async with cb:
                successes += 1

        assert cb.state == "CLOSED"


# ========== TESTS API E2E ==========

class TestAPIEndToEnd:
    """Tests end-to-end via l'API."""

    @pytest.mark.asyncio
    async def test_create_quote_and_policy_flow(self, client):
        """Test: flux création devis puis police via API."""
        # Créer un client
        customer_response = await client.post(
            "/mocks/customers",
            json={"name": "E2E Test Customer", "email": "e2e@test.com"}
        )
        assert customer_response.status_code in [200, 201]
        customer_data = customer_response.json()
        customer_id = customer_data.get("customer_id") or customer_data.get("id")

        # Créer un devis
        quote_response = await client.post(
            "/mocks/quotes",
            json={
                "customer_id": customer_id,
                "product": "HOME",
                "coverage_amount": 100000
            }
        )
        assert quote_response.status_code in [200, 201]
        quote_data = quote_response.json()
        quote_id = quote_data.get("quote_id") or quote_data.get("id")

        # Créer une police
        policy_response = await client.post(
            "/mocks/policies",
            json={
                "customer_id": customer_id,
                "product": "HOME",
                "premium": 1200.0
            }
        )
        assert policy_response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_broker_queue_flow_via_api(self, client):
        """Test: flux de messages queue via API."""
        # Envoyer un message
        send_response = await client.post(
            "/api/broker/queues/e2e_test_queue/send",
            json={"payload": {"test": "e2e", "timestamp": "2024-01-01"}}
        )
        assert send_response.status_code == 200

        # Vérifier les stats
        stats_response = await client.get("/api/broker/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats.get("messages_sent", 0) >= 1


# ========== TESTS PERFORMANCE ==========

class TestPerformanceScenarios:
    """Tests de scénarios de performance."""

    @pytest.mark.asyncio
    async def test_high_throughput_queue(self):
        """Test: débit élevé sur queue."""
        broker = get_broker()
        message_count = 100

        # Envoyer rapidement beaucoup de messages
        for i in range(message_count):
            await broker.send_to_queue("perf_queue", {"index": i})

        # Vérifier que tous sont envoyés
        stats = broker.get_stats()
        assert stats["messages_sent"] >= message_count

    @pytest.mark.asyncio
    async def test_concurrent_sagas(self):
        """Test: sagas concurrentes."""
        async def run_saga(quote_id):
            saga = SubscriptionSaga()
            return await saga.execute({"quote_id": quote_id})

        # Exécuter plusieurs sagas en parallèle
        tasks = [run_saga(f"QUO-CONC-{i:03d}") for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Toutes devraient réussir
        for result in results:
            assert result["status"] == "COMPLETED"


# ========== TESTS OBSERVABILITÉ ==========

class TestObservability:
    """Tests d'observabilité et monitoring."""

    @pytest.mark.asyncio
    async def test_event_store_stats(self):
        """Test: statistiques de l'event store."""
        event_store = get_event_store()

        # Ajouter plusieurs événements
        for i in range(10):
            await event_store.append(
                f"AGG-{i % 3:03d}",  # 3 aggregates différents
                {"type": f"Event{i % 2}", "data": {"value": i}}
            )

        stats = event_store.get_stats()

        assert stats["total_events"] == 10
        assert stats["aggregates_count"] == 3

    @pytest.mark.asyncio
    async def test_broker_stats_after_operations(self):
        """Test: statistiques du broker après opérations."""
        broker = get_broker()

        # Opérations diverses
        await broker.send_to_queue("q1", {"data": 1})
        await broker.send_to_queue("q1", {"data": 2})

        async def handler(p):
            pass

        await broker.subscribe("t1", handler)
        await broker.publish("t1", {"data": 3})

        await asyncio.sleep(0.1)

        stats = broker.get_stats()

        assert stats["messages_sent"] == 3
        assert stats["active_subscriptions"] == 1

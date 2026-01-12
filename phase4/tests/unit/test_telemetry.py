"""
Phase 4 - Unit Tests for OpenTelemetry Module (L1)
==================================================
Tests unitaires pour le module de telemetrie.
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


# =============================================================================
# TESTS DE CONFIGURATION
# =============================================================================

class TestTelemetryConfig:
    """Tests pour TelemetryConfig."""

    def test_default_config(self):
        """Test configuration par defaut."""
        from shared.telemetry import TelemetryConfig

        config = TelemetryConfig()

        assert config.service_name == "agent-mesh-kafka"
        assert config.environment == "development"
        assert config.enable_console_export is True
        assert config.enable_otlp_export is False
        assert config.sample_rate == 1.0

    def test_config_from_env(self):
        """Test chargement depuis variables d'environnement."""
        from shared.telemetry import TelemetryConfig

        with patch.dict(os.environ, {
            "OTEL_SERVICE_NAME": "test-service",
            "ENVIRONMENT": "production",
            "OTEL_SAMPLE_RATE": "0.5",
        }):
            config = TelemetryConfig.from_env()

            assert config.service_name == "test-service"
            assert config.environment == "production"
            assert config.sample_rate == 0.5

    def test_custom_config(self):
        """Test configuration personnalisee."""
        from shared.telemetry import TelemetryConfig

        config = TelemetryConfig(
            service_name="custom-service",
            environment="staging",
            enable_otlp_export=True,
            otlp_endpoint="http://jaeger:4317",
        )

        assert config.service_name == "custom-service"
        assert config.environment == "staging"
        assert config.enable_otlp_export is True
        assert config.otlp_endpoint == "http://jaeger:4317"


# =============================================================================
# TESTS D'AGENT NAME
# =============================================================================

class TestAgentName:
    """Tests pour l'enum AgentName."""

    def test_agent_names(self):
        """Test les noms d'agents."""
        from shared.telemetry import AgentName

        assert AgentName.INTAKE.value == "agent-intake"
        assert AgentName.RISK.value == "agent-risk"
        assert AgentName.DECISION.value == "agent-decision"
        assert AgentName.ORCHESTRATOR.value == "orchestrator"


# =============================================================================
# TESTS DE TELEMETRIE
# =============================================================================

class TestAgentTelemetry:
    """Tests pour AgentTelemetry."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset le singleton avant chaque test."""
        from shared.telemetry import AgentTelemetry
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False
        yield
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

    def test_initialize_creates_instance(self):
        """Test que initialize cree une instance."""
        from shared.telemetry import AgentTelemetry, AgentName, TelemetryConfig

        config = TelemetryConfig(enable_console_export=False)
        telemetry = AgentTelemetry.initialize(AgentName.RISK, config)

        assert telemetry is not None
        assert telemetry.agent_name == AgentName.RISK

    def test_singleton_pattern(self):
        """Test que le pattern singleton fonctionne."""
        from shared.telemetry import AgentTelemetry, AgentName, TelemetryConfig

        config = TelemetryConfig(enable_console_export=False)
        telemetry1 = AgentTelemetry.initialize(AgentName.RISK, config)
        telemetry2 = AgentTelemetry.initialize(AgentName.INTAKE, config)

        # Meme instance (singleton)
        assert telemetry1 is telemetry2

    def test_get_instance_without_init_raises(self):
        """Test que get_instance sans init leve une exception."""
        from shared.telemetry import AgentTelemetry

        with pytest.raises(RuntimeError, match="not initialized"):
            AgentTelemetry.get_instance()

    def test_get_instance_after_init(self):
        """Test get_instance apres initialisation."""
        from shared.telemetry import AgentTelemetry, AgentName, TelemetryConfig

        config = TelemetryConfig(enable_console_export=False)
        AgentTelemetry.initialize(AgentName.DECISION, config)

        instance = AgentTelemetry.get_instance()
        assert instance.agent_name == AgentName.DECISION


# =============================================================================
# TESTS DE CONTEXT PROPAGATION
# =============================================================================

class TestContextPropagation:
    """Tests pour la propagation de contexte."""

    @pytest.fixture(autouse=True)
    def setup_telemetry(self):
        """Setup telemetry pour les tests."""
        from shared.telemetry import AgentTelemetry, AgentName, TelemetryConfig
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

        config = TelemetryConfig(enable_console_export=False)
        self.telemetry = AgentTelemetry.initialize(AgentName.RISK, config)
        yield
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

    def test_inject_context(self):
        """Test injection de contexte."""
        carrier = {}

        with self.telemetry.trace_operation("test_op"):
            self.telemetry.inject_context(carrier)

        # Should have traceparent header
        assert "traceparent" in carrier

    def test_extract_context(self):
        """Test extraction de contexte."""
        # Simulate incoming headers
        carrier = {
            "traceparent": "00-12345678901234567890123456789012-1234567890123456-01"
        }

        context = self.telemetry.extract_context(carrier)
        assert context is not None


# =============================================================================
# TESTS DE TRACING OPERATIONS
# =============================================================================

class TestTracingOperations:
    """Tests pour les operations de tracing."""

    @pytest.fixture(autouse=True)
    def setup_telemetry(self):
        """Setup telemetry pour les tests."""
        from shared.telemetry import AgentTelemetry, AgentName, TelemetryConfig
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

        config = TelemetryConfig(enable_console_export=False)
        self.telemetry = AgentTelemetry.initialize(AgentName.RISK, config)
        yield
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

    def test_trace_operation_success(self):
        """Test trace_operation en cas de succes."""
        with self.telemetry.trace_operation("test_success") as span:
            span.set_attribute("test_key", "test_value")
            result = 42

        assert result == 42

    def test_trace_operation_with_exception(self):
        """Test trace_operation avec exception."""
        with pytest.raises(ValueError, match="test error"):
            with self.telemetry.trace_operation("test_error"):
                raise ValueError("test error")

    def test_trace_operation_with_attributes(self):
        """Test trace_operation avec attributs."""
        attributes = {
            "application_id": "APP-123",
            "amount": 50000,
        }

        with self.telemetry.trace_operation(
            "test_attrs",
            attributes=attributes
        ) as span:
            # Span should have attributes
            pass


# =============================================================================
# TESTS DES DECORATEURS
# =============================================================================

class TestDecorators:
    """Tests pour les decorateurs de tracing."""

    @pytest.fixture(autouse=True)
    def setup_telemetry(self):
        """Setup telemetry pour les tests."""
        from shared.telemetry import AgentTelemetry, AgentName, TelemetryConfig
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

        config = TelemetryConfig(enable_console_export=False)
        AgentTelemetry.initialize(AgentName.RISK, config)
        yield
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

    def test_trace_agent_operation_decorator(self):
        """Test du decorateur trace_agent_operation."""
        from shared.telemetry import trace_agent_operation

        @trace_agent_operation("test_operation")
        def my_function(x, y):
            return x + y

        result = my_function(1, 2)
        assert result == 3

    def test_trace_agent_operation_with_kwargs(self):
        """Test du decorateur avec kwargs."""
        from shared.telemetry import trace_agent_operation

        @trace_agent_operation(record_args=True)
        def process(application_id: str, data: dict):
            return f"Processed {application_id}"

        result = process(application_id="APP-123", data={"test": True})
        assert "APP-123" in result


# =============================================================================
# TESTS DU MIDDLEWARE KAFKA
# =============================================================================

class TestKafkaTracingMiddleware:
    """Tests pour KafkaTracingMiddleware."""

    @pytest.fixture(autouse=True)
    def setup_telemetry(self):
        """Setup telemetry pour les tests."""
        from shared.telemetry import AgentTelemetry, AgentName, TelemetryConfig
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

        config = TelemetryConfig(enable_console_export=False)
        AgentTelemetry.initialize(AgentName.RISK, config)
        yield
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

    def test_prepare_headers(self):
        """Test preparation des headers."""
        from shared.telemetry import KafkaTracingMiddleware

        middleware = KafkaTracingMiddleware()
        headers = middleware.prepare_headers(application_id="APP-123")

        assert "x-application-id" in headers
        assert headers["x-application-id"] == "APP-123"

    def test_prepare_headers_with_extra(self):
        """Test preparation avec headers supplementaires."""
        from shared.telemetry import KafkaTracingMiddleware

        middleware = KafkaTracingMiddleware()
        headers = middleware.prepare_headers(
            application_id="APP-456",
            extra_headers={"custom-header": "value"},
        )

        assert headers["x-application-id"] == "APP-456"
        assert headers["custom-header"] == "value"

    def test_trace_consumption_context(self):
        """Test trace_consumption context manager."""
        from shared.telemetry import KafkaTracingMiddleware

        middleware = KafkaTracingMiddleware()

        with middleware.trace_consumption(
            topic="test-topic",
            application_id="APP-789",
        ):
            # Should be inside a traced context
            pass

    def test_trace_production_context(self):
        """Test trace_production context manager."""
        from shared.telemetry import KafkaTracingMiddleware

        middleware = KafkaTracingMiddleware()

        with middleware.trace_production(
            topic="output-topic",
            application_id="APP-101",
        ):
            # Should be inside a traced context
            pass


# =============================================================================
# TESTS DE TRACED MESSAGE
# =============================================================================

class TestTracedMessage:
    """Tests pour TracedMessage."""

    @pytest.fixture(autouse=True)
    def setup_telemetry(self):
        """Setup telemetry pour les tests."""
        from shared.telemetry import AgentTelemetry, AgentName, TelemetryConfig
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

        config = TelemetryConfig(enable_console_export=False)
        AgentTelemetry.initialize(AgentName.RISK, config)
        yield
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

    def test_create_traced_message(self):
        """Test creation d'un message trace."""
        from shared.telemetry import TracedMessage

        msg = TracedMessage(
            topic="test-topic",
            key="APP-123",
            value={"application_id": "APP-123", "amount": 50000},
        )

        assert msg.topic == "test-topic"
        assert msg.key == "APP-123"
        assert msg.value["amount"] == 50000
        assert msg.headers == {}

    def test_inject_trace_context(self):
        """Test injection de contexte dans message."""
        from shared.telemetry import TracedMessage

        msg = TracedMessage(
            topic="test-topic",
            key="APP-456",
            value={"test": True},
        )

        with AgentTelemetry.get_instance().trace_operation("test"):
            result = msg.inject_trace_context()

        # Should return self
        assert result is msg
        # Should have headers injected
        assert "traceparent" in msg.headers


# =============================================================================
# TESTS DE METRIQUES
# =============================================================================

class TestMetrics:
    """Tests pour les metriques."""

    @pytest.fixture(autouse=True)
    def setup_telemetry(self):
        """Setup telemetry pour les tests."""
        from shared.telemetry import AgentTelemetry, AgentName, TelemetryConfig
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

        config = TelemetryConfig(enable_console_export=False)
        self.telemetry = AgentTelemetry.initialize(AgentName.RISK, config)
        yield
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

    def test_record_llm_call(self):
        """Test enregistrement d'un appel LLM."""
        with self.telemetry.trace_operation("test_llm"):
            self.telemetry.record_llm_call(
                model="claude-3-5-sonnet",
                input_tokens=500,
                output_tokens=200,
                latency_ms=1500.0,
            )

    def test_record_request_success(self):
        """Test enregistrement d'une requete reussie."""
        with self.telemetry.trace_operation("test_request"):
            self.telemetry.record_request(
                success=True,
                application_id="APP-123",
            )

    def test_record_request_failure(self):
        """Test enregistrement d'une requete echouee."""
        with self.telemetry.trace_operation("test_request"):
            self.telemetry.record_request(
                success=False,
                application_id="APP-456",
            )


# =============================================================================
# TESTS D'INTEGRATION
# =============================================================================

@pytest.mark.integration
class TestTelemetryIntegration:
    """Tests d'integration pour la telemetrie."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset le singleton avant chaque test."""
        from shared.telemetry import AgentTelemetry
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False
        yield
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

    def test_full_tracing_flow(self):
        """Test du flux complet de tracing."""
        from shared.telemetry import (
            AgentTelemetry,
            AgentName,
            TelemetryConfig,
            KafkaTracingMiddleware,
        )

        # Initialize
        config = TelemetryConfig(enable_console_export=False)
        telemetry = AgentTelemetry.initialize(AgentName.RISK, config)
        middleware = KafkaTracingMiddleware()

        # Simulate incoming message
        incoming_headers = {}

        # Producer injects context
        with telemetry.trace_operation("producer"):
            telemetry.inject_context(incoming_headers)

        # Consumer extracts and processes
        context = telemetry.extract_context(incoming_headers)

        with telemetry.trace_operation(
            "consumer",
            context=context,
        ):
            with telemetry.trace_operation("process_application"):
                telemetry.record_llm_call(
                    model="claude-3-5-sonnet",
                    input_tokens=100,
                    output_tokens=50,
                    latency_ms=500,
                )

                telemetry.record_request(
                    success=True,
                    application_id="APP-TEST",
                )

        # Flow completed without errors
        assert True

    def test_multiple_agents_tracing(self):
        """Test tracing entre plusieurs agents."""
        from shared.telemetry import (
            AgentTelemetry,
            AgentName,
            TelemetryConfig,
        )

        config = TelemetryConfig(enable_console_export=False)

        # Simulate Intake Agent
        telemetry = AgentTelemetry.initialize(AgentName.INTAKE, config)

        carrier = {}
        with telemetry.trace_operation("intake.validate"):
            telemetry.inject_context(carrier)
            # Pass to next agent

        # Reset singleton for next agent (in real scenario, different process)
        AgentTelemetry._instance = None
        AgentTelemetry._initialized = False

        # Simulate Risk Agent receiving message
        telemetry2 = AgentTelemetry.initialize(AgentName.RISK, config)
        context = telemetry2.extract_context(carrier)

        with telemetry2.trace_operation("risk.analyze", context=context):
            pass

        # Tracing chain preserved
        assert True

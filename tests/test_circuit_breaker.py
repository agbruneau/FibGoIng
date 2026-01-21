"""
Tests unitaires pour le Circuit Breaker.

Couvre:
- Transitions d'états (CLOSED, OPEN, HALF_OPEN)
- Seuils de failure et success
- Timeout de reset
- Context manager (sync et async)
- Décorateur protect
- Registry global
"""
import pytest
import asyncio
import time
from app.integration.cross_cutting.circuit_breaker import (
    CircuitBreaker, CircuitState, CircuitBreakerError, CircuitBreakerConfig,
    get_circuit_breaker, get_all_circuit_breakers, reset_all_circuit_breakers
)


@pytest.fixture
def circuit_breaker():
    """Crée un nouveau circuit breaker pour chaque test."""
    return CircuitBreaker(
        name="test_cb",
        failure_threshold=3,
        success_threshold=2,
        reset_timeout=0.5  # Court pour les tests
    )


@pytest.fixture(autouse=True)
def reset_registry():
    """Réinitialise le registry avant chaque test."""
    reset_all_circuit_breakers()
    yield
    reset_all_circuit_breakers()


# ========== TESTS ÉTAT INITIAL ==========

class TestInitialState:
    """Tests de l'état initial du circuit breaker."""

    def test_initial_state_is_closed(self, circuit_breaker):
        """Vérifie que l'état initial est CLOSED."""
        assert circuit_breaker.state == "CLOSED"

    def test_initial_stats_are_zero(self, circuit_breaker):
        """Vérifie que les stats sont à zéro."""
        status = circuit_breaker.get_status()

        assert status["stats"]["total_calls"] == 0
        assert status["stats"]["successful_calls"] == 0
        assert status["stats"]["failed_calls"] == 0
        assert status["stats"]["rejected_calls"] == 0

    def test_config_is_set_correctly(self, circuit_breaker):
        """Vérifie la configuration."""
        status = circuit_breaker.get_status()

        assert status["config"]["failure_threshold"] == 3
        assert status["config"]["success_threshold"] == 2
        assert status["config"]["reset_timeout"] == 0.5


# ========== TESTS CONTEXT MANAGER ASYNC ==========

class TestAsyncContextManager:
    """Tests du context manager asynchrone."""

    @pytest.mark.asyncio
    async def test_successful_call_increments_stats(self, circuit_breaker):
        """Vérifie qu'un appel réussi incrémente les stats."""
        async with circuit_breaker:
            pass  # Succès

        status = circuit_breaker.get_status()
        assert status["stats"]["total_calls"] == 1
        assert status["stats"]["successful_calls"] == 1

    @pytest.mark.asyncio
    async def test_failed_call_increments_failure_count(self, circuit_breaker):
        """Vérifie qu'un échec incrémente le compteur."""
        with pytest.raises(ValueError):
            async with circuit_breaker:
                raise ValueError("Test error")

        status = circuit_breaker.get_status()
        assert status["stats"]["failed_calls"] == 1
        assert status["failure_count"] == 1

    @pytest.mark.asyncio
    async def test_multiple_failures_open_circuit(self, circuit_breaker):
        """Vérifie que plusieurs échecs ouvrent le circuit."""
        for _ in range(3):  # failure_threshold = 3
            with pytest.raises(ValueError):
                async with circuit_breaker:
                    raise ValueError("Error")

        assert circuit_breaker.state == "OPEN"

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self, circuit_breaker):
        """Vérifie que le circuit ouvert rejette les appels."""
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                async with circuit_breaker:
                    raise ValueError("Error")

        # Essayer un appel sur circuit ouvert
        with pytest.raises(CircuitBreakerError) as exc_info:
            async with circuit_breaker:
                pass

        assert exc_info.value.state == CircuitState.OPEN
        assert circuit_breaker.get_status()["stats"]["rejected_calls"] == 1


# ========== TESTS CONTEXT MANAGER SYNC ==========

class TestSyncContextManager:
    """Tests du context manager synchrone."""

    def test_sync_successful_call(self, circuit_breaker):
        """Vérifie un appel sync réussi."""
        with circuit_breaker:
            pass  # Succès

        assert circuit_breaker.get_status()["stats"]["successful_calls"] == 1

    def test_sync_failed_call(self, circuit_breaker):
        """Vérifie un appel sync échoué."""
        with pytest.raises(RuntimeError):
            with circuit_breaker:
                raise RuntimeError("Sync error")

        assert circuit_breaker.get_status()["stats"]["failed_calls"] == 1

    def test_sync_open_circuit_rejects(self, circuit_breaker):
        """Vérifie que le circuit sync ouvert rejette."""
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                with circuit_breaker:
                    raise RuntimeError("Error")

        with pytest.raises(CircuitBreakerError):
            with circuit_breaker:
                pass


# ========== TESTS TRANSITIONS D'ÉTATS ==========

class TestStateTransitions:
    """Tests des transitions d'états."""

    @pytest.mark.asyncio
    async def test_closed_to_open_on_threshold(self, circuit_breaker):
        """Vérifie la transition CLOSED -> OPEN."""
        assert circuit_breaker.state == "CLOSED"

        for _ in range(3):
            with pytest.raises(Exception):
                async with circuit_breaker:
                    raise Exception("Fail")

        assert circuit_breaker.state == "OPEN"

    @pytest.mark.asyncio
    async def test_open_to_half_open_after_timeout(self, circuit_breaker):
        """Vérifie la transition OPEN -> HALF_OPEN après timeout."""
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(Exception):
                async with circuit_breaker:
                    raise Exception("Fail")

        assert circuit_breaker.state == "OPEN"

        # Attendre le reset_timeout
        await asyncio.sleep(0.6)

        # Vérifier que l'état est passé en HALF_OPEN
        assert circuit_breaker.state == "HALF_OPEN"

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(self, circuit_breaker):
        """Vérifie la transition HALF_OPEN -> CLOSED sur succès."""
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(Exception):
                async with circuit_breaker:
                    raise Exception("Fail")

        # Attendre HALF_OPEN
        await asyncio.sleep(0.6)
        assert circuit_breaker.state == "HALF_OPEN"

        # 2 succès requis (success_threshold = 2)
        async with circuit_breaker:
            pass
        async with circuit_breaker:
            pass

        assert circuit_breaker.state == "CLOSED"

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self, circuit_breaker):
        """Vérifie la transition HALF_OPEN -> OPEN sur échec."""
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(Exception):
                async with circuit_breaker:
                    raise Exception("Fail")

        # Attendre HALF_OPEN
        await asyncio.sleep(0.6)
        assert circuit_breaker.state == "HALF_OPEN"

        # Un échec en HALF_OPEN réouvre le circuit
        with pytest.raises(Exception):
            async with circuit_breaker:
                raise Exception("Fail in half open")

        assert circuit_breaker.state == "OPEN"


# ========== TESTS DÉCORATEUR PROTECT ==========

class TestProtectDecorator:
    """Tests du décorateur protect."""

    @pytest.mark.asyncio
    async def test_protect_async_function(self, circuit_breaker):
        """Vérifie le décorateur sur fonction async."""
        @circuit_breaker.protect
        async def async_func():
            return "success"

        result = await async_func()

        assert result == "success"
        assert circuit_breaker.get_status()["stats"]["successful_calls"] == 1

    def test_protect_sync_function(self, circuit_breaker):
        """Vérifie le décorateur sur fonction sync."""
        @circuit_breaker.protect
        def sync_func():
            return "sync success"

        result = sync_func()

        assert result == "sync success"
        assert circuit_breaker.get_status()["stats"]["successful_calls"] == 1

    @pytest.mark.asyncio
    async def test_protect_propagates_exception(self, circuit_breaker):
        """Vérifie que l'exception est propagée."""
        @circuit_breaker.protect
        async def failing_func():
            raise ValueError("Protected failure")

        with pytest.raises(ValueError) as exc_info:
            await failing_func()

        assert "Protected failure" in str(exc_info.value)


# ========== TESTS FORÇAGE D'ÉTAT ==========

class TestForceState:
    """Tests du forçage d'état."""

    def test_force_open(self, circuit_breaker):
        """Vérifie force_open()."""
        circuit_breaker.force_open()

        assert circuit_breaker.state == "OPEN"

    def test_force_close(self, circuit_breaker):
        """Vérifie force_close()."""
        circuit_breaker.force_open()
        circuit_breaker.force_close()

        assert circuit_breaker.state == "CLOSED"

    @pytest.mark.asyncio
    async def test_force_open_rejects_calls(self, circuit_breaker):
        """Vérifie que force_open rejette les appels."""
        circuit_breaker.force_open()

        with pytest.raises(CircuitBreakerError):
            async with circuit_breaker:
                pass


# ========== TESTS RESET ==========

class TestReset:
    """Tests de la réinitialisation."""

    @pytest.mark.asyncio
    async def test_reset_clears_stats(self, circuit_breaker):
        """Vérifie que reset efface les stats."""
        async with circuit_breaker:
            pass

        circuit_breaker.reset()

        status = circuit_breaker.get_status()
        assert status["stats"]["total_calls"] == 0
        assert status["stats"]["successful_calls"] == 0

    @pytest.mark.asyncio
    async def test_reset_closes_circuit(self, circuit_breaker):
        """Vérifie que reset ferme le circuit."""
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(Exception):
                async with circuit_breaker:
                    raise Exception("Fail")

        assert circuit_breaker.state == "OPEN"

        circuit_breaker.reset()

        assert circuit_breaker.state == "CLOSED"


# ========== TESTS EVENT HISTORY ==========

class TestEventHistory:
    """Tests de l'historique des événements."""

    @pytest.mark.asyncio
    async def test_event_history_records_calls(self, circuit_breaker):
        """Vérifie l'enregistrement des appels."""
        async with circuit_breaker:
            pass

        history = circuit_breaker.get_event_history()

        assert len(history) >= 1
        assert any(e["type"] == "call_success" for e in history)

    @pytest.mark.asyncio
    async def test_event_history_records_state_changes(self, circuit_breaker):
        """Vérifie l'enregistrement des changements d'état."""
        for _ in range(3):
            with pytest.raises(Exception):
                async with circuit_breaker:
                    raise Exception("Fail")

        history = circuit_breaker.get_event_history()

        assert any(e["type"] == "state_change" for e in history)

    @pytest.mark.asyncio
    async def test_event_history_limit(self, circuit_breaker):
        """Vérifie la limite de l'historique."""
        for _ in range(10):
            async with circuit_breaker:
                pass

        history = circuit_breaker.get_event_history(limit=5)

        assert len(history) == 5


# ========== TESTS REGISTRY GLOBAL ==========

class TestGlobalRegistry:
    """Tests du registry global."""

    def test_get_circuit_breaker_creates_new(self):
        """Vérifie la création d'un nouveau circuit breaker."""
        cb = get_circuit_breaker("service_a", failure_threshold=5)

        assert cb is not None
        assert cb.name == "service_a"
        assert cb.config.failure_threshold == 5

    def test_get_circuit_breaker_returns_existing(self):
        """Vérifie que le même CB est retourné."""
        cb1 = get_circuit_breaker("service_b")
        cb2 = get_circuit_breaker("service_b")

        assert cb1 is cb2

    @pytest.mark.asyncio
    async def test_get_all_circuit_breakers(self):
        """Vérifie la récupération de tous les CBs."""
        get_circuit_breaker("cb_1")
        get_circuit_breaker("cb_2")
        get_circuit_breaker("cb_3")

        all_cbs = get_all_circuit_breakers()

        assert len(all_cbs) >= 3
        assert "cb_1" in all_cbs
        assert "cb_2" in all_cbs
        assert "cb_3" in all_cbs

    @pytest.mark.asyncio
    async def test_reset_all_circuit_breakers(self):
        """Vérifie la réinitialisation de tous les CBs."""
        cb1 = get_circuit_breaker("cb_reset_1")
        cb2 = get_circuit_breaker("cb_reset_2")

        # Utiliser les CBs
        async with cb1:
            pass
        async with cb2:
            pass

        reset_all_circuit_breakers()

        assert cb1.get_status()["stats"]["total_calls"] == 0
        assert cb2.get_status()["stats"]["total_calls"] == 0


# ========== TESTS RETRY_AFTER ==========

class TestRetryAfter:
    """Tests du calcul de retry_after."""

    @pytest.mark.asyncio
    async def test_retry_after_in_error(self, circuit_breaker):
        """Vérifie que retry_after est calculé."""
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(Exception):
                async with circuit_breaker:
                    raise Exception("Fail")

        # Essayer immédiatement
        with pytest.raises(CircuitBreakerError) as exc_info:
            async with circuit_breaker:
                pass

        # retry_after devrait être proche de reset_timeout (0.5s)
        assert exc_info.value.retry_after > 0
        assert exc_info.value.retry_after <= 0.5


# ========== TESTS ON_STATE_CHANGE CALLBACK ==========

class TestOnStateChangeCallback:
    """Tests du callback on_state_change."""

    @pytest.mark.asyncio
    async def test_on_state_change_called(self):
        """Vérifie que le callback est appelé."""
        callbacks = []

        def on_change(name, old_state, new_state):
            callbacks.append((name, old_state, new_state))

        cb = CircuitBreaker(
            name="cb_callback",
            failure_threshold=2,
            on_state_change=on_change
        )

        # Provoquer un changement d'état
        for _ in range(2):
            with pytest.raises(Exception):
                async with cb:
                    raise Exception("Fail")

        assert len(callbacks) >= 1
        assert callbacks[0][0] == "cb_callback"
        assert callbacks[0][2] == CircuitState.OPEN


# ========== TESTS SUCCESS RESETS FAILURE COUNT ==========

class TestSuccessResetsFailure:
    """Tests que le succès réinitialise le compteur d'échecs."""

    @pytest.mark.asyncio
    async def test_success_resets_failure_count_in_closed(self, circuit_breaker):
        """Vérifie que le succès reset le compteur en CLOSED."""
        # 2 échecs (moins que le threshold)
        for _ in range(2):
            with pytest.raises(Exception):
                async with circuit_breaker:
                    raise Exception("Fail")

        assert circuit_breaker.get_status()["failure_count"] == 2

        # Un succès reset le compteur
        async with circuit_breaker:
            pass

        assert circuit_breaker.get_status()["failure_count"] == 0


# ========== TESTS HALF_OPEN MAX CALLS ==========

class TestHalfOpenMaxCalls:
    """Tests de la limite d'appels en HALF_OPEN."""

    def test_init_validation_error(self):
        """Vérifie que l'initialisation échoue si half_open_max_calls < success_threshold."""
        with pytest.raises(ValueError):
            CircuitBreaker(
                name="invalid_cb",
                success_threshold=3,
                half_open_max_calls=2
            )

    @pytest.mark.asyncio
    async def test_half_open_allows_calls_up_to_threshold(self):
        """Vérifie qu'on peut faire le nombre d'appels requis."""
        cb = CircuitBreaker(
            name="cb_half_open_test",
            failure_threshold=2,
            success_threshold=2,
            reset_timeout=0.1,
            half_open_max_calls=2
        )

        # Ouvrir le circuit
        for _ in range(2):
            with pytest.raises(Exception):
                async with cb:
                    raise Exception("Fail")

        # Attendre HALF_OPEN
        await asyncio.sleep(0.15)
        assert cb.state == "HALF_OPEN"

        # Appel 1: Succès
        async with cb:
            pass

        assert cb.state == "HALF_OPEN"

        # Appel 2: Succès
        async with cb:
            pass

        assert cb.state == "CLOSED"

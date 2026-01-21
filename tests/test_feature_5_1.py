"""Tests pour Feature 5.1: Résilience & Modules 12-14."""
import pytest
import asyncio
from app.integration.cross_cutting.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerError
)
from app.integration.cross_cutting.retry import (
    RetryPolicy,
    BackoffStrategy,
    Fallback,
    Timeout,
    TimeoutError,
    ResilientCall
)
from app.integration.cross_cutting.observability import (
    StructuredLogger,
    Tracer,
    MetricsCollector
)
from app.integration.cross_cutting.security import (
    JWTManager,
    RBACManager,
    SecurityManager,
    Permission
)


# ============================================================
# Tests Circuit Breaker
# ============================================================

@pytest.mark.asyncio
async def test_circuit_breaker_initial_state():
    """Test que le circuit breaker démarre en état CLOSED."""
    cb = CircuitBreaker(name="test", failure_threshold=2)
    assert cb.state == "CLOSED"


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """Test que le circuit s'ouvre après le seuil d'échecs."""
    cb = CircuitBreaker(name="test", failure_threshold=2, reset_timeout=0.5)

    async def failing_operation():
        raise Exception("Failure")

    # Premier échec
    with pytest.raises(Exception):
        async with cb:
            await failing_operation()
    assert cb.state == "CLOSED"

    # Deuxième échec -> circuit ouvert
    with pytest.raises(Exception):
        async with cb:
            await failing_operation()
    assert cb.state == "OPEN"


@pytest.mark.asyncio
async def test_circuit_breaker_rejects_when_open():
    """Test que le circuit rejette les appels quand il est ouvert."""
    cb = CircuitBreaker(name="test", failure_threshold=1, reset_timeout=1.0)

    # Ouvrir le circuit
    with pytest.raises(Exception):
        async with cb:
            raise Exception("Failure")

    assert cb.state == "OPEN"

    # Tentative d'appel -> rejeté
    with pytest.raises(CircuitBreakerError):
        async with cb:
            pass


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_timeout():
    """Test que le circuit passe en HALF_OPEN après le timeout."""
    cb = CircuitBreaker(name="test", failure_threshold=1, reset_timeout=0.1)

    # Ouvrir le circuit
    with pytest.raises(Exception):
        async with cb:
            raise Exception("Failure")

    assert cb.state == "OPEN"

    # Attendre le reset timeout
    await asyncio.sleep(0.15)

    # Le circuit devrait être HALF_OPEN
    assert cb.state == "HALF_OPEN"


@pytest.mark.asyncio
async def test_circuit_breaker_closes_after_success():
    """Test que le circuit se ferme après des succès en HALF_OPEN."""
    cb = CircuitBreaker(
        name="test",
        failure_threshold=1,
        success_threshold=1,
        reset_timeout=0.1
    )

    # Ouvrir le circuit
    with pytest.raises(Exception):
        async with cb:
            raise Exception("Failure")

    await asyncio.sleep(0.15)
    assert cb.state == "HALF_OPEN"

    # Succès en HALF_OPEN
    async with cb:
        pass

    assert cb.state == "CLOSED"


@pytest.mark.asyncio
async def test_circuit_breaker_decorator():
    """Test du décorateur circuit breaker."""
    cb = CircuitBreaker(name="decorated", failure_threshold=2)

    call_count = 0

    @cb.protect
    async def my_operation():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await my_operation()
    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_circuit_breaker_status():
    """Test du statut du circuit breaker."""
    cb = CircuitBreaker(name="stats_test", failure_threshold=3)

    # Quelques succès
    for _ in range(3):
        async with cb:
            pass

    # Un échec
    with pytest.raises(Exception):
        async with cb:
            raise Exception("Fail")

    status = cb.get_status()
    assert status["name"] == "stats_test"
    assert status["stats"]["successful_calls"] == 3
    assert status["stats"]["failed_calls"] == 1


# ============================================================
# Tests Retry Policy
# ============================================================

@pytest.mark.asyncio
async def test_retry_success_first_try():
    """Test qu'une opération réussie n'est pas retentée."""
    policy = RetryPolicy(max_retries=3)
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await policy.execute(operation)
    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_eventual_success():
    """Test qu'une opération qui réussit après des échecs fonctionne."""
    policy = RetryPolicy(max_retries=3, initial_delay=0.01)
    call_count = 0

    async def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"

    result = await policy.execute(flaky_operation)
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted():
    """Test que les retries s'épuisent correctement."""
    policy = RetryPolicy(max_retries=2, initial_delay=0.01)

    async def always_fail():
        raise ValueError("Always fails")

    with pytest.raises(ValueError):
        await policy.execute(always_fail)


@pytest.mark.asyncio
async def test_retry_exponential_backoff():
    """Test du backoff exponentiel."""
    policy = RetryPolicy(
        max_retries=3,
        initial_delay=0.1,
        backoff_strategy=BackoffStrategy.EXPONENTIAL
    )

    delays = []
    for i in range(3):
        delay = policy._calculate_delay(i)
        delays.append(delay)

    # Le délai doit augmenter exponentiellement
    assert delays[1] > delays[0]
    assert delays[2] > delays[1]


@pytest.mark.asyncio
async def test_retry_decorator():
    """Test du décorateur retry."""
    policy = RetryPolicy(max_retries=2, initial_delay=0.01)
    call_count = 0

    @policy.retry
    async def my_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("Fail")
        return "ok"

    result = await my_operation()
    assert result == "ok"
    assert call_count == 2


# ============================================================
# Tests Fallback
# ============================================================

@pytest.mark.asyncio
async def test_fallback_not_used_on_success():
    """Test que le fallback n'est pas utilisé en cas de succès."""
    fallback = Fallback(fallback_value="fallback")

    async def success():
        return "primary"

    result = await fallback.execute(success)
    assert result == "primary"


@pytest.mark.asyncio
async def test_fallback_used_on_failure():
    """Test que le fallback est utilisé en cas d'échec."""
    fallback = Fallback(fallback_value="fallback")

    async def failure():
        raise Exception("Primary failed")

    result = await fallback.execute(failure)
    assert result == "fallback"


@pytest.mark.asyncio
async def test_fallback_with_function():
    """Test du fallback avec une fonction."""
    async def fallback_func(*args, **kwargs):
        return {"status": "degraded", "args": args}

    fallback = Fallback(fallback_function=fallback_func)

    async def failure(x, y):
        raise Exception("Failed")

    result = await fallback.execute(failure, 1, 2)
    assert result["status"] == "degraded"


@pytest.mark.asyncio
async def test_fallback_with_cache():
    """Test du fallback avec cache."""
    fallback = Fallback()
    fallback._cache_duration = 300  # Active le cache
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "cached_value"
        raise Exception("Failed")

    # Premier appel réussi
    result1 = await fallback.execute(operation)
    assert result1 == "cached_value"

    # Deuxième appel échoue, utilise le cache
    result2 = await fallback.execute(operation)
    assert result2 == "cached_value"


# ============================================================
# Tests Timeout
# ============================================================

@pytest.mark.asyncio
async def test_timeout_success():
    """Test qu'une opération rapide réussit."""
    timeout = Timeout(seconds=1.0)

    async def fast_operation():
        await asyncio.sleep(0.01)
        return "done"

    result = await timeout.execute(fast_operation)
    assert result == "done"


@pytest.mark.asyncio
async def test_timeout_exceeded():
    """Test qu'une opération lente déclenche un timeout."""
    timeout = Timeout(seconds=0.05)

    async def slow_operation():
        await asyncio.sleep(1.0)
        return "never reached"

    with pytest.raises(TimeoutError):
        await timeout.execute(slow_operation)


# ============================================================
# Tests ResilientCall
# ============================================================

@pytest.mark.asyncio
async def test_resilient_call_full_chain():
    """Test de la chaîne complète timeout + retry + fallback."""
    resilient = ResilientCall(
        timeout=1.0,
        max_retries=2,
        initial_delay=0.01,
        fallback_value="fallback"
    )
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("Temporary")
        return "success"

    result = await resilient.execute(flaky)
    assert result == "success"


@pytest.mark.asyncio
async def test_resilient_call_uses_fallback():
    """Test que le fallback est utilisé après épuisement des retries."""
    resilient = ResilientCall(
        timeout=1.0,
        max_retries=1,
        initial_delay=0.01,
        fallback_value="fallback"
    )

    async def always_fail():
        raise Exception("Always fails")

    result = await resilient.execute(always_fail)
    assert result == "fallback"


# ============================================================
# Tests Observability - Logger
# ============================================================

def test_structured_logger_creates_output():
    """Test que le logger crée une sortie structurée."""
    logger = StructuredLogger(service_name="test_logger")

    # Le logger devrait fonctionner sans erreur
    logger.info("Test message", user_id="123", action="test")
    logger.warning("Warning message")
    logger.error("Error message", error_code="E001")

    logs = logger.get_logs()
    assert len(logs) >= 3


def test_structured_logger_with_filtering():
    """Test du logger avec filtrage."""
    from app.integration.cross_cutting.observability import LogLevel
    logger = StructuredLogger(service_name="test_context")

    logger.info("Info message")
    logger.error("Error message")

    all_logs = logger.get_logs()
    error_logs = logger.get_logs(level=LogLevel.ERROR)

    assert len(error_logs) <= len(all_logs)


# ============================================================
# Tests Observability - Tracer
# ============================================================

def test_tracer_creates_trace():
    """Test que le tracer crée des traces."""
    tracer = Tracer(service_name="test_service")

    span = tracer.start_trace("test_operation")
    assert span is not None
    assert span.trace_id is not None
    assert span.span_id is not None
    span.finish()


def test_tracer_child_spans():
    """Test des spans enfants."""
    tracer = Tracer(service_name="test_service")

    parent = tracer.start_trace("parent_operation")
    child = tracer.start_span("child_operation", parent_span=parent)

    assert child.trace_id == parent.trace_id
    assert child.parent_span_id == parent.span_id

    child.finish()
    parent.finish()


def test_tracer_context_manager():
    """Test du context manager pour les spans."""
    tracer = Tracer(service_name="test_service")

    with tracer.span("test_span") as span:
        assert span is not None
        span.set_tag("test_key", "test_value")


def test_tracer_get_trace():
    """Test de la récupération des traces."""
    tracer = Tracer(service_name="test_service")

    with tracer.trace("operation1") as span1:
        trace_id = span1.trace_id

    trace = tracer.get_trace(trace_id)
    assert trace is not None
    assert len(trace) >= 1


# ============================================================
# Tests Observability - Metrics
# ============================================================

def test_metrics_counter():
    """Test du compteur de métriques."""
    metrics = MetricsCollector(service_name="test")

    metrics.increment("requests_total", service="api")
    metrics.increment("requests_total", service="api")
    metrics.increment("requests_total", 5.0, service="api")

    value = metrics.get_counter("requests_total", service="api")
    assert value == 7.0


def test_metrics_gauge():
    """Test du gauge de métriques."""
    metrics = MetricsCollector(service_name="test")

    metrics.gauge("memory_usage", 100.5, unit="MB")
    metrics.gauge("memory_usage", 150.0, unit="MB")

    value = metrics.get_gauge("memory_usage", unit="MB")
    assert value == 150.0


def test_metrics_histogram():
    """Test de l'histogramme de métriques."""
    metrics = MetricsCollector(service_name="test")

    metrics.histogram("request_duration", 0.1)
    metrics.histogram("request_duration", 0.2)
    metrics.histogram("request_duration", 0.3)
    metrics.histogram("request_duration", 0.4)
    metrics.histogram("request_duration", 0.5)

    stats = metrics.get_histogram_stats("request_duration")
    assert stats is not None
    assert stats["count"] == 5


def test_metrics_timer():
    """Test du timer de métriques."""
    metrics = MetricsCollector(service_name="test")

    with metrics.timer("operation_duration"):
        import time
        time.sleep(0.01)

    stats = metrics.get_histogram_stats("operation_duration")
    assert stats is not None
    assert stats["count"] >= 1


# ============================================================
# Tests Security - JWT
# ============================================================

def test_jwt_create_token():
    """Test de la création de token JWT."""
    from app.integration.cross_cutting.security import JWTConfig
    config = JWTConfig(secret_key="test_secret")
    jwt_mgr = JWTManager(config)

    token = jwt_mgr.create_token(
        user_id="user123",
        roles=["agent"],
        scope=["read", "write"]
    )

    assert token is not None
    assert "." in token  # Format JWT: header.payload.signature


def test_jwt_decode_token():
    """Test du décodage de token JWT."""
    from app.integration.cross_cutting.security import JWTConfig
    config = JWTConfig(secret_key="test_secret")
    jwt_mgr = JWTManager(config)

    token = jwt_mgr.create_token(
        user_id="user123",
        roles=["agent", "viewer"]
    )

    payload = jwt_mgr.decode_token(token)
    assert payload.sub == "user123"
    assert "agent" in payload.roles
    assert "viewer" in payload.roles


def test_jwt_token_expiration():
    """Test de l'expiration du token."""
    from app.integration.cross_cutting.security import JWTConfig
    config = JWTConfig(secret_key="test_secret", access_token_expire_minutes=0)
    jwt_mgr = JWTManager(config)

    token = jwt_mgr.create_token(user_id="user123", expires_in_minutes=0)

    # Le token devrait être expiré immédiatement
    import time
    time.sleep(1.1)

    with pytest.raises(Exception):
        jwt_mgr.decode_token(token, verify=True)


def test_jwt_invalid_signature():
    """Test de signature invalide."""
    from app.integration.cross_cutting.security import JWTConfig
    config1 = JWTConfig(secret_key="secret1")
    config2 = JWTConfig(secret_key="secret2")
    jwt_mgr1 = JWTManager(config1)
    jwt_mgr2 = JWTManager(config2)

    token = jwt_mgr1.create_token(user_id="user123")

    with pytest.raises(Exception):
        jwt_mgr2.decode_token(token, verify=True)


# ============================================================
# Tests Security - RBAC
# ============================================================

def test_rbac_agent_permissions():
    """Test des permissions du rôle agent."""
    rbac = RBACManager()

    rbac.assign_role("user1", "agent")

    assert rbac.has_permission("user1", Permission.QUOTE_CREATE)
    assert rbac.has_permission("user1", Permission.QUOTE_READ)
    assert rbac.has_permission("user1", Permission.CUSTOMER_READ)
    assert not rbac.has_permission("user1", Permission.POLICY_DELETE)


def test_rbac_admin_permissions():
    """Test des permissions du rôle admin."""
    rbac = RBACManager()

    rbac.assign_role("admin1", "admin")

    # Admin a toutes les permissions
    assert rbac.has_permission("admin1", Permission.QUOTE_CREATE)
    assert rbac.has_permission("admin1", Permission.POLICY_DELETE)
    assert rbac.has_permission("admin1", Permission.CLAIM_CREATE)
    assert rbac.has_permission("admin1", Permission.CUSTOMER_DELETE)


def test_rbac_multiple_roles():
    """Test d'un utilisateur avec plusieurs rôles."""
    rbac = RBACManager()

    rbac.assign_role("user1", "viewer")
    rbac.assign_role("user1", "underwriter")

    # Permissions du viewer
    assert rbac.has_permission("user1", Permission.QUOTE_READ)

    # Permissions de l'underwriter
    assert rbac.has_permission("user1", Permission.POLICY_CREATE)


def test_rbac_revoke_role():
    """Test de la révocation de rôle."""
    rbac = RBACManager()

    rbac.assign_role("user1", "agent")
    assert rbac.has_permission("user1", Permission.QUOTE_CREATE)

    rbac.remove_role("user1", "agent")
    assert not rbac.has_permission("user1", Permission.QUOTE_CREATE)


# ============================================================
# Tests Security - SecurityManager
# ============================================================

def test_security_manager_authenticate():
    """Test de l'authentification complète."""
    from app.integration.cross_cutting.security import JWTConfig
    config = JWTConfig(secret_key="test_secret")
    security = SecurityManager(config)

    # Créer un utilisateur avec un rôle
    security.rbac_manager.assign_role("user123", "agent")

    # Créer un token
    token = security.jwt_manager.create_token(user_id="user123", roles=["agent"])

    # Authentifier
    context = security.authenticate(token, client_ip="192.168.1.1")

    assert context is not None
    assert context.user_id == "user123"
    assert context.authenticated


def test_security_manager_authorize():
    """Test de l'autorisation."""
    from app.integration.cross_cutting.security import JWTConfig
    config = JWTConfig(secret_key="test_secret")
    security = SecurityManager(config)

    security.rbac_manager.assign_role("user123", "agent")
    token = security.jwt_manager.create_token(user_id="user123", roles=["agent"])
    context = security.authenticate(token)

    # L'agent peut créer des devis
    assert context.has_permission(Permission.QUOTE_CREATE)

    # L'agent ne peut pas supprimer de polices
    assert not context.has_permission(Permission.POLICY_DELETE)


# ============================================================
# Tests Modules Content
# ============================================================

@pytest.mark.asyncio
async def test_module_12_content_exists():
    """Test que le contenu du module 12 existe."""
    from pathlib import Path

    base = Path("app/theory/content/12_resilience")
    assert base.is_dir()

    files = [
        "01_circuit_breaker.md",
        "02_retry_backoff.md",
        "03_timeout_fallback.md",
        "04_bulkhead.md",
        "05_chaos_engineering.md"
    ]

    for f in files:
        assert (base / f).exists(), f"Missing: {f}"


@pytest.mark.asyncio
async def test_module_13_content_exists():
    """Test que le contenu du module 13 existe."""
    from pathlib import Path

    base = Path("app/theory/content/13_observability")
    assert base.is_dir()

    files = [
        "01_three_pillars.md",
        "02_logging.md",
        "03_distributed_tracing.md",
        "04_metrics.md",
        "05_health_checks.md"
    ]

    for f in files:
        assert (base / f).exists(), f"Missing: {f}"


@pytest.mark.asyncio
async def test_module_14_content_exists():
    """Test que le contenu du module 14 existe."""
    from pathlib import Path

    base = Path("app/theory/content/14_security")
    assert base.is_dir()

    files = [
        "01_authentication.md",
        "02_authorization.md",
        "03_encryption.md",
        "04_message_security.md",
        "05_audit.md"
    ]

    for f in files:
        assert (base / f).exists(), f"Missing: {f}"


# ============================================================
# Tests Scénarios
# ============================================================

@pytest.mark.asyncio
async def test_scenarios_cross_exist():
    """Test que les scénarios CROSS existent."""
    from pathlib import Path

    base = Path("app/sandbox/scenarios/cross_cutting")
    assert base.is_dir()

    files = [
        "cross_01_circuit_breaker.py",
        "cross_02_tracing.py",
        "cross_03_security.py"
    ]

    for f in files:
        assert (base / f).exists(), f"Missing: {f}"


@pytest.mark.asyncio
async def test_scenario_cross01_structure():
    """Test de la structure du scénario CROSS-01."""
    from app.sandbox.scenarios.cross_cutting.cross_01_circuit_breaker import scenario

    assert scenario["id"] == "CROSS-01"
    assert "steps" in scenario
    assert len(scenario["steps"]) >= 5


@pytest.mark.asyncio
async def test_scenario_cross02_structure():
    """Test de la structure du scénario CROSS-02."""
    from app.sandbox.scenarios.cross_cutting.cross_02_tracing import scenario

    assert scenario["id"] == "CROSS-02"
    assert "steps" in scenario
    assert len(scenario["steps"]) >= 5


@pytest.mark.asyncio
async def test_scenario_cross03_structure():
    """Test de la structure du scénario CROSS-03."""
    from app.sandbox.scenarios.cross_cutting.cross_03_security import scenario

    assert scenario["id"] == "CROSS-03"
    assert "steps" in scenario
    assert len(scenario["steps"]) >= 5


# ============================================================
# Tests API (si disponible)
# ============================================================

@pytest.mark.asyncio
async def test_modules_12_13_14_api():
    """Test que les modules 12-14 sont accessibles via l'API."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for m in [12, 13, 14]:
            r = await client.get(f"/api/theory/modules/{m}")
            assert r.status_code == 200


@pytest.mark.asyncio
async def test_scenarios_cross_api():
    """Test que les scénarios CROSS sont accessibles via l'API."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for s in ["CROSS-01", "CROSS-02", "CROSS-03"]:
            r = await client.get(f"/api/sandbox/scenarios/{s}")
            assert r.status_code == 200
            data = r.json()
            assert "steps" in data

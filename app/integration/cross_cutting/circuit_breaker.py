"""
Circuit Breaker Pattern - Protection contre les pannes en cascade.

Le Circuit Breaker protège l'application contre les appels répétés
à un service défaillant, permettant une récupération gracieuse.

États:
- CLOSED: Fonctionnement normal, les appels passent
- OPEN: Circuit ouvert après N échecs, les appels échouent immédiatement
- HALF_OPEN: Test de récupération, un appel est autorisé
"""
import asyncio
import time
from typing import Any, Callable, Optional, Dict, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class CircuitState(Enum):
    """États possibles du circuit breaker."""
    CLOSED = "CLOSED"      # Normal - laisse passer les appels
    OPEN = "OPEN"          # Ouvert - bloque les appels
    HALF_OPEN = "HALF_OPEN"  # Test - laisse passer un appel pour tester


class CircuitBreakerError(Exception):
    """Exception levée quand le circuit est ouvert."""

    def __init__(self, message: str, state: CircuitState, retry_after: float = 0):
        self.message = message
        self.state = state
        self.retry_after = retry_after
        super().__init__(message)


@dataclass
class CircuitBreakerConfig:
    """Configuration du circuit breaker."""
    failure_threshold: int = 5          # Nombre d'échecs avant ouverture
    success_threshold: int = 2          # Nombre de succès pour fermer
    reset_timeout: float = 30.0         # Temps avant de passer en HALF_OPEN (secondes)
    half_open_max_calls: int = 2        # Appels autorisés en HALF_OPEN


@dataclass
class CircuitBreakerStats:
    """Statistiques du circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: List[Dict] = field(default_factory=list)
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None


class CircuitBreaker:
    """
    Implémentation du pattern Circuit Breaker.

    Usage:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=30)

        # Avec context manager
        async with cb:
            result = await some_risky_call()

        # Ou avec décorateur
        @cb.protect
        async def risky_function():
            ...
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        success_threshold: int = 2,
        reset_timeout: float = 30.0,
        half_open_max_calls: int = 2,
        on_state_change: Optional[Callable] = None
    ):
        if half_open_max_calls < success_threshold:
            raise ValueError(
                f"half_open_max_calls ({half_open_max_calls}) must be >= "
                f"success_threshold ({success_threshold})"
            )

        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            reset_timeout=reset_timeout,
            half_open_max_calls=half_open_max_calls
        )

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

        self.stats = CircuitBreakerStats()
        self._on_state_change = on_state_change
        self._lock = asyncio.Lock()

        # Historique des événements pour visualisation
        self._event_history: List[Dict] = []

    @property
    def state(self) -> str:
        """Retourne l'état actuel sous forme de string."""
        self._check_state_transition()
        return self._state.value

    def _check_state_transition(self):
        """Vérifie si une transition d'état est nécessaire."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.reset_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, new_state: CircuitState):
        """Effectue une transition d'état."""
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0

        # Log de la transition
        transition = {
            "timestamp": datetime.now().isoformat(),
            "from": old_state.value,
            "to": new_state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count
        }
        self.stats.state_changes.append(transition)
        self._event_history.append({
            "type": "state_change",
            **transition
        })

        # Callback optionnel
        if self._on_state_change:
            try:
                self._on_state_change(self.name, old_state, new_state)
            except Exception:
                pass

    def _record_success(self):
        """Enregistre un appel réussi."""
        self.stats.successful_calls += 1
        self.stats.last_success_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

        self._event_history.append({
            "type": "call_success",
            "timestamp": datetime.now().isoformat(),
            "state": self._state.value
        })

    def _record_failure(self, error: str = ""):
        """Enregistre un appel échoué."""
        self.stats.failed_calls += 1
        self._last_failure_time = time.time()
        self.stats.last_failure_time = self._last_failure_time

        if self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)

        self._event_history.append({
            "type": "call_failure",
            "timestamp": datetime.now().isoformat(),
            "state": self._state.value,
            "error": error
        })

    def _can_execute(self) -> bool:
        """Vérifie si un appel peut être exécuté."""
        self._check_state_transition()

        if self._state == CircuitState.CLOSED:
            return True
        elif self._state == CircuitState.OPEN:
            return False
        elif self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        return False

    async def __aenter__(self):
        """Entrée du context manager asynchrone."""
        async with self._lock:
            self.stats.total_calls += 1

            if not self._can_execute():
                self.stats.rejected_calls += 1
                retry_after = 0
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    retry_after = max(0, self.config.reset_timeout - elapsed)

                self._event_history.append({
                    "type": "call_rejected",
                    "timestamp": datetime.now().isoformat(),
                    "state": self._state.value,
                    "retry_after": retry_after
                })

                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is {self._state.value}",
                    self._state,
                    retry_after
                )

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Sortie du context manager asynchrone."""
        async with self._lock:
            if exc_type is None:
                self._record_success()
            else:
                self._record_failure(str(exc_val) if exc_val else "")
        return False

    def __enter__(self):
        """Entrée du context manager synchrone."""
        self.stats.total_calls += 1

        if not self._can_execute():
            self.stats.rejected_calls += 1
            retry_after = 0
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                retry_after = max(0, self.config.reset_timeout - elapsed)

            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is {self._state.value}",
                self._state,
                retry_after
            )

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sortie du context manager synchrone."""
        if exc_type is None:
            self._record_success()
        else:
            self._record_failure(str(exc_val) if exc_val else "")
        return False

    def protect(self, func: Callable) -> Callable:
        """Décorateur pour protéger une fonction avec le circuit breaker."""
        async def async_wrapper(*args, **kwargs):
            async with self:
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    def get_status(self) -> Dict:
        """Retourne le statut complet du circuit breaker."""
        self._check_state_transition()

        time_until_half_open = None
        if self._state == CircuitState.OPEN and self._last_failure_time:
            elapsed = time.time() - self._last_failure_time
            time_until_half_open = max(0, self.config.reset_timeout - elapsed)

        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "reset_timeout": self.config.reset_timeout
            },
            "stats": {
                "total_calls": self.stats.total_calls,
                "successful_calls": self.stats.successful_calls,
                "failed_calls": self.stats.failed_calls,
                "rejected_calls": self.stats.rejected_calls
            },
            "time_until_half_open": time_until_half_open
        }

    def get_event_history(self, limit: int = 50) -> List[Dict]:
        """Retourne l'historique des événements."""
        return self._event_history[-limit:]

    def reset(self):
        """Réinitialise le circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        self.stats = CircuitBreakerStats()
        self._event_history = []

    def force_open(self):
        """Force l'ouverture du circuit (pour tests ou maintenance)."""
        self._transition_to(CircuitState.OPEN)
        self._last_failure_time = time.time()

    def force_close(self):
        """Force la fermeture du circuit."""
        self._transition_to(CircuitState.CLOSED)


# Registry global des circuit breakers
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    reset_timeout: float = 30.0,
    **kwargs
) -> CircuitBreaker:
    """
    Récupère ou crée un circuit breaker par son nom.

    Permet de partager un circuit breaker entre plusieurs parties du code.
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            reset_timeout=reset_timeout,
            **kwargs
        )
    return _circuit_breakers[name]


def get_all_circuit_breakers() -> Dict[str, Dict]:
    """Retourne le statut de tous les circuit breakers."""
    return {name: cb.get_status() for name, cb in _circuit_breakers.items()}


def reset_all_circuit_breakers():
    """Réinitialise tous les circuit breakers."""
    for cb in _circuit_breakers.values():
        cb.reset()

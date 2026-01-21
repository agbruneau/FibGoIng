"""Classe de base pour les services mock avec gestion de latence et pannes."""
import asyncio
import random
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field


class ServiceStatus(Enum):
    """États possibles d'un service."""
    RUNNING = "running"
    DEGRADED = "degraded"
    ERROR = "error"
    STOPPED = "stopped"


class MockServiceError(Exception):
    """Exception pour les erreurs de services mock."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class ServiceConfig:
    """Configuration d'un service mock."""
    latency_ms: int = 50
    failure_rate: float = 0.0
    status: ServiceStatus = field(default=ServiceStatus.RUNNING)


class MockService:
    """
    Classe de base pour tous les services mock.

    Fonctionnalités:
    - Latence configurable
    - Injection de pannes
    - Logging des opérations
    - Statistiques
    """

    def __init__(
        self,
        name: str,
        initial_data: list = None,
        default_latency: int = 50,
        failure_rate: float = 0.0
    ):
        self.name = name
        self._data = initial_data or []
        self.config = ServiceConfig(
            latency_ms=default_latency,
            failure_rate=failure_rate
        )
        # Compatibilité avec l'ancienne API
        self.latency = default_latency
        self.failure_rate = failure_rate
        self.status = ServiceStatus.RUNNING
        self.stats = {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "total_latency_ms": 0
        }
        self.logs: List[Dict] = []
        self._event_handlers: List[Callable] = []
        self._id_counter = 0

    def _generate_id(self, prefix: str = "") -> str:
        """Génère un ID unique avec préfixe optionnel."""
        self._id_counter += 1
        unique = str(uuid.uuid4())[:8].upper()
        return f"{prefix}{unique}{self._id_counter:04d}"

    async def _simulate_latency(self):
        """Simule la latence réseau/traitement."""
        if self.latency > 0:
            # Ajoute une légère variation (±20%)
            actual_latency = self.latency * (0.8 + random.random() * 0.4)
            await asyncio.sleep(actual_latency / 1000)
            return actual_latency
        return 0

    def _should_fail(self) -> bool:
        """Détermine si la requête doit échouer."""
        if self.status == ServiceStatus.STOPPED:
            return True
        if self.status == ServiceStatus.ERROR:
            return True
        if self.failure_rate > 0:
            return random.random() < self.failure_rate
        return False

    def _log(self, operation: str, data: Dict, success: bool = True):
        """Enregistre une opération dans les logs."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "service": self.name,
            "operation": operation,
            "success": success,
            "data": data
        }
        self.logs.append(log_entry)
        # Garde uniquement les 100 derniers logs
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]

        # Notifie les handlers d'événements
        for handler in self._event_handlers:
            handler(log_entry)

    async def execute(
        self,
        operation: str,
        handler: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Exécute une opération avec gestion de latence et pannes.

        Args:
            operation: Nom de l'opération
            handler: Fonction à exécuter
            *args, **kwargs: Arguments pour le handler

        Returns:
            Résultat de l'opération ou erreur
        """
        self.stats["requests"] += 1
        start_time = datetime.now()

        # Simule la latence
        latency = await self._simulate_latency()
        self.stats["total_latency_ms"] += latency

        # Vérifie si doit échouer
        if self._should_fail():
            self.stats["failures"] += 1
            error = {
                "error": True,
                "code": "SERVICE_UNAVAILABLE",
                "message": f"Service {self.name} is unavailable",
                "timestamp": datetime.now().isoformat()
            }
            self._log(operation, error, success=False)
            raise MockServiceError(f"Service {self.name} is unavailable", 503)

        try:
            # Exécute l'opération
            if asyncio.iscoroutinefunction(handler):
                result = await handler(*args, **kwargs)
            else:
                result = handler(*args, **kwargs)

            self.stats["successes"] += 1
            self._log(operation, {"result": "success", "args": str(args)[:100]})
            return result

        except MockServiceError:
            self.stats["failures"] += 1
            raise

        except Exception as e:
            self.stats["failures"] += 1
            error = {
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self._log(operation, error, success=False)
            raise MockServiceError(str(e), 500)

    # Alias pour compatibilité
    async def _execute(self, operation: str, handler: Callable, *args, **kwargs):
        """Alias pour execute() - compatibilité avec ancienne API."""
        return await self.execute(operation, handler, *args, **kwargs)

    def configure(self, latency: Optional[int] = None, failure_rate: Optional[float] = None):
        """Configure les paramètres du service."""
        if latency is not None:
            self.latency = max(0, latency)
        if failure_rate is not None:
            self.failure_rate = max(0.0, min(1.0, failure_rate))

    def set_status(self, status: ServiceStatus):
        """Change le statut du service."""
        self.status = status
        self._log("status_change", {"new_status": status.value})

    def start(self):
        """Démarre le service."""
        self.set_status(ServiceStatus.RUNNING)

    def stop(self):
        """Arrête le service."""
        self.set_status(ServiceStatus.STOPPED)

    def inject_failure(self, failure_rate: float = 1.0):
        """Injecte des pannes dans le service."""
        self.failure_rate = failure_rate
        if failure_rate >= 0.5:
            self.status = ServiceStatus.DEGRADED
        if failure_rate >= 1.0:
            self.status = ServiceStatus.ERROR

    def reset(self):
        """Réinitialise le service."""
        self.status = ServiceStatus.RUNNING
        self.failure_rate = 0.0
        self.stats = {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "total_latency_ms": 0
        }

    def get_stats(self) -> Dict:
        """Retourne les statistiques du service."""
        return {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": self.latency,
            "failure_rate": self.failure_rate,
            **self.stats,
            "avg_latency_ms": (
                self.stats["total_latency_ms"] / self.stats["requests"]
                if self.stats["requests"] > 0 else 0
            )
        }

    def on_event(self, handler: Callable):
        """Enregistre un handler pour les événements du service."""
        self._event_handlers.append(handler)

    def get_logs(self, limit: int = 50) -> List[Dict]:
        """Retourne les derniers logs."""
        return self.logs[-limit:]


class MockServiceRegistry:
    """Registre central de tous les services mock."""

    def __init__(self):
        self._services: Dict[str, MockService] = {}

    def register(self, service_id: str, service: MockService):
        """Enregistre un service."""
        self._services[service_id] = service

    def get(self, service_id: str) -> Optional[MockService]:
        """Récupère un service par son ID."""
        return self._services.get(service_id)

    def get_all(self) -> Dict[str, MockService]:
        """Retourne tous les services."""
        return self._services

    def get_all_stats(self) -> List[Dict]:
        """Retourne les statistiques de tous les services."""
        stats_list = []
        for service_id, service in self._services.items():
            stats = service.get_stats()
            stats["id"] = service_id
            stats_list.append(stats)
        return stats_list

    def reset_all(self):
        """Réinitialise tous les services."""
        for service in self._services.values():
            service.reset()

    def stop_all(self):
        """Arrête tous les services."""
        for service in self._services.values():
            service.stop()

    def start_all(self):
        """Démarre tous les services."""
        for service in self._services.values():
            service.start()

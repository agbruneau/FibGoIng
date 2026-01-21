"""API Gateway - Routing, Rate Limiting et Cross-cutting concerns."""
import time
import asyncio
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class RateLimitAlgorithm(Enum):
    """Algorithmes de rate limiting disponibles."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"


@dataclass
class RateLimitConfig:
    """Configuration du rate limiting."""
    requests_per_minute: int = 100
    burst_size: int = 10
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET


@dataclass
class RouteConfig:
    """Configuration d'une route."""
    path_prefix: str
    service_name: str
    rate_limit: Optional[RateLimitConfig] = None
    require_auth: bool = True
    allowed_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])


class TokenBucket:
    """Implementation du Token Bucket pour le rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_update = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """Tente de consommer des tokens."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def get_state(self) -> dict:
        """Retourne l'etat actuel du bucket."""
        return {
            "remaining": int(self.tokens),
            "limit": self.capacity,
            "reset_in": int((self.capacity - self.tokens) / self.refill_rate) if self.refill_rate > 0 else 0
        }


class RateLimiter:
    """Gestionnaire de rate limiting multi-clients."""

    def __init__(self, default_config: RateLimitConfig = None):
        self.default_config = default_config or RateLimitConfig()
        self.buckets: Dict[str, TokenBucket] = {}

    def check(self, client_id: str, config: RateLimitConfig = None) -> tuple:
        """Verifie si le client peut faire une requete."""
        cfg = config or self.default_config

        if client_id not in self.buckets:
            self.buckets[client_id] = TokenBucket(
                capacity=cfg.burst_size,
                refill_rate=cfg.requests_per_minute / 60
            )

        bucket = self.buckets[client_id]
        allowed = bucket.consume()
        state = bucket.get_state()

        headers = {
            "X-RateLimit-Limit": str(cfg.requests_per_minute),
            "X-RateLimit-Remaining": str(state["remaining"]),
            "X-RateLimit-Reset": str(int(time.time()) + state["reset_in"])
        }

        return allowed, headers


class APIGateway:
    """
    API Gateway simulee avec routing et rate limiting.

    Fonctionnalites:
    - Routing base sur le path
    - Rate limiting par client
    - Metriques et logging
    """

    def __init__(self):
        self.routes: Dict[str, RouteConfig] = {}
        self.rate_limiter = RateLimiter()
        self.metrics = {
            "total_requests": 0,
            "requests_by_route": {},
            "rate_limited": 0,
            "errors": 0
        }
        self.request_log: List[Dict] = []

    def register_route(self, config: RouteConfig):
        """Enregistre une route."""
        self.routes[config.path_prefix] = config
        self.metrics["requests_by_route"][config.path_prefix] = 0

    def _match_route(self, path: str) -> Optional[RouteConfig]:
        """Trouve la route correspondant au path."""
        for prefix, config in self.routes.items():
            if path.startswith(prefix):
                return config
        return None

    async def handle_request(
        self,
        path: str,
        method: str,
        client_id: str,
        headers: Dict[str, str] = None,
        body: Any = None
    ) -> dict:
        """Traite une requete entrante."""
        self.metrics["total_requests"] += 1
        start_time = time.time()

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "path": path,
            "method": method,
            "client_id": client_id
        }

        # 1. Routing
        route = self._match_route(path)
        if not route:
            log_entry["status"] = 404
            self._log(log_entry)
            return {
                "status": 404,
                "headers": {},
                "body": {"error": {"code": "NOT_FOUND", "message": f"No route for {path}"}}
            }

        # 2. Verification methode
        if method not in route.allowed_methods:
            log_entry["status"] = 405
            self._log(log_entry)
            return {
                "status": 405,
                "headers": {},
                "body": {"error": {"code": "METHOD_NOT_ALLOWED", "message": f"{method} not allowed"}}
            }

        # 3. Rate limiting
        rate_config = route.rate_limit or RateLimitConfig()
        allowed, rate_headers = self.rate_limiter.check(client_id, rate_config)

        if not allowed:
            self.metrics["rate_limited"] += 1
            log_entry["status"] = 429
            log_entry["rate_limited"] = True
            self._log(log_entry)
            return {
                "status": 429,
                "headers": {**rate_headers, "Retry-After": "60"},
                "body": {
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests",
                        "retry_after": 60
                    }
                }
            }

        # 4. Succes - route vers le service
        self.metrics["requests_by_route"][route.path_prefix] += 1
        latency_ms = int((time.time() - start_time) * 1000)

        log_entry["status"] = 200
        log_entry["service"] = route.service_name
        log_entry["latency_ms"] = latency_ms
        self._log(log_entry)

        return {
            "status": 200,
            "headers": {
                **rate_headers,
                "X-Service": route.service_name,
                "X-Gateway-Latency": str(latency_ms)
            },
            "body": {"routed_to": route.service_name, "original_path": path}
        }

    def _log(self, entry: dict):
        """Ajoute une entree au log."""
        self.request_log.append(entry)
        if len(self.request_log) > 1000:
            self.request_log = self.request_log[-500:]

    def get_metrics(self) -> dict:
        """Retourne les metriques de la gateway."""
        return {
            **self.metrics,
            "routes_count": len(self.routes),
            "active_rate_limits": len(self.rate_limiter.buckets)
        }

    def get_routes(self) -> List[dict]:
        """Retourne la configuration des routes."""
        return [
            {
                "path": r.path_prefix,
                "service": r.service_name,
                "methods": r.allowed_methods,
                "rate_limit": r.rate_limit.requests_per_minute if r.rate_limit else "default"
            }
            for r in self.routes.values()
        ]

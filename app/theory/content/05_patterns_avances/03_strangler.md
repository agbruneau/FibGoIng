# Pattern Strangler Fig

## Résumé

Le **pattern Strangler Fig** (ou Strangler Pattern) permet de migrer progressivement d'un système legacy vers un nouveau système. Comme un figuier étrangleur qui enveloppe progressivement son hôte, le nouveau système remplace graduellement l'ancien.

## Problématique

Réécrire un système legacy en "big bang" est risqué :
- Projet long (années)
- Risque élevé d'échec
- Double maintenance pendant le projet
- Effet tunnel (pas de valeur jusqu'à la fin)

## Solution : Migration Progressive

```
Phase 1: Façade devant le legacy
┌──────────────────────────────────────┐
│ Façade / Proxy                       │
│  ┌────────────────────────────────┐  │
│  │ 100% → Legacy                  │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘

Phase 2: Première fonctionnalité migrée
┌──────────────────────────────────────┐
│ Façade / Proxy                       │
│  ┌──────────┐  ┌──────────────────┐  │
│  │ Quotes   │  │ Legacy           │  │
│  │ (Nouveau)│  │ (Policies, etc.) │  │
│  └──────────┘  └──────────────────┘  │
└──────────────────────────────────────┘

Phase 3: Plus de fonctionnalités migrées
┌──────────────────────────────────────┐
│ Façade / Proxy                       │
│  ┌──────────┐ ┌──────────┐ ┌──────┐  │
│  │ Quotes   │ │ Policies │ │Legacy│  │
│  │ (New)    │ │ (New)    │ │      │  │
│  └──────────┘ └──────────┘ └──────┘  │
└──────────────────────────────────────┘

Phase 4: Migration complète
┌──────────────────────────────────────┐
│ Nouveau Système                      │
│  ┌──────────┐ ┌──────────┐ ┌──────┐  │
│  │ Quotes   │ │ Policies │ │Claims│  │
│  │ (New)    │ │ (New)    │ │(New) │  │
│  └──────────┘ └──────────┘ └──────┘  │
└──────────────────────────────────────┘
│           Legacy décommissionné      │
```

## Étapes de Migration

### 1. Mise en place de la Façade

Créer un proxy devant le legacy qui route tout vers lui.

```python
# Façade initiale - tout va vers le legacy
class InsuranceFacade:
    def __init__(self):
        self.legacy = LegacySystem()
        self.new_quote_engine = None  # Pas encore

    async def create_quote(self, data: dict) -> dict:
        # Pour l'instant, tout vers le legacy
        return await self.legacy.create_quote(data)

    async def get_policy(self, policy_id: str) -> dict:
        return await self.legacy.get_policy(policy_id)

    async def create_claim(self, data: dict) -> dict:
        return await self.legacy.create_claim(data)
```

### 2. Migration de la Première Fonctionnalité

Migrer les devis vers le nouveau système.

```python
class InsuranceFacade:
    def __init__(self):
        self.legacy = LegacySystem()
        self.new_quote_engine = QuoteEngine()  # Nouveau!

    async def create_quote(self, data: dict) -> dict:
        # Routé vers le nouveau système
        return await self.new_quote_engine.create(data)

    async def get_policy(self, policy_id: str) -> dict:
        # Encore vers le legacy
        return await self.legacy.get_policy(policy_id)
```

### 3. Migration Progressive avec Feature Flags

```python
class InsuranceFacade:
    def __init__(self, feature_flags: FeatureFlags):
        self.flags = feature_flags
        self.legacy = LegacySystem()
        self.new_quote_engine = QuoteEngine()
        self.new_policy_admin = PolicyAdmin()

    async def create_quote(self, data: dict) -> dict:
        if self.flags.is_enabled("new_quote_engine"):
            return await self.new_quote_engine.create(data)
        return await self.legacy.create_quote(data)

    async def get_policy(self, policy_id: str) -> dict:
        if self.flags.is_enabled("new_policy_admin"):
            return await self.new_policy_admin.get(policy_id)
        return await self.legacy.get_policy(policy_id)
```

### 4. Migration Graduelle du Trafic

```python
class InsuranceFacade:
    async def create_quote(self, data: dict) -> dict:
        # 20% vers le nouveau, 80% vers le legacy
        if self.should_route_to_new("quotes", percentage=20):
            try:
                return await self.new_quote_engine.create(data)
            except Exception as e:
                # Fallback vers legacy si problème
                logger.warning(f"New system failed, fallback to legacy: {e}")
                return await self.legacy.create_quote(data)
        return await self.legacy.create_quote(data)

    def should_route_to_new(self, feature: str, percentage: int) -> bool:
        # Consistant pour un même client (sticky)
        return hash(self.current_request.client_id) % 100 < percentage
```

## Stratégies de Synchronisation

### Pendant la migration, les données doivent être cohérentes.

### Double Write (Écriture Double)

Écrire dans les deux systèmes.

```python
async def create_policy(self, data: dict) -> dict:
    # Écrire dans le nouveau
    new_result = await self.new_policy_admin.create(data)

    # Aussi dans le legacy (pour les autres systèmes)
    try:
        await self.legacy.create_policy(data)
    except Exception:
        logger.warning("Failed to sync to legacy")

    return new_result
```

### Event-based Sync

Le nouveau système publie des événements, un sync consomme et met à jour le legacy.

```
Nouveau Système → Event (PolicyCreated) → Sync Service → Legacy
```

### Change Data Capture (CDC)

Capturer les changements du legacy et les propager au nouveau.

```
Legacy DB → CDC → Event Stream → Nouveau Système
```

## Exemple Complet : Migration Quote Engine

```python
class StranglerQuoteService:
    """Service de devis avec migration progressive."""

    def __init__(
        self,
        legacy_client: LegacyClient,
        new_engine: QuoteEngine,
        feature_flags: FeatureFlags,
        metrics: MetricsCollector
    ):
        self.legacy = legacy_client
        self.new_engine = new_engine
        self.flags = feature_flags
        self.metrics = metrics

    async def create_quote(self, request: QuoteRequest) -> Quote:
        """Crée un devis via le système approprié."""

        use_new = self._should_use_new_system(request)

        if use_new:
            return await self._create_via_new(request)
        else:
            return await self._create_via_legacy(request)

    def _should_use_new_system(self, request: QuoteRequest) -> bool:
        """Détermine quel système utiliser."""
        # Certains produits toujours vers le nouveau
        if request.product in ["AUTO", "HABITATION"]:
            return self.flags.is_enabled("new_quote_engine")

        # Produits complexes restent sur legacy
        if request.product in ["FLOTTE", "RC_PRO"]:
            return False

        # Rollout progressif pour le reste
        return self.flags.percentage_enabled(
            "new_quote_engine_rollout",
            key=request.customer_id
        )

    async def _create_via_new(self, request: QuoteRequest) -> Quote:
        """Création via le nouveau moteur."""
        start = time.time()

        try:
            result = await self.new_engine.create(request)
            self.metrics.record("quote_create", system="new", success=True)

            # Optionnel: Shadow write vers legacy
            if self.flags.is_enabled("shadow_write_legacy"):
                asyncio.create_task(self._shadow_write_legacy(request))

            return result

        except Exception as e:
            self.metrics.record("quote_create", system="new", success=False)

            # Fallback vers legacy si configuré
            if self.flags.is_enabled("fallback_to_legacy"):
                logger.warning(f"Fallback to legacy: {e}")
                return await self._create_via_legacy(request)

            raise

        finally:
            self.metrics.record_latency("quote_create", time.time() - start)

    async def _create_via_legacy(self, request: QuoteRequest) -> Quote:
        """Création via le système legacy."""
        legacy_request = self._transform_to_legacy(request)
        legacy_result = await self.legacy.create_quote(legacy_request)
        return self._transform_from_legacy(legacy_result)
```

## Bonnes Pratiques

| Pratique | Description |
|----------|-------------|
| Petit périmètre | Migrer par petites fonctionnalités |
| Feature flags | Contrôler le routing dynamiquement |
| Monitoring | Comparer métriques legacy vs nouveau |
| Rollback | Pouvoir revenir au legacy instantanément |
| Sync bidirectionnelle | Pendant la transition |
| Tests shadow | Comparer les résultats des deux systèmes |

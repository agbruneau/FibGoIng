# Backlog - Interop Learning

> **Usage avec Claude Code** : Demander `/feature 1.1` pour implémenter une feature, `/test 1.1` pour exécuter ses tests.

---

## Métriques Globales

| Métrique | Cible | Actuel |
|----------|-------|--------|
| Features complétées | 21 | 6 |
| Tâches terminées | 181 | 36 |
| Tests passants | 165 | 23 |
| Couverture code | >80% | ~40% |

---

# Phase 1 - Fondations

## Feature 1.1 : Structure Projet ✅
> **Fichiers** : `requirements.txt`, `run.py`, `install.bat`, `run.bat`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Créer arborescence dossiers | `app/`, `static/`, `data/`, `tests/` | [x] |
| 2 | Créer requirements.txt | `requirements.txt` | [x] |
| 3 | Créer point d'entrée | `run.py` | [x] |
| 4 | Créer scripts Windows | `install.bat`, `run.bat` | [x] |

**Tests** : `tests/test_feature_1_1.py`
```python
from pathlib import Path

def test_directories_exist():
    dirs = ["app", "app/api", "app/mocks", "app/integration", "app/theory",
            "app/templates", "static", "static/css", "static/js", "data", "tests"]
    for d in dirs:
        assert Path(d).is_dir(), f"Missing: {d}"

def test_requirements_valid():
    req = Path("requirements.txt")
    assert req.exists()
    content = req.read_text()
    assert "fastapi" in content
    assert "uvicorn" in content

def test_run_script():
    assert Path("run.py").exists()
    content = Path("run.py").read_text()
    assert "uvicorn" in content
```

**Critères** : `[x]` Dossiers créés `[x]` pip install OK `[x]` python run.py démarre

---

## Feature 1.2 : Application FastAPI ✅
> **Fichiers** : `app/main.py`, `app/config.py`, `app/database.py`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Application FastAPI de base | `app/main.py` | [x] |
| 2 | Configuration constantes | `app/config.py` | [x] |
| 3 | Init SQLite + schéma | `app/database.py` | [x] |
| 4 | Endpoint SSE temps réel | `app/main.py` | [x] |

**Tests** : `tests/test_feature_1_2.py`
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_app_responds():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/")
        assert r.status_code == 200

def test_config():
    from app.config import APP_NAME, DATABASE_PATH
    assert APP_NAME == "Interop Learning"
    assert DATABASE_PATH is not None

@pytest.mark.asyncio
async def test_database_tables():
    from app.database import init_db, get_connection
    await init_db()
    async with get_connection() as db:
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in await cursor.fetchall()]
        assert "learner_progress" in tables
        assert "sandbox_sessions" in tables
```

**Critères** : `[x]` GET / = 200 `[x]` Config accessible `[x]` Tables SQLite créées `[x]` SSE fonctionne

---

## Feature 1.3 : Interface Utilisateur Base ✅
> **Fichiers** : `app/templates/base.html`, `static/css/`, `static/js/`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Template base HTML5 + Tailwind | `app/templates/base.html` | [x] |
| 2 | Intégrer Tailwind CSS | `static/css/tailwind.min.css` | [x] |
| 3 | Intégrer HTMX | `static/js/htmx.min.js` | [x] |
| 4 | Thème sombre par défaut | `app/templates/base.html` | [x] |
| 5 | Sidebar navigation | `app/templates/components/sidebar.html` | [x] |
| 6 | Breadcrumb dynamique | `app/templates/components/breadcrumb.html` | [x] |

**Tests** : `tests/test_feature_1_3.py`
```python
import pytest
from httpx import AsyncClient
from bs4 import BeautifulSoup

@pytest.mark.asyncio
async def test_dark_theme():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/")
        assert "dark" in r.text or "bg-gray-900" in r.text

@pytest.mark.asyncio
async def test_sidebar_exists():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/")
        soup = BeautifulSoup(r.text, "html.parser")
        assert soup.find(id="sidebar") or soup.find(class_="sidebar")

@pytest.mark.asyncio
async def test_htmx_loaded():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/")
        assert "htmx" in r.text.lower()
```

**Critères** : `[x]` Thème sombre `[x]` Sidebar visible `[x]` HTMX chargé `[x]` Breadcrumb

---

## Feature 1.4 : API Progression ✅
> **Fichiers** : `app/api/progress.py`, `app/api/theory.py`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Route GET /api/progress | `app/api/progress.py` | [x] |
| 2 | Route GET /api/theory/modules | `app/api/theory.py` | [x] |
| 3 | Route GET /api/theory/modules/{id} | `app/api/theory.py` | [x] |
| 4 | Route POST /api/theory/modules/{id}/complete | `app/api/theory.py` | [x] |

**Tests** : `tests/test_feature_1_4.py`
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_progress():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/progress")
        assert r.status_code == 200
        data = r.json()
        assert "completed_modules" in data
        assert "total_modules" in data
        assert data["total_modules"] == 16

@pytest.mark.asyncio
async def test_get_modules():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/theory/modules")
        assert r.status_code == 200
        assert len(r.json()) == 16

@pytest.mark.asyncio
async def test_complete_module():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/api/theory/modules/1/complete")
        assert r.status_code == 200
```

**Critères** : `[x]` Progression retournée `[x]` 16 modules listés `[x]` Marquage complété OK

---

## Feature 1.5 : Module 1 - Introduction ✅
> **Fichiers** : `app/theory/content/01_introduction/`, `app/theory/renderer.py`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Créer dossier contenu | `app/theory/content/01_introduction/` | [x] |
| 2 | Section 1.1 Définition | `01_definition.md` | [x] |
| 3 | Section 1.2 Trois piliers | `02_trois_piliers.md` | [x] |
| 4 | Section 1.3 Enjeux | `03_enjeux.md` | [x] |
| 5 | Section 1.4 Patterns | `04_patterns_overview.md` | [x] |
| 6 | Renderer Markdown→HTML | `app/theory/renderer.py` | [x] |
| 7 | Diagramme 3 piliers D3.js | `static/js/diagrams/pillars.js` | [ ] |
| 8 | Scénario INTRO-01 | `app/sandbox/scenarios/intro_01.py` | [x] |

**Tests** : `tests/test_feature_1_5.py`
```python
import pytest
from pathlib import Path
from httpx import AsyncClient

def test_content_files():
    base = Path("app/theory/content/01_introduction")
    assert base.is_dir()
    assert (base / "01_definition.md").exists()
    assert (base / "02_trois_piliers.md").exists()

def test_renderer():
    from app.theory.renderer import render_markdown
    html = render_markdown("# Test\n**bold**")
    assert "<h1>" in html
    assert "<strong>" in html

@pytest.mark.asyncio
async def test_module1_content():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/theory/modules/1")
        assert "interopérabilité" in r.json()["content"].lower()
```

**Critères** : `[x]` 4 sections MD `[x]` Renderer OK `[ ]` Diagramme interactif `[x]` Scénario INTRO-01

---

## Feature 1.6 : Module 2 - Domaine Assurance ✅
> **Fichiers** : `app/theory/content/02_domaine_assurance/`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Section 2.1 Processus métier | `01_processus.md` | [x] |
| 2 | Section 2.2 Entités | `02_entites.md` | [x] |
| 3 | Section 2.3 Systèmes | `03_systemes.md` | [x] |
| 4 | Section 2.4 Intégration | `04_integration.md` | [x] |
| 5 | Diagramme ER D3.js | `static/js/diagrams/entities.js` | [ ] |
| 6 | Diagramme flux processus | `static/js/diagrams/process_flow.js` | [ ] |
| 7 | Scénario INTRO-02 | `app/sandbox/scenarios/intro_02.py` | [x] |

**Tests** : `tests/test_feature_1_6.py`
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_module2_entities():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/theory/modules/2")
        content = r.json()["content"].lower()
        for entity in ["quote", "policy", "claim", "invoice", "customer"]:
            assert entity in content

@pytest.mark.asyncio
async def test_module2_systems():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/theory/modules/2")
        content = r.json()["content"].lower()
        assert "quote engine" in content
        assert "policy admin" in content
```

**Critères** : `[x]` 5 entités décrites `[x]` 8 systèmes décrits `[ ]` Diagrammes `[x]` Scénario

---

# Phase 2 - Pilier Applications 🔗

## Feature 2.1 : Services Mock
> **Fichiers** : `app/mocks/`, `data/mock_data/`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Classe base MockService | `app/mocks/base.py` | [ ] |
| 2 | Quote Engine | `app/mocks/quote_engine.py` | [ ] |
| 3 | Policy Admin | `app/mocks/policy_admin.py` | [ ] |
| 4 | Claims | `app/mocks/claims.py` | [ ] |
| 5 | Billing | `app/mocks/billing.py` | [ ] |
| 6 | Customer Hub | `app/mocks/customer_hub.py` | [ ] |
| 7 | Document Mgmt | `app/mocks/document_mgmt.py` | [ ] |
| 8 | Notifications | `app/mocks/notifications.py` | [ ] |
| 9 | External Rating | `app/mocks/external_rating.py` | [ ] |
| 10 | Données JSON fixes | `data/mock_data/*.json` | [ ] |
| 11 | Latence configurable | `app/mocks/base.py` | [ ] |
| 12 | Injection pannes | `app/mocks/base.py` | [ ] |

**Tests** : `tests/test_feature_2_1.py`
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_quote_engine():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/mocks/quotes", json={
            "customer_id": "C001", "product": "AUTO", "risk_data": {}
        })
        assert r.status_code == 201
        assert "id" in r.json()

@pytest.mark.asyncio
async def test_policy_crud():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create
        r = await client.post("/mocks/policies", json={"customer_id": "C001", "product": "AUTO"})
        assert r.status_code == 201
        pid = r.json()["number"]
        # Read
        r = await client.get(f"/mocks/policies/{pid}")
        assert r.status_code == 200
        # Delete
        r = await client.delete(f"/mocks/policies/{pid}")
        assert r.status_code == 204

@pytest.mark.asyncio
async def test_mock_data_loaded():
    from app.mocks import get_mock_data
    data = get_mock_data()
    assert len(data["customers"]) >= 5
```

**Critères** : `[ ]` 8 services mock `[ ]` Données JSON `[ ]` Latence config `[ ]` Pannes injectables

---

## Feature 2.2 : Module 3 - REST API
> **Fichiers** : `app/theory/content/03_rest_api/`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Section Richardson Model | `01_rmm.md` | [ ] |
| 2 | Section Design ressources | `02_resources.md` | [ ] |
| 3 | Section Versioning | `03_versioning.md` | [ ] |
| 4 | Section OpenAPI | `04_openapi.md` | [ ] |
| 5 | Section Erreurs HTTP | `05_errors.md` | [ ] |
| 6 | Visualiseur OpenAPI | `static/js/openapi-viewer.js` | [ ] |
| 7 | Scénario APP-01 | `app/sandbox/scenarios/app_01.py` | [ ] |

**Tests** : `tests/test_feature_2_2.py`
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_module3_rmm():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/theory/modules/3")
        content = r.json()["content"].lower()
        assert "richardson" in content or "level 0" in content

@pytest.mark.asyncio
async def test_sandbox_app01():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/sandbox/scenarios/APP-01")
        assert r.status_code == 200
        assert 6 <= len(r.json()["steps"]) <= 10
```

**Critères** : `[ ]` 5 sections `[ ]` Visualiseur OpenAPI `[ ]` Scénario APP-01

---

## Feature 2.3 : Module 4 - Gateway & BFF
> **Fichiers** : `app/integration/applications/gateway.py`, `app/integration/applications/bff.py`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Gateway routing | `app/integration/applications/gateway.py` | [ ] |
| 2 | Rate limiting | `app/integration/applications/gateway.py` | [ ] |
| 3 | BFF Mobile | `app/integration/applications/bff.py` | [ ] |
| 4 | BFF Courtier | `app/integration/applications/bff.py` | [ ] |
| 5 | Contenu Module 4 | `app/theory/content/04_api_gateway/` | [ ] |
| 6 | Scénario APP-02 | `app/sandbox/scenarios/app_02.py` | [ ] |
| 7 | Scénario APP-03 | `app/sandbox/scenarios/app_03.py` | [ ] |

**Tests** : `tests/test_feature_2_3.py`
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_gateway_routing():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/gateway/quotes/Q001")
        assert r.status_code == 200

@pytest.mark.asyncio
async def test_bff_mobile_reduced():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/bff/mobile/customer/C001")
        data = r.json()
        assert "name" in data
        assert "policies" not in data  # Réduit pour mobile

@pytest.mark.asyncio
async def test_bff_broker_full():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/bff/broker/customer/C001")
        data = r.json()
        assert "policies" in data  # Complet pour courtier
```

**Critères** : `[ ]` Gateway route `[ ]` Rate limit `[ ]` BFF mobile `[ ]` BFF broker `[ ]` Scénarios

---

## Feature 2.4 : Module 5 - Patterns Avancés
> **Fichiers** : `app/integration/applications/composition.py`, `app/integration/applications/acl.py`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | API Composition 360° | `app/integration/applications/composition.py` | [ ] |
| 2 | Anti-Corruption Layer | `app/integration/applications/acl.py` | [ ] |
| 3 | Contenu Module 5 | `app/theory/content/05_patterns_avances/` | [ ] |
| 4 | Scénario APP-04 | `app/sandbox/scenarios/app_04.py` | [ ] |
| 5 | Scénario APP-05 | `app/sandbox/scenarios/app_05.py` | [ ] |

**Tests** : `tests/test_feature_2_4.py`
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_composition_360():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/composition/customer/C001/360")
        data = r.json()
        assert "customer" in data
        assert "policies" in data
        assert "claims" in data

@pytest.mark.asyncio
async def test_acl_transform():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/acl/customer/transform", json={
            "CUST_NUM": "123", "CUST_NM": "DUPONT JEAN"
        })
        data = r.json()
        assert "firstName" in data
        assert "lastName" in data
```

**Critères** : `[ ]` Composition 5+ sources `[ ]` ACL transforme `[ ]` Scénarios APP-04/05

---

# Phase 3 - Pilier Événements ⚡

## Feature 3.1 : Message Broker In-Memory
> **Fichiers** : `app/integration/events/broker.py`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Broker central | `app/integration/events/broker.py` | [ ] |
| 2 | Queue point-à-point | `app/integration/events/broker.py` | [ ] |
| 3 | Topic Pub/Sub | `app/integration/events/broker.py` | [ ] |
| 4 | Garantie at-least-once | `app/integration/events/broker.py` | [ ] |
| 5 | Dead Letter Queue | `app/integration/events/broker.py` | [ ] |
| 6 | API contrôle | `app/api/broker.py` | [ ] |

**Tests** : `tests/test_feature_3_1.py`
```python
import pytest
import asyncio
from app.integration.events.broker import MessageBroker

@pytest.mark.asyncio
async def test_queue_point_to_point():
    broker = MessageBroker()
    await broker.send_to_queue("test", {"id": 1})
    msg = await broker.receive_from_queue("test")
    assert msg["id"] == 1

@pytest.mark.asyncio
async def test_pubsub_multi():
    broker = MessageBroker()
    received = []
    await broker.subscribe("topic", lambda m: received.append(m))
    await broker.subscribe("topic", lambda m: received.append(m))
    await broker.publish("topic", {"data": "test"})
    await asyncio.sleep(0.1)
    assert len(received) == 2

@pytest.mark.asyncio
async def test_dlq():
    broker = MessageBroker()
    async def fail(m): raise Exception("fail")
    await broker.subscribe("flaky", fail, max_retries=2)
    await broker.publish("flaky", {"x": 1})
    await asyncio.sleep(0.3)
    dlq = await broker.receive_from_queue("flaky.dlq")
    assert dlq is not None
```

**Critères** : `[ ]` Queue P2P `[ ]` Pub/Sub multi `[ ]` At-least-once `[ ]` DLQ

---

## Feature 3.2 : Visualiseur Flux D3.js
> **Fichiers** : `static/js/flow-visualizer.js`, `app/templates/sandbox/visualizer.html`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Module visualiseur | `static/js/flow-visualizer.js` | [ ] |
| 2 | Layout force-directed | `static/js/flow-visualizer.js` | [ ] |
| 3 | Animation particules | `static/js/flow-visualizer.js` | [ ] |
| 4 | Zoom et pan | `static/js/flow-visualizer.js` | [ ] |
| 5 | Timeline replay | `static/js/flow-visualizer.js` | [ ] |
| 6 | Couleurs par pilier | `static/js/flow-visualizer.js` | [ ] |
| 7 | Template page | `app/templates/sandbox/visualizer.html` | [ ] |
| 8 | Connexion SSE | `static/js/flow-visualizer.js` | [ ] |

**Tests** : `tests/test_feature_3_2.py`
```python
import pytest
from pathlib import Path
from httpx import AsyncClient

def test_visualizer_exports():
    js = Path("static/js/flow-visualizer.js").read_text()
    assert "initFlowVisualizer" in js
    assert "addNode" in js
    assert "animateMessage" in js

@pytest.mark.asyncio
async def test_visualizer_page():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/sandbox/visualizer")
        assert r.status_code == 200
        assert "svg" in r.text.lower() or "d3" in r.text.lower()
```

**Critères** : `[ ]` Nœuds services `[ ]` Particules animées `[ ]` Zoom/Pan `[ ]` Timeline `[ ]` SSE

---

## Feature 3.3 : Module 6 - Messaging Basics
> **Fichiers** : `app/theory/content/06_messaging_basics/`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Section Sync vs Async | `01_sync_async.md` | [ ] |
| 2 | Section Queue | `02_queue.md` | [ ] |
| 3 | Section Pub/Sub | `03_pubsub.md` | [ ] |
| 4 | Section Garanties | `04_guarantees.md` | [ ] |
| 5 | Section Idempotence | `05_idempotence.md` | [ ] |
| 6 | Scénario EVT-01 | `app/sandbox/scenarios/evt_01.py` | [ ] |
| 7 | Scénario EVT-02 | `app/sandbox/scenarios/evt_02.py` | [ ] |

**Tests** : `tests/test_feature_3_3.py`
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_module6_content():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/theory/modules/6")
        content = r.json()["content"].lower()
        assert "queue" in content
        assert "pub" in content or "topic" in content
        assert "idempoten" in content

@pytest.mark.asyncio
async def test_scenarios_evt01_02():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        for s in ["EVT-01", "EVT-02"]:
            r = await client.get(f"/api/sandbox/scenarios/{s}")
            assert r.status_code == 200
```

**Critères** : `[ ]` 5 sections `[ ]` Scénario EVT-01 `[ ]` Scénario EVT-02

---

## Feature 3.4 : Module 7 - Event-Driven
> **Fichiers** : `app/integration/events/event_store.py`, `app/integration/events/cqrs.py`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Event Store append-only | `app/integration/events/event_store.py` | [ ] |
| 2 | Rebuild state (replay) | `app/integration/events/event_store.py` | [ ] |
| 3 | CQRS Command Handler | `app/integration/events/cqrs.py` | [ ] |
| 4 | CQRS Query Handler | `app/integration/events/cqrs.py` | [ ] |
| 5 | Projections | `app/integration/events/cqrs.py` | [ ] |
| 6 | Contenu Module 7 | `app/theory/content/07_event_driven/` | [ ] |
| 7 | Scénario EVT-03 | `app/sandbox/scenarios/evt_03.py` | [ ] |
| 8 | Scénario EVT-05 | `app/sandbox/scenarios/evt_05.py` | [ ] |

**Tests** : `tests/test_feature_3_4.py`
```python
import pytest
from app.integration.events.event_store import EventStore

@pytest.mark.asyncio
async def test_event_store():
    es = EventStore()
    await es.append("p-1", {"type": "Created", "data": {"status": "DRAFT"}})
    await es.append("p-1", {"type": "Activated", "data": {"status": "ACTIVE"}})
    events = await es.get_events("p-1")
    assert len(events) == 2
    state = await es.rebuild_state("p-1")
    assert state["status"] == "ACTIVE"
```

**Critères** : `[ ]` Event Store `[ ]` Replay `[ ]` CQRS `[ ]` Projections `[ ]` Scénarios

---

## Feature 3.5 : Module 8 - Saga & Outbox
> **Fichiers** : `app/integration/events/saga.py`, `app/integration/events/outbox.py`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Saga Orchestrator | `app/integration/events/saga.py` | [ ] |
| 2 | Compensation (rollback) | `app/integration/events/saga.py` | [ ] |
| 3 | Outbox table + polling | `app/integration/events/outbox.py` | [ ] |
| 4 | Contenu Module 8 | `app/theory/content/08_saga_transactions/` | [ ] |
| 5 | Scénario EVT-04 | `app/sandbox/scenarios/evt_04.py` | [ ] |
| 6 | Scénario EVT-06 | `app/sandbox/scenarios/evt_06.py` | [ ] |
| 7 | Scénario EVT-07 | `app/sandbox/scenarios/evt_07.py` | [ ] |

**Tests** : `tests/test_feature_3_5.py`
```python
import pytest
from app.integration.events.saga import SagaOrchestrator

@pytest.mark.asyncio
async def test_saga_success():
    saga = SagaOrchestrator()
    saga.add_step("step1", compensate="comp1")
    saga.add_step("step2", compensate="comp2")
    result = await saga.execute({"data": "test"})
    assert result["status"] == "COMPLETED"

@pytest.mark.asyncio
async def test_saga_compensation():
    saga = SagaOrchestrator()
    compensated = []
    saga.add_step(lambda ctx: {"ok": True}, compensate=lambda ctx: compensated.append(1))
    saga.add_step(lambda ctx: (_ for _ in ()).throw(Exception("fail")), compensate=None)
    result = await saga.execute({})
    assert result["status"] == "COMPENSATED"
    assert len(compensated) == 1
```

**Critères** : `[ ]` Saga N étapes `[ ]` Compensation auto `[ ]` Outbox atomique `[ ]` Scénarios

---

# Phase 4 - Pilier Données 📊

## Feature 4.1 : ETL & CDC
> **Fichiers** : `app/integration/data/etl_pipeline.py`, `app/integration/data/cdc_simulator.py`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | ETL Extract | `app/integration/data/etl_pipeline.py` | [ ] |
| 2 | ETL Transform | `app/integration/data/etl_pipeline.py` | [ ] |
| 3 | ETL Load | `app/integration/data/etl_pipeline.py` | [ ] |
| 4 | CDC Capture | `app/integration/data/cdc_simulator.py` | [ ] |
| 5 | CDC Publish | `app/integration/data/cdc_simulator.py` | [ ] |

**Tests** : `tests/test_feature_4_1.py`
```python
import pytest
from app.integration.data.etl_pipeline import ETLPipeline
from app.integration.data.cdc_simulator import CDCSimulator

@pytest.mark.asyncio
async def test_etl_full():
    etl = ETLPipeline()
    result = await etl.run({"source": "claims", "destination": "dwh"})
    assert result["status"] == "completed"

@pytest.mark.asyncio
async def test_cdc_capture():
    cdc = CDCSimulator()
    await cdc.simulate_change("policies", "UPDATE", {"id": "P1"})
    changes = await cdc.capture_since(0)
    assert len(changes) == 1
    assert changes[0]["operation"] == "UPDATE"
```

**Critères** : `[ ]` ETL complet `[ ]` CDC capture `[ ]` CDC publie

---

## Feature 4.2 : Modules 9-11 Data
> **Fichiers** : `app/theory/content/09_etl_batch/`, `10_cdc_streaming/`, `11_data_quality/`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Contenu Module 9 ETL | `app/theory/content/09_etl_batch/` | [ ] |
| 2 | Contenu Module 10 CDC | `app/theory/content/10_cdc_streaming/` | [ ] |
| 3 | Contenu Module 11 Quality | `app/theory/content/11_data_quality/` | [ ] |
| 4 | Data Quality checks | `app/integration/data/data_quality.py` | [ ] |
| 5 | MDM golden record | `app/integration/data/mdm.py` | [ ] |
| 6 | Data Lineage | `app/integration/data/lineage.py` | [ ] |
| 7 | Scénarios DATA-01 à DATA-07 | `app/sandbox/scenarios/data_*.py` | [ ] |

**Tests** : `tests/test_feature_4_2.py`
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_modules_9_10_11():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        for m in [9, 10, 11]:
            r = await client.get(f"/api/theory/modules/{m}")
            assert r.status_code == 200

@pytest.mark.asyncio
async def test_data_scenarios():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        for i in range(1, 8):
            r = await client.get(f"/api/sandbox/scenarios/DATA-0{i}")
            assert r.status_code == 200
```

**Critères** : `[ ]` Modules 9-11 `[ ]` Data Quality `[ ]` MDM `[ ]` Lineage `[ ]` 7 scénarios

---

# Phase 5 - Patterns Transversaux

## Feature 5.1 : Résilience & Modules 12-14
> **Fichiers** : `app/integration/cross_cutting/`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Circuit Breaker | `app/integration/cross_cutting/circuit_breaker.py` | [ ] |
| 2 | Retry + Backoff | `app/integration/cross_cutting/retry.py` | [ ] |
| 3 | Fallback + Timeout | `app/integration/cross_cutting/retry.py` | [ ] |
| 4 | Observability | `app/integration/cross_cutting/observability.py` | [ ] |
| 5 | Security JWT | `app/integration/cross_cutting/security.py` | [ ] |
| 6 | Contenu Module 12 | `app/theory/content/12_resilience/` | [ ] |
| 7 | Contenu Module 13 | `app/theory/content/13_observability/` | [ ] |
| 8 | Contenu Module 14 | `app/theory/content/14_security/` | [ ] |
| 9 | Scénarios CROSS-01/02/03 | `app/sandbox/scenarios/cross_*.py` | [ ] |

**Tests** : `tests/test_feature_5_1.py`
```python
import pytest
import asyncio
from app.integration.cross_cutting.circuit_breaker import CircuitBreaker

@pytest.mark.asyncio
async def test_circuit_breaker():
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.5)
    assert cb.state == "CLOSED"
    for _ in range(2):
        try:
            async with cb: raise Exception()
        except: pass
    assert cb.state == "OPEN"
    await asyncio.sleep(0.6)
    assert cb.state == "HALF_OPEN"
```

**Critères** : `[ ]` Circuit Breaker `[ ]` Retry `[ ]` Modules 12-14 `[ ]` Scénarios CROSS

---

# Phase 6 - Synthèse

## Feature 6.1 : Modules 15-16 & Projet Final
> **Fichiers** : `app/theory/content/15_architecture_decisions/`, `16_projet_final/`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Contenu Module 15 | `app/theory/content/15_architecture_decisions/` | [ ] |
| 2 | Matrice décision | `static/js/decision-matrix.js` | [ ] |
| 3 | Anti-patterns | `15_architecture_decisions/05_antipatterns.md` | [ ] |
| 4 | Contenu Module 16 | `app/theory/content/16_projet_final/` | [ ] |
| 5 | Scénario CROSS-04 | `app/sandbox/scenarios/cross_04.py` | [ ] |

**Tests** : `tests/test_feature_6_1.py`
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_modules_15_16():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        for m in [15, 16]:
            r = await client.get(f"/api/theory/modules/{m}")
            assert r.status_code == 200

@pytest.mark.asyncio
async def test_cross04_ecosystem():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/sandbox/scenarios/CROSS-04")
        assert len(r.json()["steps"]) >= 10
```

**Critères** : `[ ]` Module 15 `[ ]` Module 16 `[ ]` CROSS-04 intègre 3 piliers

---

## Feature 6.2 : Documentation Intégrée
> **Fichiers** : `app/docs/`, `app/api/docs.py`

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Structure docs | `app/docs/` | [ ] |
| 2 | Glossaire tooltips | `app/docs/glossary.json` | [ ] |
| 3 | Fiches patterns 25+ | `app/docs/patterns/` | [ ] |
| 4 | Cheat sheets | `app/docs/cheatsheets/` | [ ] |
| 5 | API recherche | `app/api/docs.py` | [ ] |
| 6 | API patterns | `app/api/docs.py` | [ ] |

**Tests** : `tests/test_feature_6_2.py`
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_docs_search():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/docs/search?q=circuit")
        assert r.status_code == 200
        assert len(r.json()) >= 1

@pytest.mark.asyncio
async def test_docs_patterns():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/docs/patterns")
        assert len(r.json()) >= 25
```

**Critères** : `[ ]` Recherche OK `[ ]` 25+ patterns `[ ]` 50+ termes glossaire

---

## Feature 6.3 : Polish & Tests Finaux
> **Fichiers** : Tests de performance et couverture

| # | Tâche | Fichier | Statut |
|---|-------|---------|--------|
| 1 | Animations 500ms+ | CSS/JS | [ ] |
| 2 | Panneaux redimensionnables | `static/js/resize.js` | [ ] |
| 3 | Taille police ajustable | `app/api/preferences.py` | [ ] |
| 4 | Couleurs piliers cohérentes | CSS | [ ] |
| 5 | Couverture > 80% | `pytest --cov` | [ ] |
| 6 | Tests E2E | `tests/test_e2e.py` | [ ] |
| 7 | Performance < 2s | `tests/test_performance.py` | [ ] |
| 8 | Latence sandbox < 100ms | `tests/test_performance.py` | [ ] |

**Tests** : `tests/test_feature_6_3.py`
```python
import pytest
import time
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_page_performance():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        for page in ["/", "/theory/modules/1"]:
            start = time.time()
            r = await client.get(page)
            assert time.time() - start < 2.0

@pytest.mark.asyncio
async def test_e2e_journey():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        for m in range(1, 17):
            await client.post(f"/api/theory/modules/{m}/complete")
        r = await client.get("/api/progress")
        assert r.json()["percentage"] == 100
```

**Critères** : `[ ]` Pages < 2s `[ ]` Sandbox < 100ms `[ ]` Couverture 80% `[ ]` E2E OK

---

# Index des Scénarios Sandbox

| ID | Titre | Feature | Statut |
|----|-------|---------|--------|
| INTRO-01 | Explorer l'écosystème | 1.5 | [ ] |
| INTRO-02 | Cartographie des flux | 1.6 | [ ] |
| APP-01 | Créer API Quote Engine | 2.2 | [ ] |
| APP-02 | Gateway multi-partenaires | 2.3 | [ ] |
| APP-03 | BFF Mobile vs Portail | 2.3 | [ ] |
| APP-04 | Vue 360° client | 2.4 | [ ] |
| APP-05 | Migration Strangler Fig | 2.4 | [ ] |
| EVT-01 | Pub/Sub PolicyCreated | 3.3 | [ ] |
| EVT-02 | Queue traitement claims | 3.3 | [ ] |
| EVT-03 | Event Sourcing police | 3.4 | [ ] |
| EVT-04 | Saga souscription | 3.5 | [ ] |
| EVT-05 | CQRS reporting | 3.4 | [ ] |
| EVT-06 | Outbox pattern | 3.5 | [ ] |
| EVT-07 | Dead Letter handling | 3.5 | [ ] |
| DATA-01 | ETL batch sinistres | 4.2 | [ ] |
| DATA-02 | CDC temps réel polices | 4.2 | [ ] |
| DATA-03 | Pipeline renouvellements | 4.2 | [ ] |
| DATA-04 | MDM client | 4.2 | [ ] |
| DATA-05 | Contrôle qualité | 4.2 | [ ] |
| DATA-06 | Data virtualization | 4.2 | [ ] |
| DATA-07 | Data lineage | 4.2 | [ ] |
| CROSS-01 | Panne tarificateur | 5.1 | [ ] |
| CROSS-02 | Tracing distribué | 5.1 | [ ] |
| CROSS-03 | Sécuriser gateway | 5.1 | [ ] |
| CROSS-04 | Écosystème complet | 6.1 | [ ] |

---

*Dernière mise à jour: 2026-01-20*

"""Point d'entrée de l'application FastAPI."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
from datetime import datetime

from app.config import (
    APP_NAME, APP_VERSION, APP_DESCRIPTION,
    STATIC_DIR, TEMPLATES_DIR, MODULES, LEVELS, PILLAR_COLORS
)
from app.database import init_db
from app.api.progress import router as progress_router
from app.api.theory import router as theory_router
from app.api.sandbox import router as sandbox_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application."""
    # Démarrage
    await init_db()
    yield
    # Arrêt (nettoyage si nécessaire)


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates Jinja2
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Inclure les routers
app.include_router(progress_router, prefix="/api/progress", tags=["progress"])
app.include_router(theory_router, prefix="/api/theory", tags=["theory"])
app.include_router(sandbox_router, prefix="/api/sandbox", tags=["sandbox"])


# File d'événements SSE globale
sse_clients = []


async def broadcast_event(event_type: str, data: dict):
    """Diffuse un événement à tous les clients SSE connectés."""
    message = {"type": event_type, "data": data, "timestamp": datetime.now().isoformat()}
    for queue in sse_clients:
        await queue.put(message)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Page d'accueil - Dashboard."""
    return templates.TemplateResponse("base.html", {
        "request": request,
        "page_title": "Accueil",
        "modules": MODULES,
        "levels": LEVELS,
        "pillar_colors": PILLAR_COLORS,
        "breadcrumb": [{"title": "Accueil", "url": "/"}]
    })


@app.get("/theory/modules/{module_id}", response_class=HTMLResponse)
async def theory_module_page(request: Request, module_id: int):
    """Page d'un module théorique."""
    module = next((m for m in MODULES if m["id"] == module_id), None)
    if not module:
        return templates.TemplateResponse("base.html", {
            "request": request,
            "page_title": "Module non trouvé",
            "error": "Module non trouvé"
        })

    return templates.TemplateResponse("theory/module.html", {
        "request": request,
        "page_title": module["title"],
        "module": module,
        "modules": MODULES,
        "levels": LEVELS,
        "pillar_colors": PILLAR_COLORS,
        "breadcrumb": [
            {"title": "Accueil", "url": "/"},
            {"title": "Modules", "url": "/theory"},
            {"title": module["title"], "url": f"/theory/modules/{module_id}"}
        ]
    })


@app.get("/sandbox", response_class=HTMLResponse)
async def sandbox_page(request: Request):
    """Page principale du Sandbox."""
    return templates.TemplateResponse("sandbox/index.html", {
        "request": request,
        "page_title": "Sandbox",
        "modules": MODULES,
        "levels": LEVELS,
        "pillar_colors": PILLAR_COLORS,
        "breadcrumb": [
            {"title": "Accueil", "url": "/"},
            {"title": "Sandbox", "url": "/sandbox"}
        ]
    })


@app.get("/sandbox/visualizer", response_class=HTMLResponse)
async def sandbox_visualizer_page(request: Request):
    """Page du visualiseur de flux."""
    return templates.TemplateResponse("sandbox/visualizer.html", {
        "request": request,
        "page_title": "Visualiseur de Flux",
        "modules": MODULES,
        "levels": LEVELS,
        "pillar_colors": PILLAR_COLORS,
        "breadcrumb": [
            {"title": "Accueil", "url": "/"},
            {"title": "Sandbox", "url": "/sandbox"},
            {"title": "Visualiseur", "url": "/sandbox/visualizer"}
        ]
    })


@app.get("/events/stream")
async def sse_stream(request: Request):
    """Endpoint SSE pour les événements temps réel."""
    queue = asyncio.Queue()
    sse_clients.append(queue)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": message["type"],
                        "data": json.dumps(message["data"])
                    }
                except asyncio.TimeoutError:
                    # Keepalive
                    yield {"event": "ping", "data": "{}"}
        finally:
            sse_clients.remove(queue)

    return EventSourceResponse(event_generator())


@app.get("/health")
async def health_check():
    """Vérification de l'état de l'application."""
    return {
        "status": "healthy",
        "app": APP_NAME,
        "version": APP_VERSION
    }

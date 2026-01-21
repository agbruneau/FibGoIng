"""API des modules théoriques."""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.database import get_connection
from app.config import MODULES
from app.theory.renderer import render_module_content

router = APIRouter()


@router.get("/modules")
async def get_modules():
    """Liste tous les modules avec leur statut de progression."""
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT module_id, status FROM learner_progress"
        )
        progress = dict(await cursor.fetchall())

    result = []
    for module in MODULES:
        result.append({
            **module,
            "status": progress.get(module["id"], "available")
        })

    return result


@router.get("/modules/{module_id}")
async def get_module(module_id: int):
    """Retourne le contenu complet d'un module."""
    module = next((m for m in MODULES if m["id"] == module_id), None)
    if not module:
        raise HTTPException(status_code=404, detail="Module non trouvé")

    # Récupérer le contenu Markdown rendu en HTML
    content = await render_module_content(module_id)

    # Récupérer le statut de progression
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT status, started_at, completed_at FROM learner_progress WHERE module_id = ?",
            (module_id,)
        )
        row = await cursor.fetchone()

    progress = {
        "status": row[0] if row else "available",
        "started_at": row[1] if row else None,
        "completed_at": row[2] if row else None
    }

    return {
        **module,
        "content": content,
        "progress": progress
    }


@router.post("/modules/{module_id}/complete")
async def complete_module(module_id: int):
    """Marque un module comme complété."""
    module = next((m for m in MODULES if m["id"] == module_id), None)
    if not module:
        raise HTTPException(status_code=404, detail="Module non trouvé")

    async with get_connection() as db:
        # Vérifier si une entrée existe
        cursor = await db.execute(
            "SELECT id FROM learner_progress WHERE module_id = ?",
            (module_id,)
        )
        existing = await cursor.fetchone()

        now = datetime.now().isoformat()

        if existing:
            await db.execute(
                "UPDATE learner_progress SET status = 'completed', completed_at = ? WHERE module_id = ?",
                (now, module_id)
            )
        else:
            await db.execute(
                "INSERT INTO learner_progress (module_id, status, started_at, completed_at) VALUES (?, 'completed', ?, ?)",
                (module_id, now, now)
            )

        await db.commit()

    return {"status": "completed", "module_id": module_id}


@router.post("/modules/{module_id}/start")
async def start_module(module_id: int):
    """Marque un module comme en cours."""
    module = next((m for m in MODULES if m["id"] == module_id), None)
    if not module:
        raise HTTPException(status_code=404, detail="Module non trouvé")

    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT id, status FROM learner_progress WHERE module_id = ?",
            (module_id,)
        )
        existing = await cursor.fetchone()

        now = datetime.now().isoformat()

        if existing:
            # Ne pas rétrograder si déjà complété
            if existing[1] != "completed":
                await db.execute(
                    "UPDATE learner_progress SET status = 'in_progress', started_at = COALESCE(started_at, ?) WHERE module_id = ?",
                    (now, module_id)
                )
        else:
            await db.execute(
                "INSERT INTO learner_progress (module_id, status, started_at) VALUES (?, 'in_progress', ?)",
                (module_id, now)
            )

        await db.commit()

    return {"status": "in_progress", "module_id": module_id}

"""API de progression de l'apprenant."""
from fastapi import APIRouter, HTTPException
from app.database import get_connection
from app.config import MODULES

router = APIRouter()


@router.get("")
async def get_progress():
    """Retourne la progression globale de l'apprenant."""
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT module_id, status, completed_at FROM learner_progress WHERE status = 'completed'"
        )
        completed = await cursor.fetchall()

    completed_ids = [row[0] for row in completed]
    total = len(MODULES)
    completed_count = len(completed_ids)

    return {
        "completed_modules": completed_count,
        "total_modules": total,
        "percentage": round((completed_count / total) * 100) if total > 0 else 0,
        "completed_ids": completed_ids
    }


@router.get("/modules")
async def get_modules_progress():
    """Retourne le statut de tous les modules."""
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT module_id, status, started_at, completed_at FROM learner_progress"
        )
        progress_rows = await cursor.fetchall()

    # Convertir en dictionnaire
    progress_dict = {row[0]: {
        "status": row[1],
        "started_at": row[2],
        "completed_at": row[3]
    } for row in progress_rows}

    # Fusionner avec les infos des modules
    result = []
    for module in MODULES:
        progress = progress_dict.get(module["id"], {"status": "available"})
        result.append({
            **module,
            "status": progress.get("status", "available"),
            "started_at": progress.get("started_at"),
            "completed_at": progress.get("completed_at")
        })

    return result


@router.get("/stats")
async def get_stats():
    """Retourne des statistiques détaillées."""
    async with get_connection() as db:
        # Modules par statut
        cursor = await db.execute("""
            SELECT status, COUNT(*) FROM learner_progress GROUP BY status
        """)
        status_counts = dict(await cursor.fetchall())

        # Sessions sandbox
        cursor = await db.execute("SELECT COUNT(*) FROM sandbox_sessions")
        sandbox_count = (await cursor.fetchone())[0]

        # Sessions terminées
        cursor = await db.execute(
            "SELECT COUNT(*) FROM sandbox_sessions WHERE completed_at IS NOT NULL"
        )
        sandbox_completed = (await cursor.fetchone())[0]

    return {
        "modules": {
            "total": len(MODULES),
            "completed": status_counts.get("completed", 0),
            "in_progress": status_counts.get("in_progress", 0),
            "available": len(MODULES) - status_counts.get("completed", 0) - status_counts.get("in_progress", 0)
        },
        "sandbox": {
            "total_sessions": sandbox_count,
            "completed_sessions": sandbox_completed
        }
    }

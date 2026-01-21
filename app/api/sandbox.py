"""API du Sandbox."""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional
import json
from app.database import get_connection
from app.sandbox.scenarios import get_scenario, get_all_scenarios

router = APIRouter()


@router.get("/scenarios")
async def list_scenarios():
    """Liste tous les scénarios disponibles."""
    return get_all_scenarios()


@router.get("/scenarios/{scenario_id}")
async def get_scenario_details(scenario_id: str):
    """Retourne les détails d'un scénario."""
    scenario = get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")
    return scenario


@router.post("/sessions")
async def create_session(scenario_id: str):
    """Démarre une nouvelle session sandbox."""
    scenario = get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")

    async with get_connection() as db:
        cursor = await db.execute(
            "INSERT INTO sandbox_sessions (scenario_id, state, current_step) VALUES (?, ?, 1)",
            (scenario_id, json.dumps(scenario.get("initial_state", {})))
        )
        session_id = cursor.lastrowid
        await db.commit()

    return {
        "session_id": session_id,
        "scenario_id": scenario_id,
        "current_step": 1,
        "total_steps": len(scenario.get("steps", [])),
        "scenario": scenario
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: int):
    """Retourne l'état d'une session."""
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT id, scenario_id, state, current_step, started_at, completed_at FROM sandbox_sessions WHERE id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    scenario = get_scenario(row[1])

    return {
        "session_id": row[0],
        "scenario_id": row[1],
        "state": json.loads(row[2]) if row[2] else {},
        "current_step": row[3],
        "started_at": row[4],
        "completed_at": row[5],
        "scenario": scenario
    }


@router.post("/sessions/{session_id}/execute")
async def execute_command(session_id: int, command: str, args: Optional[dict] = None):
    """Exécute une commande dans le sandbox."""
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT scenario_id, state, current_step FROM sandbox_sessions WHERE id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    scenario_id, state_json, current_step = row
    state = json.loads(state_json) if state_json else {}
    scenario = get_scenario(scenario_id)

    # Enregistrer l'événement
    async with get_connection() as db:
        await db.execute(
            "INSERT INTO sandbox_events (session_id, event_type, payload) VALUES (?, ?, ?)",
            (session_id, command, json.dumps(args or {}))
        )
        await db.commit()

    # Simuler l'exécution (à implémenter selon le scénario)
    result = {
        "success": True,
        "command": command,
        "output": f"Commande '{command}' exécutée avec succès",
        "state": state
    }

    return result


@router.post("/sessions/{session_id}/validate")
async def validate_step(session_id: int):
    """Valide l'étape courante et passe à la suivante."""
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT scenario_id, current_step FROM sandbox_sessions WHERE id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    scenario_id, current_step = row
    scenario = get_scenario(scenario_id)
    total_steps = len(scenario.get("steps", []))

    next_step = current_step + 1
    completed = next_step > total_steps

    async with get_connection() as db:
        if completed:
            await db.execute(
                "UPDATE sandbox_sessions SET current_step = ?, completed_at = ? WHERE id = ?",
                (next_step, datetime.now().isoformat(), session_id)
            )
        else:
            await db.execute(
                "UPDATE sandbox_sessions SET current_step = ? WHERE id = ?",
                (next_step, session_id)
            )
        await db.commit()

    return {
        "validated": True,
        "previous_step": current_step,
        "current_step": next_step if not completed else current_step,
        "completed": completed
    }


@router.get("/sessions/{session_id}/events")
async def get_session_events(session_id: int):
    """Retourne les événements d'une session pour le replay."""
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT id, event_type, payload, timestamp FROM sandbox_events WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        rows = await cursor.fetchall()

    return [
        {
            "id": row[0],
            "event_type": row[1],
            "payload": json.loads(row[2]) if row[2] else {},
            "timestamp": row[3]
        }
        for row in rows
    ]

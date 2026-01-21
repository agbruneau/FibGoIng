"""
API Préférences utilisateur.

Gère les préférences utilisateur stockées côté serveur:
- Taille de police
- Panneaux redimensionnés
- Dernière page visitée
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
from pathlib import Path

router = APIRouter(prefix="/api/preferences", tags=["Preferences"])

# Stockage simple en fichier JSON (dans un vrai projet: session/cookie/localStorage)
PREFS_FILE = Path(__file__).parent.parent.parent / "data" / "preferences.json"


class Preferences(BaseModel):
    """Modèle des préférences utilisateur."""
    font_size: int = 16  # Taille de police en pixels (12-24)
    sidebar_width: int = 280  # Largeur sidebar en pixels
    panel_sizes: dict = {}  # Tailles des panneaux redimensionnables
    last_module: Optional[int] = None  # Dernier module visité
    last_scenario: Optional[str] = None  # Dernier scénario sandbox


def load_preferences() -> Preferences:
    """Charge les préférences depuis le fichier."""
    try:
        if PREFS_FILE.exists():
            data = json.loads(PREFS_FILE.read_text(encoding="utf-8"))
            return Preferences(**data)
    except Exception:
        pass
    return Preferences()


def save_preferences(prefs: Preferences) -> None:
    """Sauvegarde les préférences dans le fichier."""
    PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PREFS_FILE.write_text(
        json.dumps(prefs.model_dump(), indent=2),
        encoding="utf-8"
    )


@router.get("")
async def get_preferences() -> Preferences:
    """
    Récupère les préférences utilisateur.

    Returns:
        Préférences actuelles
    """
    return load_preferences()


class UpdateFontSizeRequest(BaseModel):
    font_size: int


@router.put("")
async def update_preferences(prefs: Preferences) -> Preferences:
    """
    Met à jour les préférences utilisateur.

    Args:
        prefs: Nouvelles préférences

    Returns:
        Préférences mises à jour
    """
    # Validation de la taille de police
    if not 12 <= prefs.font_size <= 24:
        raise HTTPException(
            status_code=400,
            detail="Font size must be between 12 and 24"
        )

    save_preferences(prefs)
    return prefs


@router.patch("/font-size")
async def update_font_size(request: UpdateFontSizeRequest) -> dict:
    """
    Met à jour uniquement la taille de police.

    Args:
        request: Requête contenant la nouvelle taille

    Returns:
        Confirmation avec nouvelle taille
    """
    size = request.font_size
    if not 12 <= size <= 24:
        raise HTTPException(
            status_code=400,
            detail="Font size must be between 12 and 24"
        )

    prefs = load_preferences()
    prefs.font_size = size
    save_preferences(prefs)

    return {"font_size": size, "message": "Font size updated"}


@router.patch("/last-visited")
async def update_last_visited(
    module_id: Optional[int] = None,
    scenario_id: Optional[str] = None
) -> dict:
    """
    Met à jour la dernière page visitée.

    Args:
        module_id: ID du dernier module visité
        scenario_id: ID du dernier scénario visité

    Returns:
        Confirmation
    """
    prefs = load_preferences()

    if module_id is not None:
        prefs.last_module = module_id
    if scenario_id is not None:
        prefs.last_scenario = scenario_id

    save_preferences(prefs)

    return {
        "last_module": prefs.last_module,
        "last_scenario": prefs.last_scenario
    }


@router.patch("/panel-size")
async def update_panel_size(panel_id: str, width: int) -> dict:
    """
    Met à jour la taille d'un panneau redimensionnable.

    Args:
        panel_id: Identifiant du panneau
        width: Nouvelle largeur en pixels

    Returns:
        Confirmation
    """
    prefs = load_preferences()
    prefs.panel_sizes[panel_id] = width
    save_preferences(prefs)

    return {"panel_id": panel_id, "width": width}

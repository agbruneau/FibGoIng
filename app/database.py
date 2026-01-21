"""Gestion de la base de données SQLite."""
import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path
from app.config import DATABASE_PATH


# Schéma de la base de données
SCHEMA = """
-- Progression de l'apprenant
CREATE TABLE IF NOT EXISTS learner_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL UNIQUE,
    status TEXT CHECK(status IN ('locked','available','in_progress','completed')) DEFAULT 'available',
    started_at DATETIME,
    completed_at DATETIME
);

-- État des scénarios sandbox
CREATE TABLE IF NOT EXISTS sandbox_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL,
    state JSON,
    current_step INTEGER DEFAULT 1,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

-- Événements du sandbox (pour replay)
CREATE TABLE IF NOT EXISTS sandbox_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sandbox_sessions(id),
    event_type TEXT,
    payload JSON,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Préférences utilisateur
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    font_size INTEGER DEFAULT 16,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Historique de navigation documentation
CREATE TABLE IF NOT EXISTS doc_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_path TEXT NOT NULL,
    visited_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db():
    """Initialise la base de données avec le schéma."""
    # Crée le dossier data s'il n'existe pas
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

        # Initialise les préférences utilisateur si non existantes
        await db.execute("""
            INSERT OR IGNORE INTO user_preferences (id, font_size)
            VALUES (1, 16)
        """)
        await db.commit()


@asynccontextmanager
async def get_connection():
    """Retourne une connexion à la base de données."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def get_db():
    """Dépendance FastAPI pour obtenir une connexion DB."""
    async with get_connection() as db:
        yield db

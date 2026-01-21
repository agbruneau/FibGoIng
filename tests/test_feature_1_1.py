"""Tests pour Feature 1.1 - Structure Projet"""
from pathlib import Path


def test_directories_exist():
    """Vérifie que tous les dossiers requis existent."""
    dirs = [
        "app", "app/api", "app/mocks", "app/integration", "app/theory",
        "app/templates", "static", "static/css", "static/js", "data", "tests"
    ]
    for d in dirs:
        assert Path(d).is_dir(), f"Missing: {d}"


def test_requirements_valid():
    """Vérifie que requirements.txt contient les dépendances essentielles."""
    req = Path("requirements.txt")
    assert req.exists()
    content = req.read_text()
    assert "fastapi" in content
    assert "uvicorn" in content


def test_run_script():
    """Vérifie que run.py existe et contient uvicorn."""
    assert Path("run.py").exists()
    content = Path("run.py").read_text()
    assert "uvicorn" in content

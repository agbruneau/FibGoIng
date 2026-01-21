"""
Point d'entrée de l'application Interop Learning.
Lance le serveur FastAPI et ouvre le navigateur automatiquement.
"""
import uvicorn
import webbrowser
from threading import Timer


def open_browser():
    """Ouvre le navigateur sur l'application après un délai."""
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    Timer(1.5, open_browser).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

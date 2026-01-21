@echo off
echo === Installation Interop Learning ===

echo Creation de l'environnement virtuel...
python -m venv venv
call venv\Scripts\activate.bat

echo Installation des dependances...
pip install -r requirements.txt

echo Initialisation de la base de donnees...
python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"

echo.
echo === Installation terminee ===
echo Lancez l'application avec: run.bat
pause

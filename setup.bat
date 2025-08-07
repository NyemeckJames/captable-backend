@echo off
echo ================================
echo Cap Table Management Setup
echo ================================

echo.
echo 1. Creation de l'environnement virtuel...
python -m venv venv
if errorlevel 1 (
    echo ERREUR: Impossible de creer l'environnement virtuel
    pause
    exit /b 1
)

echo.
echo 2. Activation de l'environnement virtuel...
call venv\Scripts\activate

echo.
echo 3. Installation des dependances Python...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERREUR: Installation des dependances echouee
    pause
    exit /b 1
)

echo.
echo 4. Creation du fichier de configuration...
if not exist .env (
    copy .env.example .env
    echo Fichier .env cree avec les parametres par defaut
)

echo.
echo 5. Creation des bases de donnees...
python setup_db.py
if errorlevel 1 (
    echo ERREUR: Creation des bases de donnees echouee
    echo Verifiez que PostgreSQL est demarré et accessible
    pause
    exit /b 1
)

echo.
echo 6. Execution des migrations...
alembic upgrade head
if errorlevel 1 (
    echo ERREUR: Migration de la base de donnees echouee
    pause
    exit /b 1
)

echo.
echo ================================
echo Installation terminee avec succes!
echo ================================
echo.
echo Lancement de l'application...
echo (Appuyez sur une touche pour continuer)
pause > nul

:: Activation de l'environnement virtuel pour s'assurer qu'il reste actif dans ce contexte
call venv\Scripts\activate

:: Lancer le serveur (remplace run.py par uvicorn si nécessaire)
python run.py

:: Si tu utilises uvicorn directement (par ex. avec FastAPI), remplace la ligne ci-dessus par :
:: uvicorn app.main:app --reload

exit /b 0

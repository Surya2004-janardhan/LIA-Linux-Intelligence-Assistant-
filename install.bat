@echo off
REM LIA Windows Installer
echo ====================================
echo   LIA - Local Intelligence Agent
echo   Privacy-first AI OS wrapper
echo ====================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.10+ is required.
    echo Install: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python found

REM Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip not found.
    pause
    exit /b 1
)
echo [OK] pip found

REM Clone or update
if exist "LIA" (
    echo Updating existing installation...
    cd LIA
    git pull --quiet
) else (
    echo Cloning LIA...
    git clone --quiet https://github.com/your-username/LIA.git
    cd LIA
)

REM Install dependencies
echo Installing dependencies...
pip install -e . --quiet

REM Create data directories
if not exist "memory" mkdir memory
if not exist "workflows" mkdir workflows

REM Check Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [INFO] Ollama not found. Install for local LLM: https://ollama.ai
    echo   LIA also supports OpenAI/Groq  configure in config.yaml
) else (
    echo [OK] Ollama found
    ollama list 2>nul | findstr "llama3" >nul
    if errorlevel 1 (
        echo Pulling llama3 model...
        ollama pull llama3
    ) else (
        echo [OK] llama3 model ready
    )
)

echo.
echo ====================================
echo   Installation complete!
echo ====================================
echo.
echo   Quick start:
echo     python lia.py ask "check my disk space"
echo     python lia.py explain "dir /s *.py"
echo     python lia.py status
echo     python lia.py help
echo.
pause

@echo off
echo ========================================
echo  Manufacturing Compliance Dashboard
echo  BRC/HACCP Compliance Tool
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed.
    echo Download it from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "venv" (
    echo Setting up for first time use...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    echo.
    echo Dependencies installed.
) else (
    call venv\Scripts\activate.bat
)

REM Seed demo database if it doesn't exist
if not exist "data\compliance.db" (
    echo Creating demo database...
    python data\seed_demo.py
    echo Demo database created.
    echo.
)

echo Starting dashboard...
echo Open your browser to: http://localhost:8501
echo Press Ctrl+C to stop.
echo.
streamlit run app.py

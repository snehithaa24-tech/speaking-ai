@echo off
REM Development startup script for SAHAYAK AI (Windows)
REM Runs both backend and frontend in the same window with proper error handling

echo 🚀 Starting SAHAYAK AI Development Environment

REM ============================================
REM Validate project structure
REM ============================================
if not exist "backend" (
    echo ❌ Backend directory not found. Run from project root.
    pause
    exit /b 1
)

if not exist "frontend" (
    echo ❌ Frontend directory not found. Run from project root.
    pause
    exit /b 1
)

REM ============================================
REM Check environment configuration
REM ============================================
if not exist "backend\.env" (
    echo ⚠️  backend\.env not found. Copying from .env.example...
    if exist ".env.example" (
        copy .env.example backend\.env
        echo 📝 Please edit backend\.env and add your GEMINI_API_KEY
    ) else (
        echo ❌ .env.example not found in project root
    )
    pause
    exit /b 1
)

REM Check for GEMINI_API_KEY in backend\.env
findstr /C:"GEMINI_API_KEY=" backend\.env >nul
if errorlevel 1 (
    echo ⚠️  GEMINI_API_KEY not set in backend\.env
    echo 📝 Please edit backend\.env and add your GEMINI_API_KEY from https://aistudio.google.com/apikey
    pause
    exit /b 1
)

REM ============================================
REM Validate Python availability
REM ============================================
where python >nul 2>nul
if errorlevel 1 (
    echo ❌ Python not found in PATH. Please install Python 3.11+
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2 delims=." %%i in ('python --version 2^>^&1') do set PYTHON_MINOR=%%i
if %PYTHON_MINOR% LSS 11 (
    echo ⚠️  Python 3.11+ recommended (found 3.%PYTHON_MINOR%)
)

REM ============================================
REM Setup backend virtual environment
REM ============================================
echo 🔧 Setting up backend...
cd /d backend

if not exist venv (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        cd ..
        pause
        exit /b 1
    )
)

echo 📦 Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    cd ..
    pause
    exit /b 1
)

echo 📦 Installing/updating dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    cd ..
    pause
    exit /b 1
)

REM ============================================
REM Setup frontend
REM ============================================
cd ..\frontend

if not exist node_modules (
    echo 📦 Installing frontend dependencies...
    npm install
    if errorlevel 1 (
        echo ❌ Failed to install frontend dependencies
        cd ..
        pause
        exit /b 1
    )
)

REM ============================================
REM Start services
REM ============================================
cd ..

echo.
echo ✅ Starting SAHAYAK AI services...
echo    Frontend: http://localhost:5173
echo    Backend API: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop all services.
echo.

REM Start backend in background
start "SAHAYAK AI Backend" /min cmd /c "cd /d backend && call venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

REM Give backend time to start
timeout /t 3 /nobreak >nul

REM Start frontend (blocks until stopped)
echo 🎨 Starting frontend...
cd /d frontend && npm run dev

REM If frontend stops, kill backend
echo.
echo 🛑 Frontend stopped. Stopping backend...
taskkill /FI "WINDOWTITLE eq SAHAYAK AI Backend" /F >nul 2>&1
echo ✅ All services stopped.
@echo off
setlocal EnableDelayedExpansion
 
:: ============================================================
::  Air Canvas - Launcher
:: ============================================================
 
set VENV_DIR=.venv
set REQ_FILE=requirements.txt
set MAIN_SCRIPT=src\main.py
set MODEL_DIR=assets\models
set MODEL_PATH=%MODEL_DIR%\hand_landmarker.task
set MODEL_URL=https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
 
:: ── Check Python ─────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Python not found. Please install Python 3.9-3.11 and add it to PATH.
    echo          https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
 
:: ── Virtual environment ───────────────────────────────────────────────────────
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo  [SETUP] Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  [SETUP] Virtual environment created.
)
 
call "%VENV_DIR%\Scripts\activate.bat"
 
:: ── Dependencies ─────────────────────────────────────────────────────────────
echo  [SETUP] Checking dependencies...
python -m pip install -q --upgrade pip
python -m pip install -q -r "%REQ_FILE%"
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies from %REQ_FILE%.
    pause
    exit /b 1
)
 
:: ── Model file ───────────────────────────────────────────────────────────────
if not exist "%MODEL_PATH%" (
    echo  [SETUP] Downloading hand landmark model...
    if not exist "%MODEL_DIR%" mkdir "%MODEL_DIR%"
    curl.exe -L --progress-bar -o "%MODEL_PATH%" "%MODEL_URL%"
    if errorlevel 1 (
        echo  [ERROR] Model download failed. Check your internet connection and try again.
        if exist "%MODEL_PATH%" del "%MODEL_PATH%"
        pause
        exit /b 1
    )
    echo  [SETUP] Model downloaded successfully.
)
 
:: ── Launch ───────────────────────────────────────────────────────────────────
cls
echo.
echo  ============================================================
echo    AIR CANVAS
echo  ============================================================
echo.
echo    DRAW    ^|  Index finger up, middle finger down
echo    PAUSE   ^|  Raise index + middle finger together
echo    COLOUR  ^|  Point at a swatch in the top toolbar
echo    SIZE    ^|  Point at a size dot in the top toolbar
echo    CLEAR   ^|  Point at CLEAR button  ^|  press C
echo    SAVE    ^|  Press S  -^>  saved to assets\
echo    QUIT    ^|  Press Q or Esc
echo.
echo  ============================================================
echo.
 
python "%MAIN_SCRIPT%"
set EXIT_CODE=%errorlevel%
 
:: ── Post-exit message ────────────────────────────────────────────────────────
echo.
if %EXIT_CODE% equ 0 (
    echo  [INFO] Session ended cleanly.
) else (
    echo  [WARN] Application exited with code %EXIT_CODE%.
    echo         If the camera failed, check that no other app is using it.
)
echo.
pause
@echo off
REM ============================================================
REM  Modern UI build — produces dist\Spotify\Spotify.exe
REM ============================================================
setlocal

set ROOT=%~dp0
set PY=%ROOT%venv\Scripts\python.exe

if not exist "%PY%" (
    echo [!] venv not found at %PY%
    echo     Create it first:  python -m venv venv
    exit /b 1
)

echo === [1/3] Installing runtime + build dependencies ===
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r requirements.txt
"%PY%" -m pip install pyinstaller

echo === [2/3] Cleaning previous build output ===
if exist build rmdir /s /q build
if exist "dist\Spotify" rmdir /s /q "dist\Spotify"

echo === [3/3] Building exe with PyInstaller ===
"%PY%" -m PyInstaller app_modern.spec --clean --noconfirm
if errorlevel 1 (
    echo [!] PyInstaller build failed.
    exit /b 1
)

echo.
echo === DONE ===
echo   EXE folder: %ROOT%dist\Spotify\
echo   Run:        %ROOT%dist\Spotify\Spotify.exe
endlocal

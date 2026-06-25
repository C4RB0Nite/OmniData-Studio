@echo off
setlocal
title OmniData Studio Launcher

echo ===================================================
echo       OmniData Studio - Master Launcher
echo ===================================================
echo.

:: 1. Always check Python requirements (Lightning fast if already installed)
echo [1/2] Verifying Python Dependencies...
pip install -r requirements.txt
echo.

:: 2. Always check Node modules (Lightning fast if already installed)
echo [2/2] Verifying UI Dependencies...
cd data-os-frontend
call npm install
cd ..
echo.

:: 3. Boot the Servers
echo ===================================================
echo Booting Cognitive Architecture...
echo ===================================================

:: Open Backend and LOCK the Window Title
start "OmniData_Backend" cmd /k "title OmniData_Backend && python server.py"

:: Open Frontend and LOCK the Window Title
start "OmniData_Frontend" cmd /k "title OmniData_Frontend && cd data-os-frontend && npm run dev"

echo.
echo [SUCCESS] Both servers are launching in separate windows!
echo The UI will be available at: http://localhost:3000
echo.
echo ===================================================
echo               🛑 SHUTDOWN SEQUENCE 🛑
echo ===================================================
echo DO NOT click the red 'X' on this window to close.
echo Simply press ANY KEY in this terminal to instantly 
echo shut down the Backend and Frontend simultaneously.
echo ===================================================
pause >nul

:: The Kill Switch: Triggers when you press a key
echo.
echo Shutting down OmniData Studio...
taskkill /FI "WINDOWTITLE eq OmniData_Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq OmniData_Frontend*" /T /F >nul 2>&1

echo All servers terminated successfully.
timeout /t 2 >nul
exit
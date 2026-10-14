@echo off
title 1WIN TOKEN SALE SNIPER HUB - CONTROL PANEL
color 0A
cd /d "%~dp0"

:: 1. Periksa Python & Virtual Environment
set "PYTHON_EXE=python"
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
)

:: 2. Auto-Install Dependencies jika belum
if exist "core\requirements.txt" (
    %PYTHON_EXE% -m pip install -r core\requirements.txt --quiet >nul 2>&1
)

:: 3. Setup Config Template jika belum ada
if not exist "core\config.json" (
    if exist "core\config.example.json" (
        copy /Y "core\config.example.json" "core\config.json" >nul 2>&1
    )
)

:: 4. Jalankan Service All-in-One via PM2 Otomatis Saat Launching
pm2 describe 1win-sniper-hub >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Menyalakan 1win-sniper-hub dan 1win-tunnel (Cloudflare) via PM2...
    pm2 start core/ecosystem.config.js >nul 2>&1
    pm2 save >nul 2>&1
)

:MENU
cls
echo ======================================================================
echo    🪙 1WIN TOKEN SALE SNIPER HUB (ALL-IN-ONE CONTROL PANEL)
echo    Platform : Windows
echo    Backend  : Port 6000 (Auto Local IP)
echo    Domain   : https://topnodtools.web.id
echo ======================================================================
echo.
echo    [1] 📊 Lihat Status Proses PM2
echo    [2] 📜 Lihat Live Logs Backend (Realtime Stream)
echo    [3] 🔄 Restart Semua Service (Hub + Cloudflare Tunnel)
echo    [4] 🛑 Hentikan Semua Service (Stop PM2)
echo    [5] 🚀 Jalankan Ulang Service (Start PM2)
echo    [6] 🌐 Buka Web Terminal di Browser (topnodtools.web.id)
echo    [0] ❌ Keluar Menu (Service Tetap Berjalan di Background)
echo.
echo ======================================================================
set /p opt="Pilih menu [0-6]: "

if "%opt%"=="1" goto STATUS
if "%opt%"=="2" goto LOGS
if "%opt%"=="3" goto RESTART
if "%opt%"=="4" goto STOP
if "%opt%"=="5" goto START
if "%opt%"=="6" goto OPEN_WEB
if "%opt%"=="0" goto EXIT

echo [!] Pilihan tidak valid. Silakan pilih 0-6.
timeout /t 2 >nul
goto MENU

:STATUS
cls
echo ======================================================================
echo    📊 STATUS RUNNING PM2 PROCESSES
echo ======================================================================
echo.
pm2 status
echo.
echo Tekan sembarang tombol untuk kembali ke menu...
pause >nul
goto MENU

:LOGS
cls
echo ======================================================================
echo    📜 LIVE LOGS BACKEND (Tekan Ctrl+C untuk kembali ke menu)
echo ======================================================================
echo.
pm2 logs 1win-sniper-hub --lines 30
echo.
echo Tekan sembarang tombol untuk kembali ke menu...
pause >nul
goto MENU

:RESTART
cls
echo ======================================================================
echo    🔄 MERESTART 1WIN SNIPER HUB & CLOUDFLARE TUNNEL
echo ======================================================================
echo.
pm2 restart 1win-sniper-hub 1win-tunnel
pm2 save >nul 2>&1
echo.
echo [OK] Service berhasil direstart!
echo.
timeout /t 2 >nul
goto MENU

:STOP
cls
echo ======================================================================
echo    🛑 MENGHENTIKAN SEMUA SERVICE
echo ======================================================================
echo.
pm2 stop 1win-sniper-hub 1win-tunnel
pm2 delete 1win-sniper-hub 1win-tunnel
pm2 save >nul 2>&1
echo.
echo [OK] 1win-sniper-hub dan 1win-tunnel telah dihentikan dan dibersihkan.
echo.
timeout /t 2 >nul
goto MENU

:START
cls
echo ======================================================================
echo    🚀 MENJALANKAN SERVICE (PM2)
echo ======================================================================
echo.
pm2 start core/ecosystem.config.js
pm2 save >nul 2>&1
echo.
echo [OK] 1win-sniper-hub dan 1win-tunnel berhasil dijalankan!
echo.
timeout /t 2 >nul
goto MENU

:OPEN_WEB
start https://topnodtools.web.id
goto MENU

:EXIT
cls
echo ======================================================================
echo    Service PM2 tetap berjalan aktif di background.
echo    Domain Live: https://topnodtools.web.id
echo ======================================================================
timeout /t 2 >nul
exit /b 0

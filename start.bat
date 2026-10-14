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
echo    [1] 📊 Lihat Status Proses (1win-sniper-hub & 1win-tunnel)
echo    [2] 📜 Lihat Live Logs Backend (Realtime Stream)
echo    [3] 🔄 Restart Service (1win-sniper-hub & 1win-tunnel)
echo    [4] 🛑 Hentikan Service (Stop 1win-sniper-hub & 1win-tunnel)
echo    [5] 🚀 Jalankan Ulang Service (Start 1win-sniper-hub & 1win-tunnel)
echo    [6] 🗑️ Hapus Service dari PM2 (Delete 1win-sniper-hub & 1win-tunnel)
echo    [7] 🔑 Set / Ubah Token Telegram Bot (Paste Token Langsung)
echo    [8] 🌐 Buka Web Terminal di Browser (topnodtools.web.id)
echo    [0] ❌ Keluar Menu (Service Tetap Berjalan di Background)
echo.
echo ======================================================================
set /p opt="Pilih menu [0-8]: "

if "%opt%"=="1" goto STATUS
if "%opt%"=="2" goto LOGS
if "%opt%"=="3" goto RESTART
if "%opt%"=="4" goto STOP
if "%opt%"=="5" goto START
if "%opt%"=="6" goto DELETE
if "%opt%"=="7" goto SET_TOKEN
if "%opt%"=="8" goto OPEN_WEB
if "%opt%"=="0" goto EXIT

echo [!] Pilihan tidak valid. Silakan pilih 0-8.
timeout /t 2 >nul
goto MENU

:STATUS
cls
echo ======================================================================
echo    📊 STATUS RUNNING PM2 PROCESSES (1WIN HUB & TUNNEL)
echo ======================================================================
echo.
pm2 status 1win-sniper-hub 1win-tunnel
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
echo [*] Merestart 1win-sniper-hub...
pm2 restart 1win-sniper-hub >nul 2>&1 || pm2 start core/ecosystem.config.js --only 1win-sniper-hub >nul 2>&1
echo [*] Merestart 1win-tunnel...
pm2 restart 1win-tunnel >nul 2>&1 || pm2 start core/ecosystem.config.js --only 1win-tunnel >nul 2>&1
pm2 save >nul 2>&1
echo.
echo [OK] Service 1win-sniper-hub & 1win-tunnel berhasil direstart!
echo.
timeout /t 2 >nul
goto MENU

:STOP
cls
echo ======================================================================
echo    🛑 MENGHENTIKAN 1WIN SNIPER HUB & CLOUDFLARE TUNNEL
echo ======================================================================
echo.
echo [*] Menghentikan 1win-sniper-hub...
pm2 stop 1win-sniper-hub >nul 2>&1
echo [*] Menghentikan 1win-tunnel...
pm2 stop 1win-tunnel >nul 2>&1
pm2 save >nul 2>&1
echo.
echo [OK] 1win-sniper-hub dan 1win-tunnel telah dihentikan (service lain tetap aman).
echo.
timeout /t 2 >nul
goto MENU

:START
cls
echo ======================================================================
echo    🚀 MENJALANKAN ULANG 1WIN SNIPER HUB & CLOUDFLARE TUNNEL
echo ======================================================================
echo.
echo [*] Memulai 1win-sniper-hub...
pm2 describe 1win-sniper-hub >nul 2>&1
if %errorlevel% equ 0 (
    pm2 restart 1win-sniper-hub >nul 2>&1
) else (
    pm2 start core/ecosystem.config.js --only 1win-sniper-hub >nul 2>&1
)
echo [*] Memulai 1win-tunnel...
pm2 describe 1win-tunnel >nul 2>&1
if %errorlevel% equ 0 (
    pm2 restart 1win-tunnel >nul 2>&1
) else (
    pm2 start core/ecosystem.config.js --only 1win-tunnel >nul 2>&1
)
pm2 save >nul 2>&1
echo.
echo [OK] 1win-sniper-hub dan 1win-tunnel berhasil dijalankan!
echo.
timeout /t 2 >nul
goto MENU

:DELETE
cls
echo ======================================================================
echo    🗑️ MENGHAPUS SERVICE DARI PM2 (DELETE 1WIN-HUB & 1WIN-TUNNEL)
echo ======================================================================
echo.
echo [*] Menghapus 1win-sniper-hub dari PM2...
pm2 delete 1win-sniper-hub >nul 2>&1
echo [*] Menghapus 1win-tunnel dari PM2...
pm2 delete 1win-tunnel >nul 2>&1
pm2 save >nul 2>&1
echo.
echo [OK] 1win-sniper-hub dan 1win-tunnel telah berhasil dihapus dari PM2!
echo.
timeout /t 2 >nul
goto MENU

:SET_TOKEN
cls
echo ======================================================================
echo    🔑 SET / UBAH TOKEN BOT TELEGRAM
echo ======================================================================
echo.
set "NEW_TOKEN="
set /p "NEW_TOKEN=Paste Token Telegram Bot Anda (dari @BotFather): "
if "%NEW_TOKEN%"=="" (
    echo.
    echo [!] Input kosong. Token tidak diubah.
    timeout /t 2 >nul
    goto MENU
)

%PYTHON_EXE% -c "import json, pathlib; env_path=pathlib.Path('core/.env'); lines=[l for l in (env_path.read_text(encoding='utf-8').splitlines() if env_path.exists() else []) if not l.startswith('TELEGRAM_BOT_TOKEN=')]; lines.append('TELEGRAM_BOT_TOKEN=' + '''%NEW_TOKEN%'''.strip()); env_path.write_text('\n'.join(lines) + '\n', encoding='utf-8'); cfg_path=pathlib.Path('core/config.json'); data=json.loads(cfg_path.read_text(encoding='utf-8')) if cfg_path.exists() else {}; data['telegram_bot_token']='''%NEW_TOKEN%'''.strip(); cfg_path.write_text(json.dumps(data, indent=2), encoding='utf-8')" >nul 2>&1

echo.
echo [*] Merestart 1win-sniper-hub dengan token baru...
pm2 restart 1win-sniper-hub >nul 2>&1
pm2 save >nul 2>&1
echo.
echo [OK] Token Telegram Bot berhasil disimpan dan 1win-sniper-hub telah aktif!
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

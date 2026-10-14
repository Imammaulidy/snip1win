@echo off
chcp 65001 >nul
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
    "%PYTHON_EXE%" -m pip install -r core\requirements.txt --quiet >nul 2>&1
)

:: 3. Setup Config Template jika belum ada
if not exist "core\config.json" (
    if exist "core\config.example.json" (
        copy /Y "core\config.example.json" "core\config.json" >nul 2>&1
    )
)

:: 4. Jalankan Service All-in-One via PM2 Otomatis Saat Launching
call pm2 delete 1win-tunnel >nul 2>&1
call pm2 describe 1win-sniper-hub >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Menyalakan 1win-sniper-hub via PM2...
    call pm2 start core/ecosystem.config.js --only 1win-sniper-hub >nul 2>&1
    call pm2 save >nul 2>&1
)

:MENU
cls
echo ======================================================================
echo    🪙 1WIN TOKEN SALE SNIPER HUB (ALL-IN-ONE CONTROL PANEL)
echo    Platform : Windows
echo    Backend  : Port 6000 (Auto Local IP)
echo    Domain   : https://botmicin.web.id
echo ======================================================================
echo    [1] 📊 Lihat Status Proses (1win-sniper-hub)
echo    [2] 📜 Lihat Live Logs Backend (Realtime Stream)
echo    [3] 🔄 Restart Service (1win-sniper-hub)
echo    [4] 🛑 Hentikan Service (Stop 1win-sniper-hub)
echo    [5] 🚀 Jalankan Ulang Service (Start 1win-sniper-hub)
echo    [6] 🗑️ Hapus Service dari PM2 (Delete 1win-sniper-hub)
echo    [7] 🔑 Set / Ubah Token Telegram Bot (Paste Token Langsung)
echo    [8] 🌐 Buka Web Terminal di Browser (botmicin.web.id)
echo    [0] ❌ Keluar Menu (Service Tetap Berjalan di Background)
echo.
echo ======================================================================
set "opt="
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
ping 127.0.0.1 -n 3 >nul
goto MENU

:STATUS
cls
echo ======================================================================
echo    📊 STATUS RUNNING PM2 PROCESS (1WIN SNIPER HUB)
echo ======================================================================
echo.
call pm2 status 1win-sniper-hub
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
call pm2 logs 1win-sniper-hub --lines 30
echo.
echo Tekan sembarang tombol untuk kembali ke menu...
pause >nul
goto MENU

:RESTART
cls
echo ======================================================================
echo    🔄 MERESTART 1WIN SNIPER HUB
echo ======================================================================
echo.
echo [*] Merestart 1win-sniper-hub...
call pm2 restart 1win-sniper-hub >nul 2>&1
if %errorlevel% neq 0 (
    call pm2 start core/ecosystem.config.js --only 1win-sniper-hub >nul 2>&1
)
call pm2 save >nul 2>&1
echo.
echo [OK] Service 1win-sniper-hub berhasil direstart!
echo.
ping 127.0.0.1 -n 3 >nul
goto MENU

:STOP
cls
echo ======================================================================
echo    🛑 MENGHENTIKAN 1WIN SNIPER HUB
echo ======================================================================
echo.
echo [*] Menghentikan 1win-sniper-hub...
call pm2 stop 1win-sniper-hub >nul 2>&1
call pm2 save >nul 2>&1
echo.
echo [OK] 1win-sniper-hub telah dihentikan (service lain tetap aman).
echo.
ping 127.0.0.1 -n 3 >nul
goto MENU

:START
cls
echo ======================================================================
echo    🚀 MENJALANKAN ULANG 1WIN SNIPER HUB
echo ======================================================================
echo.
echo [*] Memulai 1win-sniper-hub...
call pm2 describe 1win-sniper-hub >nul 2>&1
if %errorlevel% equ 0 (
    call pm2 restart 1win-sniper-hub >nul 2>&1
) else (
    call pm2 start core/ecosystem.config.js --only 1win-sniper-hub >nul 2>&1
)
call pm2 save >nul 2>&1
echo.
echo [OK] 1win-sniper-hub berhasil dijalankan!
echo.
ping 127.0.0.1 -n 3 >nul
goto MENU

:DELETE
cls
echo ======================================================================
echo    🗑️ MENGHAPUS SERVICE DARI PM2 (DELETE 1WIN-HUB)
echo ======================================================================
echo.
echo [*] Menghapus 1win-sniper-hub dari PM2...
call pm2 delete 1win-sniper-hub >nul 2>&1
call pm2 delete 1win-tunnel >nul 2>&1
call pm2 save >nul 2>&1
echo.
echo [OK] 1win-sniper-hub telah berhasil dihapus dari PM2!
echo.
ping 127.0.0.1 -n 3 >nul
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
    echo [!] Input kosong. Token tidak diubah.
    ping 127.0.0.1 -n 3 >nul
    goto MENU
)
"%PYTHON_EXE%" -c "import sys, json, pathlib; t=sys.argv[1].strip(); ep=pathlib.Path('core/.env'); lines=[l for l in (ep.read_text('utf-8').splitlines() if ep.exists() else []) if not l.startswith('TELEGRAM_BOT_TOKEN=')]; lines.append('TELEGRAM_BOT_TOKEN=' + t); ep.write_text('\n'.join(lines) + '\n', encoding='utf-8'); cp=pathlib.Path('core/config.json'); d=json.loads(cp.read_text('utf-8')) if cp.exists() else {}; d['telegram_bot_token']=t; cp.write_text(json.dumps(d, indent=2), encoding='utf-8')" "%NEW_TOKEN%" >nul 2>&1
echo [*] Merestart 1win-sniper-hub dengan token baru...
call pm2 restart 1win-sniper-hub >nul 2>&1
call pm2 save >nul 2>&1
echo [OK] Token Telegram Bot berhasil disimpan!
ping 127.0.0.1 -n 3 >nul
goto MENU

:OPEN_WEB
start https://botmicin.web.id
goto MENU

:EXIT
cls
echo ======================================================================
echo    Service PM2 tetap berjalan aktif di background.
echo    Domain Live: https://botmicin.web.id
echo ======================================================================
ping 127.0.0.1 -n 3 >nul
exit /b 0

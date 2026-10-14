@echo off
title 1WIN TOKEN SALE SNIPER HUB (BOT + WEB TERMINAL)
color 0A
cd /d "%~dp0"

echo ======================================================
echo    1WIN TOKEN SALE SNIPER HUB (SOLANA MAINNET)
echo    Port: 6000 (Auto Local IP) • Domain: topnodtools.web.id
echo ======================================================
echo.

if not exist "core\config.json" (
    if exist "core\config.example.json" (
        copy "core\config.example.json" "core\config.json" >nul
        echo [INFO] Berhasil membuat core\config.json baru dari template.
    )
)

echo Memeriksa dependensi Python...
python -m pip install -r requirements.txt --quiet

echo Menjalankan Telegram Bot dan Web Server di Port 6000...
python -m core.bot

pause

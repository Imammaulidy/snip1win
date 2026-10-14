@echo off
title 1WIN SNIPER HUB - PM2 LAUNCHER
color 0A
cd /d "%~dp0"

echo ======================================================================
echo    1WIN TOKEN SALE SNIPER HUB (PM2 BACKGROUND ENGINE)
echo    Backend: Port 6000 (Auto Local IP) • Cloudflare: topnodtools.web.id
echo ======================================================================
echo.

:: Bersihkan instance sebelumnya jika ada
pm2 delete 1win-sniper-hub 1win-tunnel >nul 2>&1

:: Jalankan kedua service (Bot Web Server + Cloudflare Tunnel)
pm2 start core/ecosystem.config.js
pm2 save

echo.
echo ======================================================================
echo [OK] 1win-sniper-hub dan 1win-tunnel berhasil dijalankan di background!
echo ======================================================================
pm2 status

echo.
echo [*] Menampilkan log backend secara live (Tekan Ctrl+C untuk keluar dari log)...
pm2 logs 1win-sniper-hub --lines 20

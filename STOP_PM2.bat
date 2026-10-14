@echo off
title STOP 1WIN SNIPER HUB PM2
cd /d "%~dp0"
pm2 stop 1win-sniper-hub
pm2 delete 1win-sniper-hub
pm2 stop 1win-tunnel
pm2 delete 1win-tunnel
pm2 save
echo.
echo [OK] 1win-sniper-hub & 1win-tunnel berhasil dihentikan dan dihapus dari PM2.
pause

#!/usr/bin/env bash
# ======================================================================
#  1WIN TOKEN SALE SNIPER HUB - STOP PM2 (LINUX / VPS / TERMUX)
# ======================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "   🛑 MENGHENTIKAN 1WIN SNIPER HUB & CLOUDFLARE TUNNEL (PM2)"
echo "======================================================================"
pm2 stop 1win-sniper-hub 1win-tunnel >/dev/null 2>&1 || true
pm2 delete 1win-sniper-hub 1win-tunnel >/dev/null 2>&1 || true
pm2 save >/dev/null 2>&1 || true

echo ""
echo "[OK] Seluruh proses (1win-sniper-hub & 1win-tunnel) telah dihentikan."
pm2 status

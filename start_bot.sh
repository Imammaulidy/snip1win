#!/usr/bin/env bash
# ======================================================================
#  1WIN TOKEN SALE SNIPER HUB - FOREGROUND / QUICK LAUNCHER
#  Untuk mode PM2 + Cloudflare Tunnel otomatis, gunakan: bash START_PM2.sh
# ======================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ "$1" == "--pm2" ]; then
  exec bash START_PM2.sh
fi

echo "======================================================"
echo "   1WIN TOKEN SALE SNIPER BOT (SOLANA MAINNET)"
echo "   [TIP] Jalankan 'bash START_PM2.sh' untuk mode PM2"
echo "======================================================"

if [ ! -f "core/config.json" ] && [ -f "core/config.example.json" ]; then
    cp "core/config.example.json" "core/config.json"
    echo "[INFO] Dibuat core/config.json baru dari template."
fi

# Gunakan python venv jika tersedia
if [ -f ".venv/bin/python" ]; then
    .venv/bin/pip install -r requirements.txt -q
    .venv/bin/python -m core.bot
else
    pip3 install -r requirements.txt -q 2>/dev/null || pip install -r requirements.txt -q
    python3 -m core.bot 2>/dev/null || python -m core.bot
fi

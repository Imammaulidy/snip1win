#!/bin/bash
cd "$(dirname "$0")"

echo "======================================================"
echo "   1WIN TOKEN SALE SNIPER BOT (SOLANA MAINNET)"
echo "======================================================"

if [ ! -f "core/config.json" ]; then
    if [ -f "core/config.example.json" ]; then
        cp "core/config.example.json" "core/config.json"
        echo "[INFO] Dibuat core/config.json baru dari template."
        echo "[!] Silakan edit core/config.json dengan token bot dan private key."
    fi
fi

pip install -r requirements.txt -q
python3 -m core.bot

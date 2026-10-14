#!/usr/bin/env bash
# ======================================================================
#  1WIN TOKEN SALE SNIPER HUB - ALL-IN-ONE LAUNCHER & MENU (LINUX / TERMUX)
#  Backend: Port 6000 (Auto Local IP) • Domain: https://topnodtools.web.id
# ======================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Deteksi Lingkungan Sistem
IS_TERMUX=false
if [ -n "$PREFIX" ] && [[ "$PREFIX" == *"com.termux"* ]]; then
  IS_TERMUX=true
fi

# 2. Periksa & Instalasi Dependensi Sistem Otomatis
if [ "$IS_TERMUX" = true ]; then
  command -v python >/dev/null 2>&1 || { echo "[*] Menginstal Python..."; pkg update -y && pkg install -y python; }
  command -v node >/dev/null 2>&1 || { echo "[*] Menginstal Node.js..."; pkg install -y nodejs; }
  command -v cloudflared >/dev/null 2>&1 || { echo "[*] Menginstal Cloudflared..."; pkg install -y cloudflared; }
else
  # Linux VPS (Ubuntu/Debian)
  if ! command -v python3 >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -y && sudo apt-get install -y python3 python3-pip python3-venv curl
    elif command -v yum >/dev/null 2>&1; then
      sudo yum install -y python3 python3-pip curl
    fi
  fi

  if ! command -v node >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -y && sudo apt-get install -y nodejs npm
    elif command -v yum >/dev/null 2>&1; then
      sudo yum install -y nodejs npm
    fi
  fi

  if ! command -v cloudflared >/dev/null 2>&1 && [ ! -f "core/bin/cloudflared" ]; then
    mkdir -p core/bin
    ARCH="$(uname -m)"
    if [ "$ARCH" = "x86_64" ]; then
      curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" -o core/bin/cloudflared
      chmod +x core/bin/cloudflared
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
      curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" -o core/bin/cloudflared
      chmod +x core/bin/cloudflared
    fi
  fi
fi

# 3. Instalasi PM2 jika belum ada
if ! command -v pm2 >/dev/null 2>&1; then
  if [ "$IS_TERMUX" = true ]; then
    npm install -g pm2
  else
    sudo npm install -g pm2 || npm install -g pm2 || npm install pm2
  fi
fi
export PATH="$PATH:$SCRIPT_DIR/node_modules/.bin:$(npm bin -g 2>/dev/null || true):$HOME/.npm-global/bin"

# 4. Setup Python Virtual Environment (.venv) & Dependensi
if [ ! -d ".venv" ]; then
  python3 -m venv .venv 2>/dev/null || python -m venv .venv 2>/dev/null || true
fi

if [ -f ".venv/bin/pip" ]; then
  PIP_EXEC=".venv/bin/pip"
else
  PIP_EXEC="pip3"
  command -v "$PIP_EXEC" >/dev/null 2>&1 || PIP_EXEC="pip"
fi

if [ -f "core/requirements.txt" ]; then
  $PIP_EXEC install -r core/requirements.txt -q
fi

# 5. Template Konfigurasi
if [ ! -f "core/config.json" ] && [ -f "core/config.example.json" ]; then
  cp "core/config.example.json" "core/config.json"
fi

if [ ! -f "core/.env" ]; then
  touch core/.env
  echo "PUBLIC_ACCESS=true" >> core/.env
fi

# 6. Jalankan PM2 Otomatis jika belum running
if ! pm2 describe 1win-sniper-hub >/dev/null 2>&1; then
  echo "[*] Menjalankan 1win-sniper-hub & Cloudflare Tunnel via PM2..."
  pm2 start core/ecosystem.config.js >/dev/null 2>&1
  pm2 save >/dev/null 2>&1 || true
fi

# 7. Tampilkan Interface Menu Interaktif
while true; do
  clear
  echo "======================================================================"
  echo "   🪙 1WIN TOKEN SALE SNIPER HUB (ALL-IN-ONE CONTROL PANEL)"
  if [ "$IS_TERMUX" = true ]; then
    echo "   Platform : Termux (Android)"
  else
    echo "   Platform : Linux VPS / Server"
  fi
  echo "   Backend  : Port 6000 (Auto Local IP)"
  echo "   Domain   : https://topnodtools.web.id"
  echo "======================================================================"
  echo ""
  echo "   [1] 📊 Lihat Status Proses PM2"
  echo "   [2] 📜 Lihat Live Logs Backend (Realtime Stream)"
  echo "   [3] 🔄 Restart Semua Service (Hub + Cloudflare Tunnel)"
  echo "   [4] 🛑 Hentikan Semua Service (Stop PM2)"
  echo "   [5] 🚀 Jalankan Ulang Service (Start PM2)"
  echo "   [0] ❌ Keluar Menu (Service Tetap Berjalan di Background)"
  echo ""
  echo "======================================================================"
  read -r -p "Pilih menu [0-5]: " opt

  case "$opt" in
    1)
      clear
      echo "======================================================================"
      echo "   📊 STATUS RUNNING PM2 PROCESSES"
      echo "======================================================================"
      echo ""
      pm2 status
      echo ""
      read -r -p "Tekan Enter untuk kembali ke menu..." dummy
      ;;
    2)
      clear
      echo "======================================================================"
      echo "   📜 LIVE LOGS BACKEND (Tekan Ctrl+C untuk kembali ke menu)"
      echo "======================================================================"
      echo ""
      pm2 logs 1win-sniper-hub --lines 30
      echo ""
      read -r -p "Tekan Enter untuk kembali ke menu..." dummy
      ;;
    3)
      clear
      echo "======================================================================"
      echo "   🔄 MERESTART 1WIN SNIPER HUB & CLOUDFLARE TUNNEL"
      echo "======================================================================"
      echo ""
      pm2 restart 1win-sniper-hub 1win-tunnel
      pm2 save >/dev/null 2>&1 || true
      echo ""
      echo "[OK] Service berhasil direstart!"
      sleep 2
      ;;
    4)
      clear
      echo "======================================================================"
      echo "   🛑 MENGHENTIKAN SEMUA SERVICE"
      echo "======================================================================"
      echo ""
      pm2 stop 1win-sniper-hub 1win-tunnel >/dev/null 2>&1 || true
      pm2 delete 1win-sniper-hub 1win-tunnel >/dev/null 2>&1 || true
      pm2 save >/dev/null 2>&1 || true
      echo ""
      echo "[OK] 1win-sniper-hub dan 1win-tunnel telah dihentikan."
      sleep 2
      ;;
    5)
      clear
      echo "======================================================================"
      echo "   🚀 MENJALANKAN SERVICE (PM2)"
      echo "======================================================================"
      echo ""
      pm2 start core/ecosystem.config.js
      pm2 save >/dev/null 2>&1 || true
      echo ""
      echo "[OK] 1win-sniper-hub dan 1win-tunnel berhasil dijalankan!"
      sleep 2
      ;;
    0)
      clear
      echo "======================================================================"
      echo "   Service PM2 tetap aktif di background."
      echo "   Domain Live: https://topnodtools.web.id"
      echo "======================================================================"
      exit 0
      ;;
    *)
      echo "[!] Pilihan tidak valid. Silakan pilih 0-5."
      sleep 2
      ;;
  esac
done

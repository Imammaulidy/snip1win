#!/usr/bin/env bash
# ======================================================================
#  1WIN TOKEN SALE SNIPER HUB - ALL-IN-ONE PM2 LAUNCHER (LINUX / VPS / TERMUX)
#  Backend: Port 6000 (Auto Local IP) • Cloudflare: topnodtools.web.id
# ======================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "   🚀 1WIN TOKEN SALE SNIPER HUB (ALL-IN-ONE PM2 LAUNCHER)"
echo "   Platform: Linux VPS / Termux Android"
echo "   Live Domain: https://topnodtools.web.id"
echo "======================================================================"
echo ""

# 1. Deteksi Lingkungan Sistem
IS_TERMUX=false
if [ -n "$PREFIX" ] && [[ "$PREFIX" == *"com.termux"* ]]; then
  IS_TERMUX=true
  echo "[+] Lingkungan terdeteksi: Termux (Android)"
else
  echo "[+] Lingkungan terdeteksi: Linux VPS / Standalone"
fi

# 2. Periksa / Instalasi Kebutuhan Dasar
echo "[*] Memeriksa dependensi sistem (Python, Node.js, PM2, Cloudflared)..."

if [ "$IS_TERMUX" = true ]; then
  command -v python >/dev/null 2>&1 || { echo "[*] Menginstal Python di Termux..."; pkg update -y && pkg install -y python; }
  command -v node >/dev/null 2>&1 || { echo "[*] Menginstal Node.js di Termux..."; pkg install -y nodejs; }
  command -v cloudflared >/dev/null 2>&1 || { echo "[*] Menginstal Cloudflared di Termux..."; pkg install -y cloudflared; }
else
  # Linux VPS / Ubuntu / Debian
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[*] Menginstal Python 3..."
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -y && sudo apt-get install -y python3 python3-pip python3-venv curl
    elif command -v yum >/dev/null 2>&1; then
      sudo yum install -y python3 python3-pip curl
    fi
  fi

  if ! command -v node >/dev/null 2>&1; then
    echo "[*] Menginstal Node.js & npm..."
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -y && sudo apt-get install -y nodejs npm
    elif command -v yum >/dev/null 2>&1; then
      sudo yum install -y nodejs npm
    fi
  fi

  # Binary Cloudflared Linux jika belum ada di sistem
  if ! command -v cloudflared >/dev/null 2>&1 && [ ! -f "core/bin/cloudflared" ]; then
    mkdir -p core/bin
    ARCH="$(uname -m)"
    echo "[*] Mengunduh binary Cloudflared untuk arsitektur ($ARCH)..."
    if [ "$ARCH" = "x86_64" ]; then
      curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" -o core/bin/cloudflared
      chmod +x core/bin/cloudflared
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
      curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" -o core/bin/cloudflared
      chmod +x core/bin/cloudflared
    else
      echo "[!] Arsitektur $ARCH memerlukan instalasi cloudflared manual."
    fi
  fi
fi

# 3. Instalasi PM2 jika belum tersedia
if ! command -v pm2 >/dev/null 2>&1; then
  echo "[*] Menginstal PM2 Process Manager secara global..."
  if [ "$IS_TERMUX" = true ]; then
    npm install -g pm2
  else
    sudo npm install -g pm2 || npm install -g pm2 || npm install pm2
  fi
fi

# Tambahkan path npm global / lokal jika diperlukan
export PATH="$PATH:$SCRIPT_DIR/node_modules/.bin:$(npm bin -g 2>/dev/null || true):$HOME/.npm-global/bin"

# 4. Setup Python Virtual Environment (.venv) & Dependensi
if [ ! -d ".venv" ]; then
  echo "[*] Membuat isolasi Python virtual environment (.venv)..."
  python3 -m venv .venv 2>/dev/null || python -m venv .venv 2>/dev/null || true
fi

if [ -f ".venv/bin/pip" ]; then
  PIP_EXEC=".venv/bin/pip"
  PYTHON_EXEC=".venv/bin/python"
else
  PIP_EXEC="pip3"
  PYTHON_EXEC="python3"
  command -v "$PIP_EXEC" >/dev/null 2>&1 || PIP_EXEC="pip"
  command -v "$PYTHON_EXEC" >/dev/null 2>&1 || PYTHON_EXEC="python"
fi

echo "[*] Menginstal dependensi Python dari requirements.txt..."
$PIP_EXEC install -r requirements.txt -q

# 5. Konfigurasi Awal (core/config.json & core/.env)
if [ ! -f "core/config.json" ] && [ -f "core/config.example.json" ]; then
  cp "core/config.example.json" "core/config.json"
  echo "[*] Dibuat core/config.json dari template contoh."
fi

if [ ! -f "core/.env" ]; then
  touch core/.env
  echo "PUBLIC_ACCESS=true" >> core/.env
fi

# 6. Bersihkan Instance PM2 Lama & Jalankan Service All-in-One
echo ""
echo "[*] Merestart & menjalankan 1WIN Sniper Hub + Cloudflare Tunnel di PM2..."
pm2 delete 1win-sniper-hub 1win-tunnel >/dev/null 2>&1 || true

pm2 start core/ecosystem.config.js
pm2 save >/dev/null 2>&1 || true

echo ""
echo "======================================================================"
echo " [OK] 1win-sniper-hub & 1win-tunnel AKTIF DI BACKGROUND PM2!"
echo " 🌐 Web & Mini App URL : https://topnodtools.web.id"
echo " 🤖 Telegram Bot        : Akses via Telegram"
echo "======================================================================"
echo ""
pm2 status

echo ""
echo "[*] Menampilkan live log 20 baris pertama (Tekan Ctrl+C untuk kembali ke terminal)..."
pm2 logs 1win-sniper-hub --lines 20

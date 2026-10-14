#!/usr/bin/env bash
# ======================================================================
#  1WIN TOKEN SALE SNIPER HUB - ALL-IN-ONE LAUNCHER & MENU (LINUX / TERMUX)
#  Backend: Port 6000 (Auto Local IP) • Domain: https://topnodtools.web.id
# ======================================================================

# Non-interactive mode agar tidak memunculkan popup konfigurasi kernel/layar merah di VPS
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

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
  # Linux VPS (Ubuntu/Debian) - Pastikan python3, pip, venv terpasang (bukan hanya python3)
  NEED_PKG=false
  if ! command -v python3 >/dev/null 2>&1 || ! command -v pip3 >/dev/null 2>&1 || ! python3 -c "import venv" >/dev/null 2>&1; then
    NEED_PKG=true
  fi

  if [ "$NEED_PKG" = true ]; then
    echo "[*] Menginstal dependensi sistem (python3, pip, venv, curl)..."
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -y && sudo apt-get install -y python3 python3-pip python3-venv python3-full curl || true
    elif command -v yum >/dev/null 2>&1; then
      sudo yum install -y python3 python3-pip curl || true
    fi
  fi

  if ! command -v node >/dev/null 2>&1; then
    echo "[*] Menginstal Node.js & npm..."
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -y && sudo apt-get install -y nodejs npm || true
    elif command -v yum >/dev/null 2>&1; then
      sudo yum install -y nodejs npm || true
    fi
  fi

  if ! command -v cloudflared >/dev/null 2>&1 && [ ! -f "core/bin/cloudflared" ]; then
    mkdir -p core/bin
    ARCH="$(uname -m)"
    echo "[*] Mengunduh binary Cloudflared ($ARCH)..."
    if [ "$ARCH" = "x86_64" ]; then
      curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" -o core/bin/cloudflared || true
      chmod +x core/bin/cloudflared 2>/dev/null || true
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
      curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" -o core/bin/cloudflared || true
      chmod +x core/bin/cloudflared 2>/dev/null || true
    fi
  fi
  if [ -f "core/bin/cloudflared" ]; then
    chmod +x core/bin/cloudflared 2>/dev/null || true
  fi
fi

# 3. Instalasi PM2 jika belum ada
if ! command -v pm2 >/dev/null 2>&1; then
  echo "[*] Menginstal PM2 Process Manager..."
  if [ "$IS_TERMUX" = true ]; then
    npm install -g pm2
  else
    sudo npm install -g pm2 || npm install -g pm2 || npm install pm2
  fi
fi
export PATH="$PATH:$SCRIPT_DIR/node_modules/.bin:$(npm bin -g 2>/dev/null || true):$HOME/.npm-global/bin"

# 4. Setup Python Virtual Environment (.venv) & Dependensi
echo "[*] Menyiapkan environment Python..."
if [ ! -d ".venv" ] || [ ! -f ".venv/bin/pip" ]; then
  echo "[*] Membuat virtual environment .venv..."
  rm -rf .venv 2>/dev/null || true
  python3 -m venv .venv 2>/dev/null || python -m venv .venv 2>/dev/null || true
fi

# Fallback install python3-venv jika .venv gagal dibuat
if [ ! -f ".venv/bin/pip" ] && command -v apt-get >/dev/null 2>&1; then
  sudo apt-get install -y python3-venv python3-full || true
  python3 -m venv .venv 2>/dev/null || true
fi

if [ -f ".venv/bin/pip" ]; then
  PIP_EXEC=".venv/bin/pip"
  PYTHON_EXEC=".venv/bin/python"
else
  PIP_EXEC="pip3"
  command -v "$PIP_EXEC" >/dev/null 2>&1 || PIP_EXEC="pip"
  PYTHON_EXEC="python3"
  command -v "$PYTHON_EXEC" >/dev/null 2>&1 || PYTHON_EXEC="python"
fi

if [ -f "core/requirements.txt" ]; then
  echo "[*] Menginstal dependensi Python dari core/requirements.txt..."
  if [ -f ".venv/bin/pip" ]; then
    $PIP_EXEC install -r core/requirements.txt
  else
    $PIP_EXEC install -r core/requirements.txt --break-system-packages || \
    $PIP_EXEC install -r core/requirements.txt || \
    $PIP_EXEC install --user -r core/requirements.txt --break-system-packages || true
  fi
fi

# Verifikasi dependensi wajib sebelum menjalankan PM2
echo "[*] Memverifikasi modul aiohttp & solana..."
if ! $PYTHON_EXEC -c "import aiohttp, telegram, solana" >/dev/null 2>&1; then
  echo "[!] Mencoba instalasi modul langsung..."
  $PIP_EXEC install aiohttp httpx solana solders python-telegram-bot base58 --break-system-packages || \
  $PIP_EXEC install aiohttp httpx solana solders python-telegram-bot base58 || true
fi

# 5. Template Konfigurasi
if [ ! -f "core/config.json" ] && [ -f "core/config.example.json" ]; then
  cp "core/config.example.json" "core/config.json"
fi

if [ ! -f "core/.env" ]; then
  touch core/.env
  echo "PUBLIC_ACCESS=true" >> core/.env
fi

# 6. Jalankan PM2 (HANYA jalankan service 1win-sniper-hub & 1win-tunnel, dilarang menyentuh aplikasi lain)
echo "[*] Menjalankan 1win-sniper-hub & 1win-tunnel via PM2..."
pkill -9 -f "tunnel_runner.py" 2>/dev/null || true
pkill -9 -f "topnodtools" 2>/dev/null || true
pm2 delete 1win-sniper-hub 1win-tunnel >/dev/null 2>&1 || true
pm2 start core/ecosystem.config.js --only 1win-sniper-hub >/dev/null 2>&1 || pm2 restart 1win-sniper-hub >/dev/null 2>&1 || true
pm2 start core/ecosystem.config.js --only 1win-tunnel >/dev/null 2>&1 || pm2 restart 1win-tunnel >/dev/null 2>&1 || true
pm2 save >/dev/null 2>&1 || true

# Cek status token Cloudflare Tunnel
CF_CHECK=""
if [ -f "core/.env" ]; then
  CF_CHECK=$(grep -E "^CLOUDFLARE_TUNNEL_TOKEN=" core/.env | cut -d'=' -f2- | tr -d ' "\r\n')
fi
if [ -z "$CF_CHECK" ] && [ ! -f "$HOME/.cloudflared/58eb85db-cd18-45a5-ad97-b6b99ea9848f.json" ]; then
  echo ""
  echo "⚠️  Catatan: Cloudflare Tunnel Token belum dikonfigurasi di core/.env."
  echo "    Gunakan Menu [7] -> [2] untuk memasukkan token Cloudflare jika ingin domain live."
  sleep 2
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
  echo "   [1] 📊 Lihat Status Proses (1win-sniper-hub & 1win-tunnel)"
  echo "   [2] 📜 Lihat Live Logs Backend & Tunnel (Realtime Stream)"
  echo "   [3] 🔄 Restart Service (1win-sniper-hub & 1win-tunnel)"
  echo "   [4] 🛑 Hentikan Service (Stop 1win-sniper-hub & 1win-tunnel)"
  echo "   [5] 🚀 Jalankan Ulang Service (Start 1win-sniper-hub & 1win-tunnel)"
  echo "   [6] 🗑️ Hapus Service dari PM2 (Delete 1win-sniper-hub & 1win-tunnel)"
  echo "   [7] 🔑 Set / Ubah Token (Telegram Bot & Cloudflare Tunnel)"
  echo "   [0] ❌ Keluar Menu (Service Tetap Berjalan di Background)"
  echo ""
  echo "======================================================================"
  read -r -p "Pilih menu [0-7]: " opt

  case "$opt" in
    1)
      clear
      echo "======================================================================"
      echo "   📊 STATUS PROSES 1WIN SNIPER HUB & TUNNEL"
      echo "======================================================================"
      echo ""
      pm2 status 1win-sniper-hub 1win-tunnel 2>/dev/null || pm2 status
      echo ""
      read -r -p "Tekan Enter untuk kembali ke menu..." dummy
      ;;
    2)
      clear
      echo "======================================================================"
      echo "   📜 LIVE LOGS BACKEND & TUNNEL (Tekan Ctrl+C untuk kembali ke menu)"
      echo "======================================================================"
      echo ""
      pm2 logs 1win-sniper-hub 1win-tunnel --lines 30
      echo ""
      read -r -p "Tekan Enter untuk kembali ke menu..." dummy
      ;;
    3)
      clear
      echo "======================================================================"
      echo "   🔄 MERESTART 1WIN SNIPER HUB & CLOUDFLARE TUNNEL"
      echo "======================================================================"
      echo ""
      echo "[*] Membersihkan proses tunnel lama..."
      pkill -9 -f "tunnel_runner.py" 2>/dev/null || true
      pkill -9 -f "topnodtools" 2>/dev/null || true
      sleep 1
      echo "[*] Merestart 1win-sniper-hub..."
      pm2 restart 1win-sniper-hub >/dev/null 2>&1 || pm2 start core/ecosystem.config.js --only 1win-sniper-hub >/dev/null 2>&1 || true
      echo "[*] Merestart 1win-tunnel..."
      pm2 restart 1win-tunnel >/dev/null 2>&1 || pm2 start core/ecosystem.config.js --only 1win-tunnel >/dev/null 2>&1 || true
      pm2 save >/dev/null 2>&1 || true
      echo ""
      echo "[OK] Service 1win-sniper-hub & 1win-tunnel berhasil direstart!"
      sleep 2
      ;;
    4)
      clear
      echo "======================================================================"
      echo "   🛑 MENGHENTIKAN 1WIN SNIPER HUB & CLOUDFLARE TUNNEL"
      echo "======================================================================"
      echo ""
      echo "[*] Menghentikan 1win-sniper-hub..."
      pm2 stop 1win-sniper-hub >/dev/null 2>&1 || true
      echo "[*] Menghentikan 1win-tunnel..."
      pm2 stop 1win-tunnel >/dev/null 2>&1 || true
      pkill -9 -f "tunnel_runner.py" 2>/dev/null || true
      pkill -9 -f "topnodtools" 2>/dev/null || true
      pm2 save >/dev/null 2>&1 || true
      echo ""
      echo "[OK] 1win-sniper-hub dan 1win-tunnel telah dihentikan (service lain tetap aman)."
      sleep 2
      ;;
    5)
      clear
      echo "======================================================================"
      echo "   🚀 MENJALANKAN ULANG 1WIN SNIPER HUB & CLOUDFLARE TUNNEL"
      echo "======================================================================"
      echo ""
      echo "[*] Membersihkan proses tunnel lama..."
      pkill -9 -f "tunnel_runner.py" 2>/dev/null || true
      pkill -9 -f "topnodtools" 2>/dev/null || true
      sleep 1
      echo "[*] Memulai service 1win-sniper-hub..."
      pm2 restart 1win-sniper-hub >/dev/null 2>&1 || pm2 start core/ecosystem.config.js --only 1win-sniper-hub >/dev/null 2>&1 || true
      echo "[*] Memulai service 1win-tunnel..."
      pm2 restart 1win-tunnel >/dev/null 2>&1 || pm2 start core/ecosystem.config.js --only 1win-tunnel >/dev/null 2>&1 || true
      pm2 save >/dev/null 2>&1 || true
      echo ""
      echo "[OK] 1win-sniper-hub dan 1win-tunnel berhasil dijalankan!"
      sleep 2
      ;;
    6)
      clear
      echo "======================================================================"
      echo "   🗑️ HAPUS SERVICE DARI PM2 (DELETE 1WIN-HUB & 1WIN-TUNNEL)"
      echo "======================================================================"
      echo ""
      echo "[*] Menghapus 1win-sniper-hub dari PM2..."
      pm2 delete 1win-sniper-hub >/dev/null 2>&1 || true
      echo "[*] Menghapus 1win-tunnel dari PM2..."
      pm2 delete 1win-tunnel >/dev/null 2>&1 || true
      pkill -9 -f "tunnel_runner.py" 2>/dev/null || true
      pkill -9 -f "topnodtools" 2>/dev/null || true
      pm2 save >/dev/null 2>&1 || true
      echo ""
      echo "[OK] 1win-sniper-hub dan 1win-tunnel telah berhasil dihapus dari PM2!"
      echo "     (Service lain seperti depilQR & depilStellar tetap aman)."
      sleep 2
      ;;
    7)
      clear
      echo "======================================================================"
      echo "   🔑 PENGATURAN KREDENSIAL / TOKEN (1WIN SNIPER)"
      echo "======================================================================"
      echo ""
      CUR_TG_TOKEN=""
      CUR_CF_TOKEN=""
      if [ -f "core/.env" ]; then
        CUR_TG_TOKEN=$(grep -E "^TELEGRAM_BOT_TOKEN=" core/.env | cut -d'=' -f2- | tr -d ' "\r')
        CUR_CF_TOKEN=$(grep -E "^CLOUDFLARE_TUNNEL_TOKEN=" core/.env | cut -d'=' -f2- | tr -d ' "\r')
      fi
      if [ -z "$CUR_TG_TOKEN" ] && [ -f "core/config.json" ]; then
        CUR_TG_TOKEN=$(grep -o '"telegram_bot_token": *"[^"]*"' core/config.json | cut -d'"' -f4)
      fi

      if [ -n "$CUR_TG_TOKEN" ] && [ "$CUR_TG_TOKEN" != "YOUR_TELEGRAM_BOT_TOKEN_FROM_BOTFATHER" ]; then
        TOKEN_LEN=${#CUR_TG_TOKEN}
        if [ "$TOKEN_LEN" -gt 15 ]; then
          echo "1. Token Telegram Bot : ${CUR_TG_TOKEN:0:8}********${CUR_TG_TOKEN: -6}"
        else
          echo "1. Token Telegram Bot : Terpasang"
        fi
      else
        echo "1. Token Telegram Bot : (Belum diatur)"
      fi

      if [ -n "$CUR_CF_TOKEN" ]; then
        CF_LEN=${#CUR_CF_TOKEN}
        if [ "$CF_LEN" -gt 15 ]; then
          echo "2. Token Cloudflare   : ${CUR_CF_TOKEN:0:8}********${CUR_CF_TOKEN: -6}"
        else
          echo "2. Token Cloudflare   : Terpasang"
        fi
      else
        echo "2. Token Cloudflare   : (Belum diatur - dibutuhkan untuk domain topnodtools.web.id)"
      fi

      echo ""
      echo "   [1] Ubah Token Telegram Bot"
      echo "   [2] Ubah Token Cloudflare Tunnel (topnodtools)"
      echo "   [0] Kembali ke Menu Utama"
      echo ""
      read -r -p "Pilih opsi [0-2]: " t_opt

      case "$t_opt" in
        1)
          echo ""
          read -r -p "Paste Token Telegram Bot (dari @BotFather): " NEW_TG
          NEW_TG=$(echo "$NEW_TG" | tr -d ' \r\n"')
          if [ -n "$NEW_TG" ]; then
            touch core/.env
            if grep -q "^TELEGRAM_BOT_TOKEN=" core/.env; then
              sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=${NEW_TG}|" core/.env
            else
              echo "TELEGRAM_BOT_TOKEN=${NEW_TG}" >> core/.env
            fi

            if [ -f "core/config.json" ]; then
              $PYTHON_EXEC -c "
import json, pathlib
p = pathlib.Path('core/config.json')
try:
    d = json.loads(p.read_text(encoding='utf-8'))
except:
    d = {}
d['telegram_bot_token'] = '''${NEW_TG}'''
p.write_text(json.dumps(d, indent=2), encoding='utf-8')
" 2>/dev/null || true
            fi

            echo ""
            echo "[*] Merestart 1win-sniper-hub dengan token baru..."
            pm2 restart 1win-sniper-hub >/dev/null 2>&1 || pm2 start core/ecosystem.config.js --only 1win-sniper-hub >/dev/null 2>&1 || true
            pm2 save >/dev/null 2>&1 || true
            echo ""
            echo "[OK] Token Telegram Bot berhasil disimpan!"
          else
            echo ""
            echo "[!] Input kosong. Token tidak diubah."
          fi
          sleep 2
          ;;
        2)
          echo ""
          read -r -p "Paste Token Cloudflare Tunnel (base64 token): " NEW_CF
          NEW_CF=$(echo "$NEW_CF" | tr -d ' \r\n"')
          if [ -n "$NEW_CF" ]; then
            touch core/.env
            if grep -q "^CLOUDFLARE_TUNNEL_TOKEN=" core/.env; then
              sed -i "s|^CLOUDFLARE_TUNNEL_TOKEN=.*|CLOUDFLARE_TUNNEL_TOKEN=${NEW_CF}|" core/.env
            else
              echo "CLOUDFLARE_TUNNEL_TOKEN=${NEW_CF}" >> core/.env
            fi

            echo ""
            echo "[*] Merestart 1win-tunnel dengan token Cloudflare baru..."
            pkill -9 -f "tunnel_runner.py" 2>/dev/null || true
            pkill -9 -f "topnodtools" 2>/dev/null || true
            pm2 restart 1win-tunnel >/dev/null 2>&1 || pm2 start core/ecosystem.config.js --only 1win-tunnel >/dev/null 2>&1 || true
            pm2 save >/dev/null 2>&1 || true
            echo ""
            echo "[OK] Token Cloudflare Tunnel berhasil disimpan dan 1win-tunnel aktif!"
          else
            echo ""
            echo "[!] Input kosong. Token tidak diubah."
          fi
          sleep 2
          ;;
        *)
          ;;
      esac
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
      echo "[!] Pilihan tidak valid. Silakan pilih 0-7."
      sleep 2
      ;;
  esac
done

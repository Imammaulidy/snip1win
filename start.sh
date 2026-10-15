#!/usr/bin/env bash
# ======================================================================
#  1WIN TOKEN SALE SNIPER HUB - ALL-IN-ONE LAUNCHER & MENU (LINUX / TERMUX)
#  Backend: Port 6000 (Auto Local IP) • Domain: https://botmicin.web.id
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
else
  # Linux VPS (Ubuntu/Debian) - Pastikan python3, pip, venv terpasang
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

# 6. Jalankan PM2 (HANYA jalankan service 1win-sniper-hub, dilarang menyentuh aplikasi lain)
echo "[*] Menjalankan 1win-sniper-hub via PM2..."
pm2 delete 1win-tunnel >/dev/null 2>&1 || true
pm2 describe 1win-sniper-hub >/dev/null 2>&1
if [ $? -ne 0 ]; then
  pm2 start core/ecosystem.config.js --only 1win-sniper-hub >/dev/null 2>&1 || true
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
  echo "   Domain   : https://botmicin.web.id"
  echo "======================================================================"
  echo ""
  echo "   [1] 📊 Lihat Status Proses (1win-sniper-hub)"
  echo "   [2] 📜 Lihat Live Logs Backend (Realtime Stream)"
  echo "   [3] 🔄 Restart Service (1win-sniper-hub)"
  echo "   [4] 🛑 Hentikan Service (Stop 1win-sniper-hub)"
  echo "   [5] 🚀 Jalankan Ulang Service (Start 1win-sniper-hub)"
  echo "   [6] 🗑️ Hapus Service dari PM2 (Delete 1win-sniper-hub)"
  echo "   [7] 🔑 Set / Ubah Token Bot Telegram (Paste Token Langsung)"
  echo "   [8] 🌐 Setup Reverse Proxy Nginx & SSL (botmicin.web.id)"
  echo "   [0] ❌ Keluar Menu (Service Tetap Berjalan di Background)"
  echo ""
  echo "======================================================================"
  read -r -p "Pilih menu [0-8]: " opt

  case "$opt" in
    1)
      clear
      echo "======================================================================"
      echo "   📊 STATUS PROSES 1WIN SNIPER HUB"
      echo "======================================================================"
      echo ""
      pm2 status 1win-sniper-hub 2>/dev/null || pm2 status
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
      echo "   🔄 MERESTART 1WIN SNIPER HUB"
      echo "======================================================================"
      echo ""
      echo "[*] Merestart 1win-sniper-hub..."
      pm2 restart 1win-sniper-hub >/dev/null 2>&1 || pm2 start core/ecosystem.config.js --only 1win-sniper-hub >/dev/null 2>&1 || true
      pm2 save >/dev/null 2>&1 || true
      echo ""
      echo "[OK] Service 1win-sniper-hub berhasil direstart!"
      sleep 2
      ;;
    4)
      clear
      echo "======================================================================"
      echo "   🛑 MENGHENTIKAN 1WIN SNIPER HUB"
      echo "======================================================================"
      echo ""
      echo "[*] Menghentikan 1win-sniper-hub..."
      pm2 stop 1win-sniper-hub >/dev/null 2>&1 || true
      pm2 save >/dev/null 2>&1 || true
      echo ""
      echo "[OK] 1win-sniper-hub telah dihentikan (service lain tetap aman)."
      sleep 2
      ;;
    5)
      clear
      echo "======================================================================"
      echo "   🚀 MENJALANKAN ULANG 1WIN SNIPER HUB"
      echo "======================================================================"
      echo ""
      echo "[*] Memulai service 1win-sniper-hub..."
      pm2 restart 1win-sniper-hub >/dev/null 2>&1 || pm2 start core/ecosystem.config.js --only 1win-sniper-hub >/dev/null 2>&1 || true
      pm2 save >/dev/null 2>&1 || true
      echo ""
      echo "[OK] 1win-sniper-hub berhasil dijalankan!"
      sleep 2
      ;;
    6)
      clear
      echo "======================================================================"
      echo "   🗑️ HAPUS SERVICE DARI PM2 (DELETE 1WIN-HUB)"
      echo "======================================================================"
      echo ""
      echo "[*] Menghapus 1win-sniper-hub dari PM2..."
      pm2 delete 1win-sniper-hub >/dev/null 2>&1 || true
      pm2 delete 1win-tunnel >/dev/null 2>&1 || true
      pm2 save >/dev/null 2>&1 || true
      echo ""
      echo "[OK] 1win-sniper-hub telah berhasil dihapus dari PM2!"
      echo "     (Service lain seperti depilQR & depilStellar tetap aman)."
      sleep 2
      ;;
    7)
      clear
      echo "======================================================================"
      echo "   🔑 SET / UBAH TOKEN BOT TELEGRAM"
      echo "======================================================================"
      echo ""
      CUR_TG_TOKEN=""
      if [ -f "core/.env" ]; then
        CUR_TG_TOKEN=$(grep -E "^TELEGRAM_BOT_TOKEN=" core/.env | cut -d'=' -f2- | tr -d ' "\r')
      fi
      if [ -z "$CUR_TG_TOKEN" ] && [ -f "core/config.json" ]; then
        CUR_TG_TOKEN=$(grep -o '"telegram_bot_token": *"[^"]*"' core/config.json | cut -d'"' -f4)
      fi

      if [ -n "$CUR_TG_TOKEN" ] && [ "$CUR_TG_TOKEN" != "YOUR_TELEGRAM_BOT_TOKEN_FROM_BOTFATHER" ]; then
        TOKEN_LEN=${#CUR_TG_TOKEN}
        if [ "$TOKEN_LEN" -gt 15 ]; then
          echo "Token saat ini : ${CUR_TG_TOKEN:0:8}********${CUR_TG_TOKEN: -6}"
        else
          echo "Token saat ini : Terpasang"
        fi
      else
        echo "Token saat ini : (Belum diatur / Masih default template)"
      fi

      echo ""
      read -r -p "Paste Token Telegram Bot Anda (dari @BotFather): " NEW_TG
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
        echo "[OK] Token Telegram Bot berhasil disimpan dan 1win-sniper-hub telah aktif!"
      else
        echo ""
        echo "[!] Input kosong. Token tidak diubah."
      fi
      sleep 2
      ;;
    8)
      clear
      echo "======================================================================"
      echo "   🌐 SETUP REVERSE PROXY NGINX & SSL (botmicin.web.id)"
      echo "======================================================================"
      echo ""
      AUTO_LOCAL_IP=$($PYTHON_EXEC -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2>/dev/null)
      if [ -z "$AUTO_LOCAL_IP" ]; then
        AUTO_LOCAL_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7}' | head -n 1)
      fi
      if [ -z "$AUTO_LOCAL_IP" ]; then
        AUTO_LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
      fi
      if [ -z "$AUTO_LOCAL_IP" ]; then
        AUTO_LOCAL_IP="10.0.0.4"
      fi

      echo "Target Domain : https://botmicin.web.id"
      echo "Backend Target: http://${AUTO_LOCAL_IP}:6000 (Murni IP Lokal Otomatis)"
      echo ""
      echo "Menu ini akan mengonfigurasi Nginx di VPS untuk merutekan:"
      echo "https://botmicin.web.id -> http://${AUTO_LOCAL_IP}:6000"
      echo ""
      read -r -p "Lanjutkan konfigurasi otomatis Nginx? (y/n): " confirm_nginx
      if [[ "$confirm_nginx" =~ ^[Yy]$ ]]; then
        echo ""
        echo "[1/4] Memeriksa dependensi Nginx, Certbot & Firewall sistem..."
        if command -v apt-get >/dev/null 2>&1; then
          sudo apt-get update -y && sudo apt-get install -y nginx certbot python3-certbot-nginx ufw || true
        elif command -v yum >/dev/null 2>&1; then
          sudo yum install -y epel-release && sudo yum install -y nginx certbot python3-certbot-nginx || true
        fi

        echo "[*] Membuka port 80 dan 443 di firewall OS (UFW & iptables)..."
        if command -v ufw >/dev/null 2>&1; then
          sudo ufw allow 80/tcp >/dev/null 2>&1 || true
          sudo ufw allow 443/tcp >/dev/null 2>&1 || true
          sudo ufw allow 'Nginx Full' >/dev/null 2>&1 || true
          sudo ufw reload >/dev/null 2>&1 || true
        fi
        sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
        sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || true

        echo "[2/4] Menulis konfigurasi Nginx untuk botmicin.web.id (Upstream: http://${AUTO_LOCAL_IP}:6000)..."
        NGINX_CONF="/etc/nginx/sites-available/botmicin"
        if [ ! -d "/etc/nginx/sites-available" ]; then
          NGINX_CONF="/etc/nginx/conf.d/botmicin.conf"
        fi

        cat << EOF | sudo tee "$NGINX_CONF" > /dev/null
server {
    listen 80;
    server_name botmicin.web.id www.botmicin.web.id;

    location / {
        proxy_pass http://${AUTO_LOCAL_IP}:6000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

        if [ -d "/etc/nginx/sites-enabled" ]; then
          sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
          sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/botmicin
        fi

        echo "[3/4] Menguji & me-restart Nginx service..."
        sudo nginx -t
        sudo systemctl enable nginx 2>/dev/null || true
        sudo systemctl restart nginx 2>/dev/null || sudo service nginx restart || true

        echo "[4/4] Menerbitkan sertifikat SSL gratis (Let's Encrypt Certbot)..."
        echo "Pastikan DNS A record botmicin.web.id sudah mengarah ke IP 20.204.42.222!"
        if sudo certbot --nginx -d botmicin.web.id --non-interactive --agree-tos --register-unsafely-without-email --redirect; then
          echo ""
          echo "======================================================================"
          echo "✅ [SUKSES] Setup Reverse Proxy Nginx & SSL Berhasil!"
          echo "🌐 Web Terminal & Mini App Aktif di: https://botmicin.web.id"
          echo "======================================================================"
        else
          echo ""
          echo "======================================================================"
          echo "⚠️  [PERHATIAN] Certbot timeout saat memvalidasi port 80!"
          echo "    Penyebab: Firewall Azure (Network Security Group / NSG) memblokir port 80 & 443."
          echo ""
          echo "    Langkah Buka Port di Azure Portal:"
          echo "    1. Masuk ke Azure Portal -> Virtual Machines -> ydc-studio"
          echo "    2. Pilih menu 'Networking' di bilah kiri"
          echo "    3. Klik 'Add inbound port rule'"
          echo "    4. Destination port ranges: 80, 443"
          echo "    5. Protocol: TCP | Action: Allow | Name: Allow-Web"
          echo "    6. Klik 'Add'"
          echo "    Setelah rule Azure tersimpan, jalankan ulang menu [8] ini!"
          echo "======================================================================"
        fi
      else
        echo "[*] Dibatalkan."
      fi
      echo ""
      read -r -p "Tekan Enter untuk kembali ke menu..." dummy
      ;;
    0)
      clear
      echo "======================================================================"
      echo "   Service PM2 tetap aktif di background."
      echo "   Domain Live: https://botmicin.web.id"
      echo "======================================================================"
      exit 0
      ;;
    *)
      echo "[!] Pilihan tidak valid. Silakan pilih 0-8."
      sleep 2
      ;;
  esac
done

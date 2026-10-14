# 🪙 1WIN Token Sale Sniper Hub (Telegram Bot & Web Terminal)

Bot sniper presale & DEX resmi untuk token **$1WIN** on-chain Solana Mainnet dengan Web Terminal port 6000 dan Cloudflare Tunnel domain `topnodtools.web.id`.

### 📌 Detail Kontrak Resmi ($1WIN)
- **Token Mint (CA)**: `FjPKUGnF5zBpdEv18gT8FJCtxh3MKrFkoeYekgYr1win`
- **Network**: Solana Mainnet (SPL Token)
- **Program ID**: `GWvQinGBRa7ZUzhXY23MrLjdsx3KfRGxH8yXURBwrz1R`
- **Harga Presale**: $0.03 USDC | **Alokasi**: 130,000,000 $1WIN
- **Web Terminal**: `https://topnodtools.web.id` (`http://<AUTO_LOCAL_IP>:6000`)

---

## ⚡ Instalasi Cepat (Copy-Paste Ready)

### 📱 1. Termux (Android)
```bash
pkg update -y && pkg install -y git python
git clone https://github.com/Imammaulidy/snip1win.git
cd snip1win
pip install -r requirements.txt
sh start_bot.sh
```

### 💻 2. Windows (PC / Laptop)
1. Buka PowerShell / Command Prompt lalu jalankan:
```cmd
git clone https://github.com/Imammaulidy/snip1win.git
cd snip1win
pip install -r requirements.txt
```
2. **Jalankan Bot**:
- **Mode Background PM2 (Recommended)**: Double-click file [`START_PM2.bat`](START_PM2.bat) (Otomatis menjalankan Bot Port 6000 + Cloudflare Tunnel `topnodtools.web.id`).
- **Mode Konsol Biasa**: Double-click file [`START_BOT.bat`](START_BOT.bat).
- **Hentikan PM2**: Double-click [`STOP_PM2.bat`](STOP_PM2.bat).

---

## 🎮 Fitur Interaksi Cepat & Multi-Worker

| Tombol / Fitur | Cara Kerja Instan |
| :--- | :--- |
| **📱 Telegram Mini App (TMA)** | Buka terminal trading langsung di dalam aplikasi Telegram tanpa browser luar. |
| **🛡️ Worker "Satpam" (Radar)** | Radar background 250ms memantau status presale & pool DEX on-chain Solana. |
| **⚡ Worker "Buy" Zero-Latency** | Begitu status presale live, dieksekusi sub-milidetik tanpa delay. |
| **🔴 Worker "Sell" 1-Klik** | Tombol instan Sell 25%, 50%, 100% via Jupiter Swap di Bot & Mini App. |
| **🔑 Multi-User Wallet Isolation** | Setiap pengguna mengelola wallet masing-masing secara privat & terenkripsi. |
| **🌐 Web Terminal Sync** | State Telegram Bot & Web Terminal 100% sinkron via IP Lokal Otomatis Port 6000. |

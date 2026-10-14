# 🪙 1WIN Token Sale Sniper Hub (Telegram Bot & Web Terminal)

Bot sniper presale & DEX resmi untuk token **$1WIN** on-chain Solana Mainnet dengan Web Terminal port 6000 dan domain `botmicin.web.id`.

### 📌 Detail Kontrak Resmi ($1WIN)
- **Token Mint (CA)**: `FjPKUGnF5zBpdEv18gT8FJCtxh3MKrFkoeYekgYr1win`
- **Network**: Solana Mainnet (SPL Token)
- **Program ID**: `GWvQinGBRa7ZUzhXY23MrLjdsx3KfRGxH8yXURBwrz1R`
- **Harga Presale**: $0.03 USDC | **Alokasi**: 130,000,000 $1WIN
- **Web Terminal / Mini App**: `https://botmicin.web.id` (`http://<AUTO_LOCAL_IP>:6000`)

---

## ⚡ Instalasi Cepat (Copy-Paste Ready)

### 🐧 1. Linux VPS (Ubuntu / Debian / CentOS)
Jalankan satu perintah berikut di terminal VPS:
```bash
git clone https://github.com/Imammaulidy/snip1win.git && cd snip1win && bash start.sh
```
> Otomatis memeriksa dependensi sistem, mengisolasi virtualenv, menjalankan PM2 Hub untuk `botmicin.web.id`, dan menampilkan Control Panel interaktif. Gunakan Menu `[8]` untuk konfigurasi otomatis Reverse Proxy Nginx & SSL Certbot.

### 📱 2. Termux (Android)
```bash
pkg update -y && pkg install -y git python nodejs
git clone https://github.com/Imammaulidy/snip1win.git
cd snip1win
bash start.sh
```

### 💻 3. Windows (PC / Laptop)
1. Clone repositori:
```cmd
git clone https://github.com/Imammaulidy/snip1win.git
cd snip1win
```
2. Double-click file [`start.bat`](start.bat).
> Otomatis menginstal paket pendukung ke background PM2 dan memunculkan Control Panel menu untuk melihat status, live logs, restart, atau stop service.

---

## 🎮 Fitur Interaksi Cepat & Multi-Worker

| Tombol / Fitur | Cara Kerja Instan |
| :--- | :--- |
| **📱 Telegram Mini App (TMA)** | Buka terminal trading langsung di dalam aplikasi Telegram tanpa browser luar (`https://botmicin.web.id`). |
| **🛡️ Worker "Satpam" (Radar)** | Radar background 250ms memantau status presale & pool DEX on-chain Solana. |
| **⚡ Worker "Buy" Zero-Latency** | Begitu status presale live, dieksekusi sub-milidetik tanpa delay. |
| **🔴 Worker "Sell" 1-Klik** | Tombol instan Sell 25%, 50%, 100% via Jupiter Swap di Bot & Mini App. |
| **🔑 Multi-User Wallet Isolation** | Setiap pengguna mengelola wallet masing-masing secara privat & terenkripsi. |
| **🌐 Web Terminal Sync** | State Telegram Bot & Web Terminal 100% sinkron via IP Lokal Otomatis Port 6000. |

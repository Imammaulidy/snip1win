const path = require('path');
const fs = require('fs');
const os = require('os');

// Deteksi IP Lokal LAN aktif secara otomatis
function getLocalIp() {
  try {
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
      for (const iface of interfaces[name]) {
        if (iface.family === 'IPv4' && !iface.internal) {
          return iface.address;
        }
      }
    }
  } catch (e) {}
  return '127.0.0.1';
}

const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';

// 1. Baca .env jika tersedia
function loadEnv() {
  const envCandidates = [
    path.resolve(rootDir, 'core', '.env'),
    path.resolve(rootDir, '.env')
  ];
  for (const envFile of envCandidates) {
    if (fs.existsSync(envFile)) {
      try {
        const lines = fs.readFileSync(envFile, 'utf8').split('\n');
        for (let line of lines) {
          line = line.trim();
          if (line && !line.startsWith('#') && line.includes('=')) {
            const idx = line.indexOf('=');
            const k = line.substring(0, idx).trim();
            const v = line.substring(idx + 1).trim();
            if (!process.env[k]) {
              process.env[k] = v;
            }
          }
        }
      } catch (e) {}
    }
  }
}
loadEnv();

// Deteksi IP Lokal LAN aktif secara otomatis
function getLocalIp() {
  try {
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
      for (const iface of interfaces[name]) {
        if (iface.family === 'IPv4' && !iface.internal) {
          return iface.address;
        }
      }
    }
  } catch (e) {}
  return '127.0.0.1';
}

const localIp = getLocalIp();

// Deteksi Python interpreter yang valid secara dinamis
let pythonPath = isWin ? 'python' : 'python3';
if (isWin) {
  const venvPythonw = path.resolve(rootDir, '.venv', 'Scripts', 'pythonw.exe');
  const venvPython = path.resolve(rootDir, '.venv', 'Scripts', 'python.exe');
  if (fs.existsSync(venvPythonw)) {
    pythonPath = venvPythonw;
  } else if (fs.existsSync(venvPython)) {
    pythonPath = venvPython;
  }
} else {
  const venvPython = path.resolve(rootDir, '.venv', 'bin', 'python');
  const venvPython3 = path.resolve(rootDir, '.venv', 'bin', 'python3');
  if (fs.existsSync(venvPython)) {
    pythonPath = venvPython;
  } else if (fs.existsSync(venvPython3)) {
    pythonPath = venvPython3;
  }
}

// Deteksi binary cloudflared secara dinamis
let cloudflaredPath = 'cloudflared';
const winBin = path.resolve(__dirname, 'bin', 'cloudflared.exe');
const projectWinBin = path.resolve(rootDir, 'core', 'bin', 'cloudflared.exe');
const linuxBin = path.resolve(__dirname, 'bin', 'cloudflared');
const projectLinuxBin = path.resolve(rootDir, 'core', 'bin', 'cloudflared');
const termuxBin = '/data/data/com.termux/files/usr/bin/cloudflared';
const usrLocalBin = '/usr/local/bin/cloudflared';

if (isWin) {
  if (fs.existsSync(winBin)) cloudflaredPath = winBin;
  else if (fs.existsSync(projectWinBin)) cloudflaredPath = projectWinBin;
} else {
  if (fs.existsSync(linuxBin)) cloudflaredPath = linuxBin;
  else if (fs.existsSync(projectLinuxBin)) cloudflaredPath = projectLinuxBin;
  else if (fs.existsSync(termuxBin)) cloudflaredPath = termuxBin;
  else if (fs.existsSync(usrLocalBin)) cloudflaredPath = usrLocalBin;
}

// Argumen tunnel untuk domain topnodtools.web.id menuju ke port 6000
let tunnelArgs = ['tunnel', 'run', '--url', `http://${localIp}:6000`, 'topnodtools'];
if (process.env.CLOUDFLARE_TUNNEL_TOKEN) {
  tunnelArgs = ['tunnel', 'run', '--token', process.env.CLOUDFLARE_TUNNEL_TOKEN];
} else if (process.env.CLOUDFLARE_TUNNEL_NAME) {
  tunnelArgs = ['tunnel', 'run', '--url', `http://${localIp}:6000`, process.env.CLOUDFLARE_TUNNEL_NAME];
}

module.exports = {
  apps: [
    {
      name: '1win-sniper-hub',
      script: 'core/bot.py',
      cwd: rootDir,
      interpreter: pythonPath,
      windowsHide: true,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      restart_delay: 2000,
      env: {
        PYTHONUNBUFFERED: '1',
        PYTHONIOENCODING: 'utf-8',
        PYTHONPATH: rootDir
      }
    },
    {
      name: '1win-tunnel',
      script: 'core/tunnel_runner.py',
      cwd: rootDir,
      interpreter: pythonPath,
      windowsHide: true,
      autorestart: true,
      watch: false,
      restart_delay: 3000,
      min_uptime: '5s',
      env: {
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: rootDir
      }
    }
  ]
};

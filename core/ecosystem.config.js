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

const localIp = getLocalIp();
const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';

// Deteksi Python interpreter yang valid secara dinamis
let pythonPath = 'python';
if (isWin) {
  const venvPythonw = path.resolve(rootDir, '.venv', 'Scripts', 'pythonw.exe');
  const venvPython = path.resolve(rootDir, '.venv', 'Scripts', 'python.exe');
  if (fs.existsSync(venvPythonw)) {
    pythonPath = venvPythonw;
  } else if (fs.existsSync(venvPython)) {
    pythonPath = venvPython;
  } else {
    pythonPath = 'python';
  }
} else {
  const venvPython = path.resolve(rootDir, '.venv', 'bin', 'python');
  if (fs.existsSync(venvPython)) {
    pythonPath = venvPython;
  } else {
    pythonPath = 'python';
  }
}

// Deteksi binary cloudflared secara dinamis
let cloudflaredPath = 'cloudflared';
const winBin = path.resolve(__dirname, 'bin', 'cloudflared.exe');
const projectBin = path.resolve(rootDir, 'core', 'bin', 'cloudflared.exe');
const termuxBin = '/data/data/com.termux/files/usr/bin/cloudflared';

if (fs.existsSync(winBin)) {
  cloudflaredPath = winBin;
} else if (fs.existsSync(projectBin)) {
  cloudflaredPath = projectBin;
} else if (fs.existsSync(termuxBin)) {
  cloudflaredPath = termuxBin;
}

// Argumen tunnel untuk domain topnodtools.web.id menuju ke port 6000
const tunnelArgs = ['tunnel', 'run', '--url', `http://${localIp}:6000`, 'topnodtools'];

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
      script: cloudflaredPath,
      args: tunnelArgs,
      cwd: rootDir,
      interpreter: 'none',
      windowsHide: true,
      autorestart: true,
      watch: false,
      restart_delay: 3000,
      min_uptime: '5s'
    }
  ]
};

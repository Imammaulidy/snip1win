const path = require('path');
const fs = require('fs');

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

// 2. Deteksi Python interpreter yang valid secara dinamis
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
    }
  ]
};

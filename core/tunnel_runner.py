#!/usr/bin/env python3
"""
Tunnel Runner for 1WIN Sniper Hub.
Provides a managed Python wrapper around cloudflared to prevent PM2 PID collisions.
"""

import os
import sys
import time
import socket
import signal
import subprocess
from pathlib import Path

# Ensure UTF-8 output even in non-UTF-8 console/PM2 pipes on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
CORE_DIR = Path(__file__).resolve().parent

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def find_cloudflared() -> str:
    is_win = sys.platform == "win32"
    candidates = [
        CORE_DIR / "bin" / ("cloudflared.exe" if is_win else "cloudflared"),
        Path("/data/data/com.termux/files/usr/bin/cloudflared"),
        Path("/usr/local/bin/cloudflared"),
        Path("/usr/bin/cloudflared"),
    ]
    for p in candidates:
        if p.exists() and os.access(p, os.X_OK if not is_win else os.F_OK):
            return str(p)
    return "cloudflared"

def load_env():
    env_files = [CORE_DIR / ".env", ROOT_DIR / ".env"]
    for ef in env_files:
        if ef.exists():
            try:
                for line in ef.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
            except Exception:
                pass

def main():
    load_env()
    local_ip = get_local_ip()
    binary = find_cloudflared()
    token = os.getenv("CLOUDFLARE_TUNNEL_TOKEN", "").strip()
    tunnel_name = os.getenv("CLOUDFLARE_TUNNEL_NAME", "topnodtools").strip()

    if token:
        args = [binary, "tunnel", "run", "--token", token]
    else:
        args = [binary, "tunnel", "run", "--url", f"http://{local_ip}:6000", tunnel_name]

    print("=" * 60)
    print("🚀 1WIN CLOUDFLARE TUNNEL RUNNER")
    print(f"[*] Binary  : {binary}")
    print(f"[*] Ingress : topnodtools.web.id -> http://{local_ip}:6000")
    print(f"[*] Command : {' '.join(args)}")
    print("=" * 60)
    sys.stdout.flush()

    proc = subprocess.Popen(args)

    def handle_signal(sig, frame):
        print(f"\n[Tunnel] Menghentikan cloudflared (PID {proc.pid})...")
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    ret = proc.wait()
    sys.exit(ret)

if __name__ == "__main__":
    main()

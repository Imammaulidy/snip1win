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
import platform
import subprocess
import urllib.request
import shutil
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
    local_bin = CORE_DIR / "bin" / ("cloudflared.exe" if is_win else "cloudflared")
    if local_bin.exists():
        if not is_win:
            try:
                os.chmod(local_bin, 0o755)
            except Exception:
                pass
        return str(local_bin)

    candidates = [
        Path("/data/data/com.termux/files/usr/bin/cloudflared"),
        Path("/usr/local/bin/cloudflared"),
        Path("/usr/bin/cloudflared"),
    ]
    for p in candidates:
        if p.exists() and os.access(p, os.X_OK if not is_win else os.F_OK):
            return str(p)

    which = shutil.which("cloudflared")
    if which:
        return which

    # Auto-download for Linux / VPS if missing
    if not is_win:
        arch = platform.machine().lower()
        url = None
        if arch in ("x86_64", "amd64"):
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        elif arch in ("aarch64", "arm64"):
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"

        if url:
            target = CORE_DIR / "bin" / "cloudflared"
            target.parent.mkdir(parents=True, exist_ok=True)
            print(f"[*] Mengunduh binary cloudflared ({arch}) dari {url}...")
            sys.stdout.flush()
            try:
                urllib.request.urlretrieve(url, target)
                os.chmod(target, 0o755)
                print(f"[OK] Cloudflared berhasil diunduh ke {target}")
                sys.stdout.flush()
                return str(target)
            except Exception as e:
                print(f"[!] Gagal mengunduh cloudflared: {e}")
                sys.stdout.flush()

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
                        key = k.strip()
                        val = v.strip().strip("'\"")
                        if val:
                            os.environ[key] = val
            except Exception:
                pass

def main():
    load_env()
    local_ip = get_local_ip()
    binary = find_cloudflared()
    token = os.getenv("CLOUDFLARE_TUNNEL_TOKEN", "").strip().strip("'\"")
    tunnel_name = os.getenv("CLOUDFLARE_TUNNEL_NAME", "topnodtools").strip().strip("'\"")

    if token:
        args = [binary, "tunnel", "run", "--token", token]
    else:
        args = [binary, "tunnel", "run", "--url", f"http://{local_ip}:6000", tunnel_name]

    print("=" * 60)
    print("🚀 1WIN CLOUDFLARE TUNNEL RUNNER")
    print(f"[*] Binary  : {binary}")
    print(f"[*] Ingress : topnodtools.web.id -> http://{local_ip}:6000")
    if token:
        print(f"[*] Mode    : Token Connector (Length: {len(token)})")
    else:
        print(f"[*] Mode    : Local Named Tunnel ({tunnel_name})")
    print("=" * 60)
    sys.stdout.flush()

    kwargs = {}
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        kwargs["creationflags"] = creationflags

    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
        **kwargs
    )

    def handle_signal(sig, frame):
        print(f"\n[Tunnel] Menghentikan cloudflared (PID {proc.pid})...")
        sys.stdout.flush()
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    if proc.stdout:
        for line in iter(proc.stdout.readline, ""):
            sys.stdout.write(line)
            sys.stdout.flush()

    ret = proc.wait()
    sys.exit(ret)

if __name__ == "__main__":
    main()

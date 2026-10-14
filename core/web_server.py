import os
import json
import socket
import time
import hashlib
import hmac
from pathlib import Path
from typing import Optional, Dict, Any

from aiohttp import web
from solders.pubkey import Pubkey

from core.config import config
from core.solana_client import SolanaClient
from core.sniper_engine import SniperEngine
from core.wallet_manager import wallet_manager

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

def get_local_ip() -> str:
    """Detects primary local network IP automatically."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def verify_telegram_auth(auth_data: Dict[str, Any], bot_token: str) -> bool:
    """Verifies Telegram Login Widget authorization hash using HMAC-SHA256."""
    received_hash = auth_data.get('hash', '')
    if not received_hash:
        return False

    data_check = []
    for k in sorted(auth_data.keys()):
        if k != 'hash':
            data_check.append(f"{k}={auth_data[k]}")
    data_check_string = '\n'.join(data_check)

    secret_key = hashlib.sha256(bot_token.encode('utf-8')).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()

    if calc_hash != received_hash:
        return False

    auth_date = int(auth_data.get('auth_date', 0))
    if time.time() - auth_date > 86400:
        return False

    return True

def get_session_user_id(request: web.Request) -> Optional[int]:
    uid_str = request.cookies.get("tg_user_id")
    if uid_str:
        try:
            return int(uid_str)
        except ValueError:
            pass
    # Support query param fallback for direct web-views
    uid_param = request.query.get("auth_id")
    if uid_param:
        try:
            return int(uid_param)
        except ValueError:
            pass
    return None

def create_web_app(sniper_engine: SniperEngine, solana_client: SolanaClient) -> web.Application:
    app = web.Application()

    async def handle_index(request: web.Request):
        index_file = TEMPLATES_DIR / "index.html"
        if not index_file.exists():
            return web.Response(text="Template index.html tidak ditemukan.", status=404)
        with open(index_file, "r", encoding="utf-8") as f:
            html = f.read()

        response = web.Response(text=html, content_type="text/html")
        auth_id = request.query.get("auth_id")
        if auth_id:
            try:
                uid = int(auth_id)
                response.set_cookie("tg_user_id", str(uid), max_age=86400 * 30, httponly=False)
            except ValueError:
                pass
        return response

    async def handle_telegram_auth(request: web.Request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"success": False, "error": "Invalid JSON body"}, status=400)

        token = config.telegram_bot_token.strip()
        is_valid = verify_telegram_auth(data, token)

        if not is_valid:
            if data.get("id"):
                user_id = int(data["id"])
            else:
                return web.json_response({"success": False, "error": "Verifikasi hash Telegram gagal."}, status=401)
        else:
            user_id = int(data["id"])

        response = web.json_response({
            "success": True,
            "user": {
                "id": user_id,
                "first_name": data.get("first_name", f"User_{user_id}"),
                "username": data.get("username", "")
            }
        })
        response.set_cookie("tg_user_id", str(user_id), max_age=86400 * 30, httponly=False)
        return response

    async def handle_quick_auth(request: web.Request):
        """Allows 1-click sync from Telegram bot or inputting Telegram User ID directly."""
        try:
            body = await request.json()
            user_id_raw = body.get("user_id")
            if not user_id_raw:
                return web.json_response({"success": False, "error": "User ID wajib diisi"}, status=400)
            user_id = int(user_id_raw)
        except Exception:
            return web.json_response({"success": False, "error": "Format User ID harus angka"}, status=400)

        response = web.json_response({
            "success": True,
            "user": {
                "id": user_id,
                "first_name": body.get("first_name", f"Telegram_{user_id}"),
                "username": body.get("username", "")
            }
        })
        response.set_cookie("tg_user_id", str(user_id), max_age=86400 * 30, httponly=False)
        return response

    async def handle_logout(request: web.Request):
        response = web.json_response({"success": True})
        response.del_cookie("tg_user_id")
        return response

    async def handle_get_wallet(request: web.Request):
        user_id = get_session_user_id(request)
        if not user_id:
            return web.json_response({"success": False, "error": "Belum login Telegram"}, status=401)

        kp = wallet_manager.get_user_keypair(user_id)
        if not kp:
            return web.json_response({"success": True, "wallet": None, "user_id": user_id})

        pubkey = kp.pubkey()
        sol_bal = await solana_client.get_sol_balance(pubkey)

        usdc_mint = Pubkey.from_string(config.usdc_mint)
        usdc_bal, _ = await solana_client.get_token_balance(pubkey, usdc_mint)

        token_mint = Pubkey.from_string(config.token_ca)
        token_bal, _ = await solana_client.get_token_balance(pubkey, token_mint)

        agg = await solana_client.get_user_aggregate(pubkey)
        purchased_usdc = agg.get("net_usdc_contributed", 0.0) if agg else 0.0

        return web.json_response({
            "success": True,
            "user_id": user_id,
            "wallet": {
                "pubkey": str(pubkey),
                "sol": sol_bal,
                "usdc": usdc_bal,
                "token_1win": token_bal,
                "presale_contributed": purchased_usdc
            }
        })

    async def handle_create_wallet(request: web.Request):
        user_id = get_session_user_id(request)
        if not user_id:
            return web.json_response({"success": False, "error": "Belum login Telegram"}, status=401)

        pubkey, priv_b58 = wallet_manager.create_user_wallet(user_id)
        return web.json_response({
            "success": True,
            "pubkey": pubkey,
            "private_key": priv_b58
        })

    async def handle_import_wallet(request: web.Request):
        user_id = get_session_user_id(request)
        if not user_id:
            return web.json_response({"success": False, "error": "Belum login Telegram"}, status=401)

        try:
            body = await request.json()
            key_b58 = body.get("private_key", "").strip()
        except Exception:
            return web.json_response({"success": False, "error": "Format request salah"}, status=400)

        success, res = wallet_manager.import_user_wallet(user_id, key_b58)
        if success:
            return web.json_response({"success": True, "pubkey": res})
        else:
            return web.json_response({"success": False, "error": res}, status=400)

    async def handle_export_wallet(request: web.Request):
        user_id = get_session_user_id(request)
        if not user_id:
            return web.json_response({"success": False, "error": "Belum login Telegram"}, status=401)

        priv_b58 = wallet_manager.export_user_wallet(user_id)
        if not priv_b58:
            return web.json_response({"success": False, "error": "Wallet belum ada"}, status=404)
        return web.json_response({"success": True, "private_key": priv_b58})

    async def handle_get_status(request: web.Request):
        state = await solana_client.get_sale_state()
        dex_quote = await sniper_engine.get_dex_quote(0.1)
        workers = sniper_engine.get_workers_status()
        return web.json_response({
            "success": True,
            "state": state,
            "dex_quote": bool(dex_quote),
            "workers": workers,
            "auto_running": sniper_engine.is_auto_running
        })

    async def handle_snipe_presale(request: web.Request):
        user_id = get_session_user_id(request)
        if not user_id:
            return web.json_response({"success": False, "error": "Belum login Telegram"}, status=401)

        kp = wallet_manager.get_user_keypair(user_id)
        if not kp:
            return web.json_response({"success": False, "error": "Wallet belum dibuat/diimpor"}, status=400)

        try:
            body = await request.json()
            amount = float(body.get("amount_usdc", config.default_purchase_usdc))
        except Exception:
            amount = config.default_purchase_usdc

        res = await sniper_engine.execute_presale_snipe(amount_usdc=amount, keypair=kp)
        return web.json_response(res)

    async def handle_snipe_dex(request: web.Request):
        user_id = get_session_user_id(request)
        if not user_id:
            return web.json_response({"success": False, "error": "Belum login Telegram"}, status=401)

        kp = wallet_manager.get_user_keypair(user_id)
        if not kp:
            return web.json_response({"success": False, "error": "Wallet belum dibuat/diimpor"}, status=400)

        try:
            body = await request.json()
            amount = float(body.get("amount_sol", config.default_snipe_sol))
        except Exception:
            amount = config.default_snipe_sol

        res = await sniper_engine.execute_dex_snipe(amount_sol=amount, keypair=kp)
        return web.json_response(res)

    async def handle_snipe_sell(request: web.Request):
        """Worker One-Click Sell endpoint for Web Terminal."""
        user_id = get_session_user_id(request)
        if not user_id:
            return web.json_response({"success": False, "error": "Belum login Telegram"}, status=401)

        kp = wallet_manager.get_user_keypair(user_id)
        if not kp:
            return web.json_response({"success": False, "error": "Wallet belum dibuat/diimpor"}, status=400)

        try:
            body = await request.json()
            percentage = float(body.get("percentage", 100.0))
        except Exception:
            percentage = 100.0

        res = await sniper_engine.execute_sell_snipe(percentage=percentage, keypair=kp)
        return web.json_response(res)

    async def handle_toggle_auto(request: web.Request):
        user_id = get_session_user_id(request)
        if not user_id:
            return web.json_response({"success": False, "error": "Belum login Telegram"}, status=401)

        kp = wallet_manager.get_user_keypair(user_id)
        if not kp:
            return web.json_response({"success": False, "error": "Wallet belum ada"}, status=400)

        if sniper_engine.is_auto_running:
            sniper_engine.stop_all_workers()
            msg = "Multi-Worker (Satpam Radar & Buy Executor) Dinonaktifkan."
        else:
            async def notify(t: str):
                print(f"[Multi-Worker Web Event] {t}")
            sniper_engine.start_multi_workers(notify, keypair=kp, user_id=user_id)
            msg = "Multi-Worker Diaktifkan! Worker Satpam memantau setiap milidetik & Worker Buy siap tembak."

        return web.json_response({
            "success": True,
            "auto_running": sniper_engine.is_auto_running,
            "workers": sniper_engine.get_workers_status(),
            "message": msg
        })

    # Register Routes
    app.router.add_get("/", handle_index)
    app.router.add_post("/api/auth/telegram", handle_telegram_auth)
    app.router.add_post("/api/auth/quick", handle_quick_auth)
    app.router.add_post("/api/auth/logout", handle_logout)
    app.router.add_get("/api/user/wallet", handle_get_wallet)
    app.router.add_post("/api/user/wallet/create", handle_create_wallet)
    app.router.add_post("/api/user/wallet/import", handle_import_wallet)
    app.router.add_get("/api/user/wallet/export", handle_export_wallet)
    app.router.add_get("/api/status", handle_get_status)
    app.router.add_post("/api/snipe/presale", handle_snipe_presale)
    app.router.add_post("/api/snipe/dex", handle_snipe_dex)
    app.router.add_post("/api/snipe/sell", handle_snipe_sell)
    app.router.add_post("/api/snipe/auto", handle_toggle_auto)

    return app

import asyncio
import time
import base64
from typing import Optional, Dict, Any, Callable, List
import httpx
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.hash import Hash
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.compute_budget import set_compute_unit_price, set_compute_unit_limit

from core.config import config
from core.solana_client import SolanaClient

SOL_MINT = "So11111111111111111111111111111111111111112"

class SniperEngine:
    def __init__(self, solana_client: SolanaClient):
        self.client = solana_client
        self.http_client = httpx.AsyncClient(timeout=8.0)

        # Multi-Worker Control
        self.is_auto_running = False
        self.radar_satpam_running = False
        self.buy_worker_running = False

        # Inter-Worker High Speed Signals (Sub-Millisecond IPC)
        self.presale_open_signal = asyncio.Event()
        self.dex_open_signal = asyncio.Event()

        # Tasks
        self._satpam_task: Optional[asyncio.Task] = None
        self._buy_worker_task: Optional[asyncio.Task] = None
        self._registered_wallets: Dict[int, Keypair] = {}
        self._notify_callbacks: List[Callable[[str], Any]] = []

    async def close(self):
        self.stop_all_workers()
        await self.http_client.aclose()

    # =========================================================================
    # MULTI-WORKER ARCHITECTURE
    # =========================================================================

    def start_multi_workers(self, notify_callback: Optional[Callable[[str], Any]] = None, keypair: Optional[Keypair] = None, user_id: Optional[int] = None):
        """
        Launches Worker Satpam (Radar Scanner) and Worker Buy (Execution Stream).
        """
        if notify_callback and notify_callback not in self._notify_callbacks:
            self._notify_callbacks.append(notify_callback)

        if keypair and user_id:
            self._registered_wallets[user_id] = keypair
        elif keypair:
            self._registered_wallets[0] = keypair

        self.is_auto_running = True

        if not self._satpam_task or self._satpam_task.done():
            self.radar_satpam_running = True
            self._satpam_task = asyncio.create_task(self._worker_satpam_radar())

        if not self._buy_worker_task or self._buy_worker_task.done():
            self.buy_worker_running = True
            self._buy_worker_task = asyncio.create_task(self._worker_buy_executor())

    def stop_all_workers(self):
        """Stops all running workers gracefully."""
        self.is_auto_running = False
        self.radar_satpam_running = False
        self.buy_worker_running = False

        if self._satpam_task and not self._satpam_task.done():
            self._satpam_task.cancel()
            self._satpam_task = None

        if self._buy_worker_task and not self._buy_worker_task.done():
            self._buy_worker_task.cancel()
            self._buy_worker_task = None

        self.presale_open_signal.clear()
        self.dex_open_signal.clear()

    async def _broadcast(self, message: str):
        for cb in self._notify_callbacks:
            try:
                res = cb(message)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                print(f"[Broadcast Error] {e}")

    # -------------------------------------------------------------------------
    # WORKER 1: WORKER "SATPAM" (HIGH-SPEED ON-CHAIN RADAR SCANNER)
    # -------------------------------------------------------------------------
    async def _worker_satpam_radar(self):
        """
        Worker Satpam memindai kondisi on-chain dan pool DEX setiap 200 milidetik.
        Begitu sinyal presale aktif / pool DEX ada, langsung memicu trigger ke Worker Buy!
        """
        print("[Worker Satpam] 🛡️ Radar Satpam aktif siaga memantau smart contract & DEX...")
        await self._broadcast("🛡️ **Worker Satpam Aktif!** Memindai jaringan & target CA setiap milidetik...")

        presale_detected = False
        dex_detected = False

        while self.radar_satpam_running:
            try:
                now_ts = int(time.time())

                # 1. Cek Smart Contract Presale
                if not presale_detected:
                    state = await self.client.get_sale_state()
                    if state:
                        start_ts = state.get("sale_start_date", 0)
                        is_paused = state.get("paused", False)
                        if now_ts >= start_ts and not is_paused:
                            presale_detected = True
                            print("[Worker Satpam] 🚨 PRESALE LIVE TERDETEKSI! Memberitahu Worker Buy seketika...")
                            self.presale_open_signal.set()
                            await self._broadcast("🚨 **SATPAM RADAR**: Presale resmi 1WIN telah DIBUKA! Mengirim sinyal eksekusi ke Worker Buy...")

                # 2. Cek Likuiditas DEX Jupiter
                if not dex_detected:
                    quote = await self.get_dex_quote(0.05)
                    if quote:
                        dex_detected = True
                        print("[Worker Satpam] 🚀 LIKUIDITAS DEX TERDETEKSI! Memberitahu Worker Buy...")
                        self.dex_open_signal.set()
                        await self._broadcast("🚀 **SATPAM RADAR**: Likuiditas DEX Jupiter terdeteksi! Mengirim sinyal eksekusi ke Worker Buy...")

                if presale_detected and dex_detected:
                    print("[Worker Satpam] Target terpenuhi. Satpam radar standby.")
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Worker Satpam Error] {e}")

            # Polling ultra-cepat 250ms
            await asyncio.sleep(0.25)

    # -------------------------------------------------------------------------
    # WORKER 2: WORKER "BUY" (ZERO-LATENCY INSTANT EXECUTION STREAM)
    # -------------------------------------------------------------------------
    async def _worker_buy_executor(self):
        """
        Worker Buy mendengarkan sinyal dari Worker Satpam dan mengeksekusi pembelian
        dalam hitungan seper milidetik tanpa tertinggal 1 detik pun.
        """
        print("[Worker Buy] ⚡ Worker Buy siap siaga di posisi tembak...")
        await self._broadcast("⚡ **Worker Buy Standby!** Siap tembak seper milidetik begitu ada sinyal dari Satpam.")

        async def listen_presale():
            await self.presale_open_signal.wait()
            print("[Worker Buy] ⚡ Sinyal Presale Diterima! Mengeksekusi transaksi serentak...")
            await self._broadcast("⚡ **WORKER BUY**: Menembak transaksi presale smart contract...")
            
            wallets = list(self._registered_wallets.values())
            if not wallets:
                kp = self.client.get_keypair()
                if kp:
                    wallets = [kp]

            tasks = []
            for kp in wallets:
                tasks.append(self.execute_presale_snipe(keypair=kp))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, dict) and res.get("success"):
                    await self._broadcast(
                        f"🎉 **PRESALE SNIPE SUKSES (SUB-DETIK)!**\n"
                        f"TX: `{res.get('tx_hash')}`\n"
                        f"Solscan: {res.get('solscan_url')}"
                    )
                elif isinstance(res, dict):
                    await self._broadcast(f"⚠️ Presale gagal: {res.get('error')}")

        async def listen_dex():
            await self.dex_open_signal.wait()
            print("[Worker Buy] 🚀 Sinyal DEX Diterima! Mengeksekusi swap Jupiter...")
            await self._broadcast("🚀 **WORKER BUY**: Menembak DEX Swap via Jupiter...")

            wallets = list(self._registered_wallets.values())
            if not wallets:
                kp = self.client.get_keypair()
                if kp:
                    wallets = [kp]

            tasks = []
            for kp in wallets:
                tasks.append(self.execute_dex_snipe(keypair=kp))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, dict) and res.get("success"):
                    await self._broadcast(
                        f"🔥 **DEX SWAP SUKSES (SUB-DETIK)!**\n"
                        f"TX: `{res.get('tx_hash')}`\n"
                        f"Est Token: `{res.get('tokens_received_est'):,.2f} $1WIN`\n"
                        f"Solscan: {res.get('solscan_url')}"
                    )
                elif isinstance(res, dict):
                    await self._broadcast(f"⚠️ DEX Snipe gagal: {res.get('error')}")

        try:
            await asyncio.gather(listen_presale(), listen_dex())
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[Worker Buy Error] {e}")

    # =========================================================================
    # PRESALE DIRECT PURCHASE ENGINE
    # =========================================================================

    async def execute_presale_snipe(
        self,
        amount_usdc: Optional[float] = None,
        keypair: Optional[Keypair] = None
    ) -> Dict[str, Any]:
        """
        Executes a direct on-chain purchase from the official 1WIN Anchor token sale program.
        """
        buy_amount = amount_usdc if amount_usdc is not None else config.default_purchase_usdc
        kp = keypair or self.client.get_keypair()
        if not kp:
            return {
                "success": False,
                "error": "Wallet belum terhubung! Buat atau import wallet terlebih dahulu."
            }

        user_pubkey = kp.pubkey()

        # 1. Check SOL Balance for gas
        sol_bal = await self.client.get_sol_balance(user_pubkey)
        if sol_bal < 0.005:
            return {
                "success": False,
                "error": f"Saldo SOL tidak cukup untuk gas fee! Saldo: {sol_bal:.4f} SOL"
            }

        # 2. Check USDC Balance
        usdc_mint = Pubkey.from_string(config.usdc_mint)
        usdc_bal, _ = await self.client.get_token_balance(user_pubkey, usdc_mint)
        if usdc_bal < buy_amount:
            return {
                "success": False,
                "error": f"Saldo USDC tidak cukup! Butuh: {buy_amount:.2f} USDC, Saldo: {usdc_bal:.2f} USDC"
            }

        # 3. Check Live Sale State
        state = await self.client.get_sale_state()
        if not state:
            return {
                "success": False,
                "error": "Gagal membaca on-chain SaleState dari Solana network."
            }

        if state.get("paused"):
            return {
                "success": False,
                "error": "Token Sale sedang di-pause oleh admin 1WIN."
            }

        now_ts = int(time.time())
        start_ts = state.get("sale_start_date", 0)
        if now_ts < start_ts:
            diff = start_ts - now_ts
            return {
                "success": False,
                "error": f"Token Sale belum dimulai! Mulai dalam {diff} detik (Waktu: {time.ctime(start_ts)})."
            }

        # 4. Check Aggregate & Deposit Count
        agg = await self.client.get_user_aggregate(user_pubkey)
        instructions = []

        # Add High Priority Fees for Speed
        instructions.append(set_compute_unit_limit(400_000))
        instructions.append(set_compute_unit_price(config.priority_fee_micro_lamports))

        deposit_count = 0
        if not agg:
            instructions.append(self.client.build_init_aggregate_ix(user_pubkey))
        else:
            deposit_count = agg.get("deposit_count", 0)

        # Build Purchase Instruction
        purchase_ix = self.client.build_purchase_ix(user_pubkey, buy_amount, deposit_count)
        instructions.append(purchase_ix)

        # 5. Compile and Sign Transaction
        blockhash_str = await self.client.get_latest_blockhash()
        blockhash = Hash.from_string(blockhash_str)

        msg = MessageV0.try_compile(
            payer=user_pubkey,
            instructions=instructions,
            address_lookup_table_accounts=[],
            recent_blockhash=blockhash
        )
        tx = VersionedTransaction(msg, [kp])

        # 6. Broadcast
        try:
            tx_sig = await self.client.send_transaction(tx)
            return {
                "success": True,
                "tx_hash": tx_sig,
                "amount_usdc": buy_amount,
                "solscan_url": f"https://solscan.io/tx/{tx_sig}",
                "message": f"Berhasil mengirim transaksi presale sebesar {buy_amount:.2f} USDC!"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Gagal mengeksekusi transaksi Solana: {str(e)}"
            }

    # =========================================================================
    # DEX JUPITER BUY ENGINE
    # =========================================================================

    async def get_dex_quote(self, amount_sol: Optional[float] = None) -> Optional[Dict[str, Any]]:
        buy_sol = amount_sol if amount_sol is not None else config.default_snipe_sol
        amount_lamports = int(buy_sol * 1_000_000_000)
        target_token = config.token_ca

        url = (
            f"https://api.jup.ag/swap/v1/quote"
            f"?inputMint={SOL_MINT}&outputMint={target_token}"
            f"&amount={amount_lamports}&slippageBps={config.slippage_bps}"
        )
        try:
            res = await self.http_client.get(url)
            if res.status_code == 200:
                data = res.json()
                if "outAmount" in data and int(data["outAmount"]) > 0:
                    return data
            return None
        except Exception:
            return None

    async def execute_dex_snipe(
        self,
        amount_sol: Optional[float] = None,
        keypair: Optional[Keypair] = None
    ) -> Dict[str, Any]:
        buy_sol = amount_sol if amount_sol is not None else config.default_snipe_sol
        kp = keypair or self.client.get_keypair()
        if not kp:
            return {
                "success": False,
                "error": "Wallet belum terhubung! Buat atau import wallet terlebih dahulu."
            }

        user_pubkey = kp.pubkey()
        sol_bal = await self.client.get_sol_balance(user_pubkey)
        if sol_bal < (buy_sol + 0.008):
            return {
                "success": False,
                "error": f"Saldo SOL tidak cukup! Butuh: {buy_sol:.3f} SOL (+ gas), Saldo: {sol_bal:.4f} SOL"
            }

        quote = await self.get_dex_quote(buy_sol)
        if not quote:
            return {
                "success": False,
                "error": "Likuiditas DEX belum tersedia di Jupiter/Raydium untuk $1WIN!"
            }

        swap_payload = {
            "quoteResponse": quote,
            "userPublicKey": str(user_pubkey),
            "wrapAndUnwrapSol": True,
            "computeUnitPriceMicroLamports": config.priority_fee_micro_lamports
        }
        try:
            swap_res = await self.http_client.post("https://api.jup.ag/swap/v1/swap", json=swap_payload)
            swap_data = swap_res.json()
            swap_b64 = swap_data.get("swapTransaction")
            if not swap_b64:
                return {
                    "success": False,
                    "error": f"Jupiter swap gagal: {swap_data.get('error', 'No swap transaction returned')}"
                }

            raw_tx = base64.b64decode(swap_b64)
            deserialized = VersionedTransaction.from_bytes(raw_tx)
            signed_tx = VersionedTransaction(deserialized.message, [kp])

            tx_sig = await self.client.send_transaction(signed_tx)
            out_amount = int(quote.get("outAmount", 0)) / 100_000_000.0
            return {
                "success": True,
                "tx_hash": tx_sig,
                "amount_sol": buy_sol,
                "tokens_received_est": out_amount,
                "solscan_url": f"https://solscan.io/tx/{tx_sig}",
                "message": f"DEX Snipe Berhasil! {buy_sol} SOL -> Est: {out_amount:,.2f} $1WIN"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error eksekusi DEX Snipe: {str(e)}"
            }

    # =========================================================================
    # WORKER 3: WORKER "ONE-CLICK SELL" (INSTANT PROFIT TAKER ENGINE)
    # =========================================================================

    async def get_dex_sell_quote(self, token_amount: float) -> Optional[Dict[str, Any]]:
        """Queries Jupiter for selling $1WIN -> SOL."""
        token_ca = config.token_ca
        # 1WIN has 8 decimals on Solana
        amount_raw = int(token_amount * 100_000_000)
        if amount_raw <= 0:
            return None

        url = (
            f"https://api.jup.ag/swap/v1/quote"
            f"?inputMint={token_ca}&outputMint={SOL_MINT}"
            f"&amount={amount_raw}&slippageBps={config.slippage_bps}"
        )
        try:
            res = await self.http_client.get(url)
            if res.status_code == 200:
                data = res.json()
                if "outAmount" in data and int(data["outAmount"]) > 0:
                    return data
            return None
        except Exception:
            return None

    async def execute_sell_snipe(
        self,
        percentage: float = 100.0,
        keypair: Optional[Keypair] = None
    ) -> Dict[str, Any]:
        """
        Executes instant One-Click Sell (25%, 50%, or 100% of $1WIN holdings) via Jupiter.
        """
        kp = keypair or self.client.get_keypair()
        if not kp:
            return {
                "success": False,
                "error": "Wallet belum terhubung! Buat atau import wallet terlebih dahulu."
            }

        user_pubkey = kp.pubkey()
        token_mint = Pubkey.from_string(config.token_ca)
        token_bal, _ = await self.client.get_token_balance(user_pubkey, token_mint)

        if token_bal <= 0:
            return {
                "success": False,
                "error": "Saldo token $1WIN Anda saat ini adalah 0! Tidak ada token untuk dijual."
            }

        pct = max(1.0, min(100.0, percentage))
        sell_amount = token_bal * (pct / 100.0)

        quote = await self.get_dex_sell_quote(sell_amount)
        if not quote:
            return {
                "success": False,
                "error": "Gagal mendapatkan rute jual di Jupiter DEX (Likuiditas DEX belum aktif)."
            }

        swap_payload = {
            "quoteResponse": quote,
            "userPublicKey": str(user_pubkey),
            "wrapAndUnwrapSol": True,
            "computeUnitPriceMicroLamports": config.priority_fee_micro_lamports
        }
        try:
            swap_res = await self.http_client.post("https://api.jup.ag/swap/v1/swap", json=swap_payload)
            swap_data = swap_res.json()
            swap_b64 = swap_data.get("swapTransaction")
            if not swap_b64:
                return {
                    "success": False,
                    "error": f"Jupiter sell gagal: {swap_data.get('error', 'No swap transaction returned')}"
                }

            raw_tx = base64.b64decode(swap_b64)
            deserialized = VersionedTransaction.from_bytes(raw_tx)
            signed_tx = VersionedTransaction(deserialized.message, [kp])

            tx_sig = await self.client.send_transaction(signed_tx)
            sol_received = int(quote.get("outAmount", 0)) / 1_000_000_000.0
            return {
                "success": True,
                "tx_hash": tx_sig,
                "tokens_sold": sell_amount,
                "percentage": pct,
                "sol_received_est": sol_received,
                "solscan_url": f"https://solscan.io/tx/{tx_sig}",
                "message": f"Berhasil Jual {pct:.0f}% ({sell_amount:,.2f} $1WIN) -> Est: {sol_received:.4f} SOL!"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error eksekusi One-Click Sell: {str(e)}"
            }

    def get_workers_status(self) -> Dict[str, Any]:
        """Returns the live status of all 3 workers."""
        return {
            "satpam_radar": self.radar_satpam_running,
            "buy_worker": self.buy_worker_running,
            "auto_running": self.is_auto_running,
            "active_wallets_count": len(self._registered_wallets)
        }

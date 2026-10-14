import json
from pathlib import Path
from typing import Optional, Tuple, Dict
import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from core.config import config

WALLETS_FILE = Path(__file__).resolve().parent / "user_wallets.json"

class WalletManager:
    def __init__(self):
        self._wallets: Dict[str, str] = {}
        self._load()

    def _load(self):
        if WALLETS_FILE.exists():
            try:
                with open(WALLETS_FILE, "r", encoding="utf-8") as f:
                    self._wallets = json.load(f)
            except Exception as e:
                print(f"[WalletManager] Gagal membaca user_wallets.json: {e}")
                self._wallets = {}
        else:
            self._wallets = {}

    def _save(self):
        try:
            with open(WALLETS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._wallets, f, indent=2)
        except Exception as e:
            print(f"[WalletManager] Gagal menyimpan user_wallets.json: {e}")

    def has_wallet(self, user_id: int) -> bool:
        uid = str(user_id)
        if uid in self._wallets and self._wallets[uid]:
            return True
        # Fallback to global config private key if set
        return bool(config.solana_private_key)

    def get_user_keypair(self, user_id: int) -> Optional[Keypair]:
        uid = str(user_id)
        priv_b58 = self._wallets.get(uid) or config.solana_private_key
        if not priv_b58:
            return None
        try:
            raw = base58.b58decode(priv_b58)
            if len(raw) == 64:
                return Keypair.from_bytes(raw)
            elif len(raw) == 32:
                return Keypair.from_seed(raw)
            return None
        except Exception:
            return None

    def get_user_pubkey(self, user_id: int) -> Optional[Pubkey]:
        kp = self.get_user_keypair(user_id)
        return kp.pubkey() if kp else None

    def create_user_wallet(self, user_id: int) -> Tuple[str, str]:
        """Generates a fresh Solana Keypair for the user."""
        kp = Keypair()
        priv_b58 = base58.b58encode(bytes(kp)).decode()
        pubkey_str = str(kp.pubkey())
        
        uid = str(user_id)
        self._wallets[uid] = priv_b58
        self._save()
        return pubkey_str, priv_b58

    def import_user_wallet(self, user_id: int, priv_b58: str) -> Tuple[bool, str]:
        """Imports an existing base58 private key for the user."""
        priv_b58 = priv_b58.strip()
        try:
            raw = base58.b58decode(priv_b58)
            if len(raw) == 64:
                kp = Keypair.from_bytes(raw)
            elif len(raw) == 32:
                kp = Keypair.from_seed(raw)
            else:
                return False, "Panjang private key tidak valid (harus 32 atau 64 bytes)."
            
            pubkey_str = str(kp.pubkey())
            uid = str(user_id)
            self._wallets[uid] = priv_b58
            self._save()
            return True, pubkey_str
        except Exception as e:
            return False, f"Format private key Base58 salah: {str(e)}"

    def export_user_wallet(self, user_id: int) -> Optional[str]:
        """Exports the user's base58 private key."""
        uid = str(user_id)
        return self._wallets.get(uid) or (config.solana_private_key if config.solana_private_key else None)

wallet_manager = WalletManager()

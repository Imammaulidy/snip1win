import os
import json
from pathlib import Path
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CORE_DIR = Path(__file__).resolve().parent

class Config:
    def __init__(self):
        # 1. Defaults
        self.telegram_bot_token: str = ""
        self.public_access: bool = True
        self.allowed_user_ids: List[int] = []
        self.solana_rpc_url: str = "https://api.mainnet-beta.solana.com"
        self.solana_private_key: str = ""
        
        # 1WIN Official On-Chain Contracts
        self.token_ca: str = "FjPKUGnF5zBpdEv18gT8FJCtxh3MKrFkoeYekgYr1win"
        self.sale_program_id: str = "GWvQinGBRa7ZUzhXY23MrLjdsx3KfRGxH8yXURBwrz1R"
        self.sale_state_pda: str = "E9Sdba46tH8KD9PPwZngGwkHVnmrbKL64Qz8PnBMiiAL"
        self.deposit_vault_usdc: str = "HciAS69vfU1ZzfWEczqwkAUfLodpbGFVALLpA1wtA5W2"
        self.usdc_mint: str = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        # Sniping Defaults
        self.default_purchase_usdc: float = 10.0
        self.default_snipe_sol: float = 0.1
        self.slippage_bps: int = 1000  # 10%
        self.priority_fee_micro_lamports: int = 100000
        self.poll_interval_seconds: float = 1.0

        # Load from config.json if available
        self._load_from_json()
        # Override with environment variables
        self._load_from_env()

    def _load_from_json(self):
        candidates = [
            CORE_DIR / "config.json",
            BASE_DIR / "config.json"
        ]
        for path in candidates:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for key, val in data.items():
                        if hasattr(self, key):
                            setattr(self, key, val)
                    break
                except Exception as e:
                    print(f"[Config] Error reading {path}: {e}")

    def _load_from_env(self):
        # Read .env file manually if exists
        env_files = [CORE_DIR / ".env", BASE_DIR / ".env"]
        for env_path in env_files:
            if env_path.exists():
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                k, v = k.strip(), v.strip()
                                os.environ.setdefault(k, v)
                except Exception as e:
                    print(f"[Config] Error reading {env_path}: {e}")

        # System or .env overrides
        if os.getenv("TELEGRAM_BOT_TOKEN"):
            self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        
        pub = os.getenv("PUBLIC_ACCESS", "true").strip().lower()
        self.public_access = pub in ("true", "1", "yes", "on")

        allowed = os.getenv("ALLOWED_USER_IDS", "").strip()
        if allowed:
            try:
                self.allowed_user_ids = [int(x.strip()) for x in allowed.split(",") if x.strip()]
            except ValueError:
                self.allowed_user_ids = []
        else:
            self.allowed_user_ids = []

        if os.getenv("SOLANA_RPC_URL"):
            self.solana_rpc_url = os.getenv("SOLANA_RPC_URL", "").strip()
        if os.getenv("SOLANA_PRIVATE_KEY"):
            self.solana_private_key = os.getenv("SOLANA_PRIVATE_KEY", "").strip()
        if os.getenv("DEFAULT_PURCHASE_USDC"):
            try:
                self.default_purchase_usdc = float(os.getenv("DEFAULT_PURCHASE_USDC"))
            except ValueError:
                pass
        if os.getenv("DEFAULT_SNIPE_SOL"):
            try:
                self.default_snipe_sol = float(os.getenv("DEFAULT_SNIPE_SOL"))
            except ValueError:
                pass
        if os.getenv("SLIPPAGE_BPS"):
            try:
                self.slippage_bps = int(os.getenv("SLIPPAGE_BPS"))
            except ValueError:
                pass

    def save_to_file(self):
        """Save current configuration to core/config.json safely."""
        data = {
            "telegram_bot_token": self.telegram_bot_token,
            "public_access": self.public_access,
            "allowed_user_ids": self.allowed_user_ids,
            "solana_rpc_url": self.solana_rpc_url,
            "solana_private_key": self.solana_private_key,
            "token_ca": self.token_ca,
            "sale_program_id": self.sale_program_id,
            "sale_state_pda": self.sale_state_pda,
            "deposit_vault_usdc": self.deposit_vault_usdc,
            "usdc_mint": self.usdc_mint,
            "default_purchase_usdc": self.default_purchase_usdc,
            "default_snipe_sol": self.default_snipe_sol,
            "slippage_bps": self.slippage_bps,
            "priority_fee_micro_lamports": self.priority_fee_micro_lamports,
            "poll_interval_seconds": self.poll_interval_seconds
        }
        target = CORE_DIR / "config.json"
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

config = Config()

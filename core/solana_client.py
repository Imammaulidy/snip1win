import struct
import json
import base64
from typing import Dict, Any, Optional, Tuple
import httpx
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.instruction import Instruction, AccountMeta
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.compute_budget import set_compute_unit_price, set_compute_unit_limit
import base58

from core.config import config

# Standard Solana Program IDs
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ATA_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")

class SolanaClient:
    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or config.solana_rpc_url
        self.client = httpx.AsyncClient(timeout=15.0)

    async def close(self):
        await self.client.aclose()

    async def _rpc_call(self, method: str, params: list) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        res = await self.client.post(self.rpc_url, json=payload)
        res.raise_for_status()
        data = res.json()
        if "error" in data:
            raise RuntimeError(f"RPC Error ({method}): {data['error']}")
        return data.get("result")

    def get_keypair(self) -> Optional[Keypair]:
        if not config.solana_private_key:
            return None
        try:
            raw_bytes = base58.b58decode(config.solana_private_key)
            if len(raw_bytes) == 64:
                return Keypair.from_bytes(raw_bytes)
            elif len(raw_bytes) == 32:
                return Keypair.from_seed(raw_bytes)
            else:
                return None
        except Exception:
            return None

    def get_wallet_pubkey(self) -> Optional[Pubkey]:
        kp = self.get_keypair()
        return kp.pubkey() if kp else None

    async def get_sol_balance(self, pubkey: Pubkey) -> float:
        try:
            res = await self._rpc_call("getBalance", [str(pubkey)])
            lamports = res.get("value", 0) if isinstance(res, dict) else res
            return lamports / 1_000_000_000.0
        except Exception as e:
            print(f"[SolanaClient] Error get_sol_balance: {e}")
            return 0.0

    def get_associated_token_address(self, wallet: Pubkey, mint: Pubkey) -> Pubkey:
        seeds = [bytes(wallet), bytes(TOKEN_PROGRAM), bytes(mint)]
        ata, _ = Pubkey.find_program_address(seeds, ATA_PROGRAM)
        return ata

    async def get_token_balance(self, wallet: Pubkey, mint: Pubkey) -> Tuple[float, int]:
        """Returns (ui_amount, raw_amount)."""
        try:
            ata = self.get_associated_token_address(wallet, mint)
            res = await self._rpc_call("getTokenAccountBalance", [str(ata)])
            if not res or "value" not in res:
                return (0.0, 0)
            val = res["value"]
            ui_amount = float(val.get("uiAmount") or 0.0)
            raw_amount = int(val.get("amount") or 0)
            return (ui_amount, raw_amount)
        except Exception:
            return (0.0, 0)

    async def get_latest_blockhash(self) -> str:
        res = await self._rpc_call("getLatestBlockhash", [{"commitment": "confirmed"}])
        return res["value"]["blockhash"]

    async def get_account_data(self, pubkey: Pubkey) -> Optional[bytes]:
        res = await self._rpc_call("getAccountInfo", [str(pubkey), {"encoding": "base64"}])
        val = res.get("value")
        if not val or not val.get("data"):
            return None
        data_b64 = val["data"][0]
        return base64.b64decode(data_b64)

    async def get_sale_state(self) -> Optional[Dict[str, Any]]:
        """Reads and decodes the live on-chain 1WIN SaleState PDA."""
        state_pda = Pubkey.from_string(config.sale_state_pda)
        raw_data = await self.get_account_data(state_pda)
        if not raw_data or len(raw_data) < 324:
            return None

        offset = 8  # Skip Anchor 8-byte discriminator
        owner = base58.b58encode(raw_data[offset:offset+32]).decode()
        offset += 32
        
        pending_owner_tag = raw_data[offset]
        offset += 1
        pending_owner = None
        if pending_owner_tag == 1:
            pending_owner = base58.b58encode(raw_data[offset:offset+32]).decode()
            offset += 32

        admin = base58.b58encode(raw_data[offset:offset+32]).decode()
        offset += 32
        operator = base58.b58encode(raw_data[offset:offset+32]).decode()
        offset += 32
        usdc_mint = base58.b58encode(raw_data[offset:offset+32]).decode()
        offset += 32
        token_mint = base58.b58encode(raw_data[offset:offset+32]).decode()
        offset += 32
        deposit_vault = base58.b58encode(raw_data[offset:offset+32]).decode()
        offset += 32
        token_vault = base58.b58encode(raw_data[offset:offset+32]).decode()
        offset += 32

        price_usdc = struct.unpack("<Q", raw_data[offset:offset+8])[0]
        offset += 8
        emission = struct.unpack("<Q", raw_data[offset:offset+8])[0]
        offset += 8
        min_per_tx = struct.unpack("<Q", raw_data[offset:offset+8])[0]
        offset += 8
        max_per_tx = struct.unpack("<Q", raw_data[offset:offset+8])[0]
        offset += 8
        deposits_usdc = struct.unpack("<Q", raw_data[offset:offset+8])[0]
        offset += 8
        pool_fixed_amount = struct.unpack("<Q", raw_data[offset:offset+8])[0]
        offset += 8
        participants = struct.unpack("<Q", raw_data[offset:offset+8])[0]
        offset += 8
        sale_start_date = struct.unpack("<q", raw_data[offset:offset+8])[0]
        offset += 8
        sale_end_date = struct.unpack("<q", raw_data[offset:offset+8])[0]
        offset += 8
        claim_duration = struct.unpack("<q", raw_data[offset:offset+8])[0]
        offset += 8
        claim_start_date = struct.unpack("<q", raw_data[offset:offset+8])[0]
        offset += 8
        pool_fixed = bool(raw_data[offset])
        offset += 1
        paused = bool(raw_data[offset])
        offset += 1

        return {
            "owner": owner,
            "pending_owner": pending_owner,
            "admin": admin,
            "operator": operator,
            "usdc_mint": usdc_mint,
            "token_mint": token_mint,
            "deposit_vault": deposit_vault,
            "token_vault": token_vault,
            "price_usdc": price_usdc / 1_000_000.0,
            "emission": emission / 100_000_000.0,
            "min_per_tx_usdc": min_per_tx / 1_000_000.0,
            "max_per_tx_usdc": max_per_tx / 1_000_000.0,
            "deposits_usdc_contributed": deposits_usdc / 1_000_000.0,
            "pool_fixed_amount": pool_fixed_amount,
            "participants": participants,
            "sale_start_date": sale_start_date,
            "sale_end_date": sale_end_date,
            "claim_duration": claim_duration,
            "claim_start_date": claim_start_date,
            "pool_fixed": pool_fixed,
            "paused": paused
        }

    async def get_user_aggregate(self, user: Pubkey) -> Optional[Dict[str, Any]]:
        program_id = Pubkey.from_string(config.sale_program_id)
        agg_pda, _ = Pubkey.find_program_address([b"aggregate", bytes(user)], program_id)
        data = await self.get_account_data(agg_pda)
        if not data or len(data) < 8 + 32 + 8 + 8:
            return None
        
        offset = 8  # discriminator
        wallet = base58.b58encode(data[offset:offset+32]).decode()
        offset += 32
        net_usdc = struct.unpack("<Q", data[offset:offset+8])[0]
        offset += 8
        deposit_count = struct.unpack("<Q", data[offset:offset+8])[0]
        return {
            "pda": agg_pda,
            "wallet": wallet,
            "net_usdc_contributed": net_usdc / 1_000_000.0,
            "deposit_count": deposit_count
        }

    def build_init_aggregate_ix(self, user: Pubkey) -> Instruction:
        """Constructs Anchor init_aggregate instruction."""
        program_id = Pubkey.from_string(config.sale_program_id)
        sale_state_pda = Pubkey.from_string(config.sale_state_pda)
        agg_pda, _ = Pubkey.find_program_address([b"aggregate", bytes(user)], program_id)
        blacklist_pda, _ = Pubkey.find_program_address([b"blacklist", bytes(user)], program_id)
        event_auth_pda, _ = Pubkey.find_program_address([b"__event_authority"], program_id)

        # Discriminator for init_aggregate: [95, 193, 236, 92, 115, 236, 189, 213]
        ix_data = bytes([95, 193, 236, 92, 115, 236, 189, 213])

        accounts = [
            AccountMeta(pubkey=sale_state_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=user, is_signer=True, is_writable=True),
            AccountMeta(pubkey=agg_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=blacklist_pda, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=event_auth_pda, is_signer=False, is_writable=False),
            AccountMeta(pubkey=program_id, is_signer=False, is_writable=False),
        ]
        return Instruction(program_id=program_id, data=ix_data, accounts=accounts)

    def build_purchase_ix(self, user: Pubkey, amount_usdc: float, deposit_count: int = 0) -> Instruction:
        """Constructs Anchor purchase instruction for $1WIN Sale."""
        program_id = Pubkey.from_string(config.sale_program_id)
        sale_state_pda = Pubkey.from_string(config.sale_state_pda)
        agg_pda, _ = Pubkey.find_program_address([b"aggregate", bytes(user)], program_id)
        
        deposit_count_bytes = struct.pack("<Q", deposit_count)
        deposit_pda, _ = Pubkey.find_program_address([b"deposit", bytes(user), deposit_count_bytes], program_id)
        
        blacklist_pda, _ = Pubkey.find_program_address([b"blacklist", bytes(user)], program_id)
        graylist_pda, _ = Pubkey.find_program_address([b"graylist", bytes(user)], program_id)
        event_auth_pda, _ = Pubkey.find_program_address([b"__event_authority"], program_id)

        usdc_mint = Pubkey.from_string(config.usdc_mint)
        user_usdc_ata = self.get_associated_token_address(user, usdc_mint)
        deposit_vault = Pubkey.from_string(config.deposit_vault_usdc)

        # Discriminator for purchase: [21, 93, 113, 154, 193, 160, 242, 168]
        amount_micro = int(amount_usdc * 1_000_000)
        ix_data = bytes([21, 93, 113, 154, 193, 160, 242, 168]) + struct.pack("<Q", amount_micro)

        accounts = [
            AccountMeta(pubkey=sale_state_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=user, is_signer=True, is_writable=True),
            AccountMeta(pubkey=agg_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=deposit_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=blacklist_pda, is_signer=False, is_writable=False),
            AccountMeta(pubkey=graylist_pda, is_signer=False, is_writable=False),
            AccountMeta(pubkey=user_usdc_ata, is_signer=False, is_writable=True),
            AccountMeta(pubkey=deposit_vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=event_auth_pda, is_signer=False, is_writable=False),
            AccountMeta(pubkey=program_id, is_signer=False, is_writable=False),
        ]
        return Instruction(program_id=program_id, data=ix_data, accounts=accounts)

    async def send_transaction(self, tx: VersionedTransaction) -> str:
        serialized = bytes(tx)
        b64_tx = base64.b64encode(serialized).decode()
        res = await self._rpc_call("sendTransaction", [
            b64_tx,
            {
                "encoding": "base64",
                "skipPreflight": False,
                "preflightCommitment": "confirmed",
                "maxRetries": 3
            }
        ])
        return res

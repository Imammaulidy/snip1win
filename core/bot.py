import sys
from pathlib import Path

# Ensure UTF-8 output encoding across all platforms (prevents Windows charmap UnicodeEncodeError)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Ensure root directory is always on sys.path regardless of execution context / PM2
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
import logging
import signal
import time
from typing import Optional, Dict

from aiohttp import web
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ForceReply,
    WebAppInfo,
    MenuButtonWebApp
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from solders.pubkey import Pubkey
import base58

from core.config import config
from core.solana_client import SolanaClient
from core.sniper_engine import SniperEngine
from core.wallet_manager import wallet_manager
from core.web_server import create_web_app, get_local_ip

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("1WinSniperHub")

# Initialize Clients
solana_client = SolanaClient()
sniper_engine = SniperEngine(solana_client)

# In-memory User Interaction State tracking
user_states: Dict[int, Dict] = {}

def is_authorized(user_id: int) -> bool:
    if config.public_access:
        return True
    if not config.allowed_user_ids:
        return True
    return user_id in config.allowed_user_ids

def is_potential_base58_privkey(text: str) -> bool:
    """Detects whether a raw input string is a valid Solana Base58 Private Key."""
    text = text.strip()
    if " " in text or "\n" in text or "\t" in text:
        return False
    if not (40 <= len(text) <= 90):
        return False
    try:
        raw = base58.b58decode(text)
        return len(raw) in (32, 64)
    except Exception:
        return False

# ==============================================================================
# KEYBOARD BUILDERS
# ==============================================================================

def get_reply_keyboard() -> ReplyKeyboardMarkup:
    """Persistent bottom keyboard with In-App Telegram Mini App button."""
    keyboard = [
        [KeyboardButton("📱 Buka $1WIN Mini App", web_app=WebAppInfo(url="https://topnodtools.web.id"))],
        [KeyboardButton("⚡ Snipe Presale"), KeyboardButton("🚀 Snipe DEX")],
        [KeyboardButton("🔴 Jual $1WIN (Sell)"), KeyboardButton("💰 Saldo & Wallet")],
        [KeyboardButton("📊 Status Sale"), KeyboardButton("⚙️ Pengaturan Cepat")],
        [KeyboardButton("🎲 Buat Wallet Baru"), KeyboardButton("🔑 Import Wallet")],
        [KeyboardButton("❓ Bantuan")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Main dashboard inline keyboard."""
    has_wallet = wallet_manager.has_wallet(user_id)
    auto_label = "🔴 Stop Multi-Worker" if sniper_engine.is_auto_running else "🟢 Start Multi-Worker (Satpam & Buy)"

    rows = []
    # Row 1: Action Sniping (Buy Presale & Buy DEX)
    rows.append([
        InlineKeyboardButton("⚡ Snipe Presale", callback_data="menu_snipe_presale"),
        InlineKeyboardButton("🚀 Snipe DEX", callback_data="menu_snipe_dex")
    ])

    # Row 2: Instant Sell & Balances
    rows.append([
        InlineKeyboardButton("🔴 Jual $1WIN (Sell)", callback_data="menu_sell"),
        InlineKeyboardButton("💰 Cek Saldo & Wallet", callback_data="check_wallet")
    ])

    # Row 3: Multi-Worker Toggle
    rows.append([
        InlineKeyboardButton(auto_label, callback_data="toggle_auto")
    ])

    # Row 4: Wallet Management
    if not has_wallet:
        rows.append([
            InlineKeyboardButton("🎲 Buat Wallet Baru", callback_data="create_wallet"),
            InlineKeyboardButton("🔑 Import Private Key", callback_data="prompt_import")
        ])
    else:
        rows.append([
            InlineKeyboardButton("🔑 Ganti Wallet", callback_data="prompt_import"),
            InlineKeyboardButton("📤 Export Private Key", callback_data="export_wallet")
        ])

    # Row 5: Status & Settings
    rows.append([
        InlineKeyboardButton("📊 Status On-Chain", callback_data="check_status"),
        InlineKeyboardButton("⚙️ Pengaturan Cepat", callback_data="check_settings")
    ])

    # Row 6: In-App Mini App Direct Launch Button
    rows.append([
        InlineKeyboardButton("📱 Buka Mini App $1WIN (In-App)", web_app=WebAppInfo(url=f"https://topnodtools.web.id/?auth_id={user_id}"))
    ])

    return InlineKeyboardMarkup(rows)

def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Interactive Settings panel with 1-click preset buttons."""
    rows = []
    # Row 1: Presale USDC Presets
    rows.append([
        InlineKeyboardButton("10 USDC", callback_data="set_usdc_10"),
        InlineKeyboardButton("25 USDC", callback_data="set_usdc_25"),
        InlineKeyboardButton("50 USDC", callback_data="set_usdc_50"),
        InlineKeyboardButton("100 USDC", callback_data="set_usdc_100"),
        InlineKeyboardButton("250 USDC", callback_data="set_usdc_250")
    ])
    # Row 2: DEX SOL Presets
    rows.append([
        InlineKeyboardButton("0.05 SOL", callback_data="set_sol_0.05"),
        InlineKeyboardButton("0.1 SOL", callback_data="set_sol_0.1"),
        InlineKeyboardButton("0.25 SOL", callback_data="set_sol_0.25"),
        InlineKeyboardButton("0.5 SOL", callback_data="set_sol_0.5"),
        InlineKeyboardButton("1.0 SOL", callback_data="set_sol_1.0")
    ])
    # Row 3: Direct Typing (No command needed)
    rows.append([
        InlineKeyboardButton("✏️ Ketik USDC Manual", callback_data="input_custom_usdc"),
        InlineKeyboardButton("✏️ Ketik SOL Manual", callback_data="input_custom_sol")
    ])
    # Row 4: Navigation
    rows.append([
        InlineKeyboardButton("🔄 Refresh Nilai", callback_data="check_settings"),
        InlineKeyboardButton("🔙 Menu Utama", callback_data="main_menu")
    ])
    return InlineKeyboardMarkup(rows)

def get_snipe_presale_keyboard() -> InlineKeyboardMarkup:
    """1-Click Presale purchase presets."""
    def_amount = config.default_purchase_usdc
    rows = [
        [
            InlineKeyboardButton("⚡ 10 USDC", callback_data="do_snipe_presale_10"),
            InlineKeyboardButton("⚡ 25 USDC", callback_data="do_snipe_presale_25"),
            InlineKeyboardButton("⚡ 50 USDC", callback_data="do_snipe_presale_50")
        ],
        [
            InlineKeyboardButton("⚡ 100 USDC", callback_data="do_snipe_presale_100"),
            InlineKeyboardButton("⚡ 250 USDC", callback_data="do_snipe_presale_250"),
            InlineKeyboardButton("⚡ 500 USDC", callback_data="do_snipe_presale_500")
        ],
        [
            InlineKeyboardButton(f"⚡ Beli Default ({def_amount:.1f} USDC)", callback_data=f"do_snipe_presale_{def_amount}")
        ],
        [
            InlineKeyboardButton("✏️ Ketik Nominal Lain", callback_data="input_snipe_custom_usdc"),
            InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(rows)

def get_snipe_dex_keyboard() -> InlineKeyboardMarkup:
    """1-Click DEX Swap presets."""
    def_amount = config.default_snipe_sol
    rows = [
        [
            InlineKeyboardButton("🚀 0.05 SOL", callback_data="do_snipe_dex_0.05"),
            InlineKeyboardButton("🚀 0.1 SOL", callback_data="do_snipe_dex_0.1"),
            InlineKeyboardButton("🚀 0.25 SOL", callback_data="do_snipe_dex_0.25")
        ],
        [
            InlineKeyboardButton("🚀 0.5 SOL", callback_data="do_snipe_dex_0.5"),
            InlineKeyboardButton("🚀 1.0 SOL", callback_data="do_snipe_dex_1.0"),
            InlineKeyboardButton("🚀 2.0 SOL", callback_data="do_snipe_dex_2.0")
        ],
        [
            InlineKeyboardButton(f"🚀 Swap Default ({def_amount:.3f} SOL)", callback_data=f"do_snipe_dex_{def_amount}")
        ],
        [
            InlineKeyboardButton("✏️ Ketik Nominal Lain", callback_data="input_snipe_custom_sol"),
            InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(rows)

def get_sell_keyboard() -> InlineKeyboardMarkup:
    """1-Click Sell / Take Profit presets."""
    rows = [
        [
            InlineKeyboardButton("🔴 Jual 25%", callback_data="do_sell_25"),
            InlineKeyboardButton("🔴 Jual 50%", callback_data="do_sell_50")
        ],
        [
            InlineKeyboardButton("🔥 JUAL 100% (INSTANT DUMP)", callback_data="do_sell_100")
        ],
        [
            InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(rows)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Batal", callback_data="cancel_action")]
    ])

# ==============================================================================
# CORE BOT COMMANDS & PRESENTATION
# ==============================================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("⛔ Akses dibatasi.")
        return

    # Clear pending state
    user_states.pop(user.id, None)

    kp = wallet_manager.get_user_keypair(user.id)
    if kp:
        wallet_info = f"💳 **Wallet Terhubung**: `{kp.pubkey()}`"
    else:
        wallet_info = (
            "⚠️ **Wallet Belum Terhubung!**\n"
            "Klik tombol **🎲 Buat Wallet Baru** atau langsung **Paste Private Key** Anda ke chat."
        )

    text = (
        "🪙 **1WIN TOKEN SALE SNIPER HUB (SOLANA)** 🪙\n\n"
        "Selamat datang di Sniper Bot & Terminal resmi untuk **$1WIN Token Sale**.\n"
        "Sistem dilengkapi Arsitektur Multi-Worker (Worker Satpam Radar, Worker Buy Sub-Milidetik, & Worker One-Click Sell).\n\n"
        f"{wallet_info}\n\n"
        f"🎯 **Target Token CA**: `{config.token_ca}`\n"
        f"🏛 **Sale Program ID**: `{config.sale_program_id}`\n"
        f"💵 **Harga Presale**: $0.03 USDC (SPL)\n"
        f"🌐 **Web Interface**: `https://topnodtools.web.id`\n"
        f"⚙️ **Multi-Worker**: {'🟢 AKTIF (SATPAM & BUY SIAGA)' if sniper_engine.is_auto_running else '⚪ STANDBY'}\n\n"
        "💡 *Gunakan tombol menu di bawah atau tombol keyboard untuk interaksi cepat tanpa mengetik perintah.*"
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_reply_keyboard()
    )
    await update.message.reply_text(
        "⚡ **PILIH AKSI CEPAT**:",
        reply_markup=get_main_keyboard(user.id)
    )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kp = wallet_manager.get_user_keypair(user.id)
    pub = f"`{kp.pubkey()}`" if kp else "Belum Ada"

    text = (
        "🪙 **1WIN SNIPER DASHBOARD**\n\n"
        f"💳 **Wallet**: {pub}\n"
        f"💵 **Preset Presale**: `{config.default_purchase_usdc} USDC`\n"
        f"🟣 **Preset DEX**: `{config.default_snipe_sol} SOL`\n"
        f"⚙️ **Multi-Worker Engine**: {'🟢 AKTIF' if sniper_engine.is_auto_running else '⚪ STANDBY'}\n\n"
        "Pilih tindakan di bawah:"
    )
    if update.callback_query:
        await update.callback_query.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(user.id)
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(user.id)
        )

async def cmd_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user.id):
        return

    kp = wallet_manager.get_user_keypair(user.id)
    if not kp:
        text = (
            "⚠️ **Anda Belum Memiliki Wallet di Bot!**\n\n"
            "Pilih opsi sekali klik di bawah:\n"
            "1️⃣ Klik **🎲 Buat Wallet Baru** untuk membuat dompet Solana otomatis.\n"
            "2️⃣ Klik **🔑 Import Private Key** atau cukup langsung paste private key Anda ke sini."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Buat Wallet Baru", callback_data="create_wallet")],
            [InlineKeyboardButton("🔑 Import Private Key (Paste Langsung)", callback_data="prompt_import")]
        ])
        if update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        return

    pubkey = kp.pubkey()
    if update.callback_query:
        msg = await update.callback_query.message.reply_text("🔄 Memeriksa saldo on-chain...")
    else:
        msg = await update.message.reply_text("🔄 Memeriksa saldo on-chain...")

    sol_bal = await solana_client.get_sol_balance(pubkey)
    usdc_mint = Pubkey.from_string(config.usdc_mint)
    usdc_bal, _ = await solana_client.get_token_balance(pubkey, usdc_mint)
    token_mint = Pubkey.from_string(config.token_ca)
    token_bal, _ = await solana_client.get_token_balance(pubkey, token_mint)

    agg = await solana_client.get_user_aggregate(pubkey)
    purchased_usdc = agg.get("net_usdc_contributed", 0.0) if agg else 0.0

    wallet_text = (
        "💳 **SOLANA SNIPER WALLET**\n\n"
        f"📬 **Alamat Deposit**:\n`{pubkey}`\n\n"
        f"🟣 **Saldo SOL**: `{sol_bal:.4f} SOL`\n"
        f"💵 **Saldo USDC**: `${usdc_bal:.2f} USDC`\n"
        f"🪙 **Saldo $1WIN**: `{token_bal:,.2f} $1WIN`\n"
        f"📥 **Total Kontribusi Presale**: `${purchased_usdc:.2f} USDC`\n\n"
        "💡 *Untuk mengisi saldo, transfer SOL (min 0.01 SOL untuk gas fee) & USDC ke alamat di atas.*"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Beli Presale", callback_data="menu_snipe_presale"),
            InlineKeyboardButton("🚀 Beli DEX", callback_data="menu_snipe_dex")
        ],
        [
            InlineKeyboardButton("🔴 Jual $1WIN (Sell)", callback_data="menu_sell"),
            InlineKeyboardButton("🔄 Refresh Saldo", callback_data="check_wallet")
        ],
        [
            InlineKeyboardButton("🔑 Ganti Wallet (Paste)", callback_data="prompt_import"),
            InlineKeyboardButton("📤 Export Private Key", callback_data="export_wallet")
        ],
        [
            InlineKeyboardButton("🔙 Menu Utama", callback_data="main_menu")
        ]
    ])
    await msg.edit_text(wallet_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

async def cmd_create_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pubkey, priv_b58 = wallet_manager.create_user_wallet(user.id)
    text = (
        "🎉 **WALLET SOLANA BARU BERHASIL DIBUAT!**\n\n"
        f"📬 **Alamat Publik (Deposit)**:\n`{pubkey}`\n\n"
        f"🔐 **Private Key (Base58)**:\n`{priv_b58}`\n\n"
        "⚠️ **PENTING: SIMPAN PRIVATE KEY ANDA!**\n"
        "Private key ini dapat diimpor langsung ke Phantom / Solflare. Jangan bagikan kepada siapa pun!"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(user.id))
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(user.id))

async def prompt_import_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_states[user.id] = {"state": "WAITING_IMPORT"}

    text = (
        "🔑 **HUBUNGKAN WALLET SOLANA (LANGSUNG PASTE)**\n\n"
        "Silakan **langsung kirimkan / paste** Private Key Base58 Solana Anda ke chat ini:\n\n"
        "🛡️ **Proteksi Keamanan Aktif**:\n"
        "Pesan chat Anda yang berisi private key akan **langsung dihapus otomatis** oleh bot dalam hitungan milidetik demi privasi mutlak!\n\n"
        "*(Ketik `batal` atau klik tombol di bawah untuk membatalkan)*"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cancel_keyboard()
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cancel_keyboard()
        )

async def cmd_export_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    priv_b58 = wallet_manager.export_user_wallet(user.id)
    if not priv_b58:
        msg = "⚠️ Anda belum memiliki wallet yang tersimpan."
        if update.callback_query:
            await update.callback_query.message.reply_text(msg)
        else:
            await update.message.reply_text(msg)
        return

    kp = wallet_manager.get_user_keypair(user.id)
    pubkey = kp.pubkey() if kp else "Unknown"

    text = (
        "🔐 **EXPORT PRIVATE KEY WALLET ANDA**\n\n"
        f"📬 **Alamat**: `{pubkey}`\n\n"
        f"🔑 **Private Key**:\n`{priv_b58}`\n\n"
        "⚠️ *Simpan baik-baik di tempat aman dan jangan berikan kepada siapa pun!*"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.callback_query:
        msg = await update.callback_query.message.reply_text("🔄 Memeriksa status on-chain Solana...")
    else:
        msg = await update.message.reply_text("🔄 Memeriksa status on-chain Solana...")

    try:
        state = await solana_client.get_sale_state()
        if not state:
            await msg.edit_text("❌ Gagal membaca SaleState on-chain dari Solana RPC.")
            return

        now_ts = int(time.time())
        start_ts = state["sale_start_date"]
        time_left = start_ts - now_ts
        if time_left > 0:
            hours, rem = divmod(time_left, 3600)
            mins, secs = divmod(rem, 60)
            countdown_str = f"⏳ Dimulai dalam: **{hours}j {mins}m {secs}d**"
        else:
            countdown_str = "🟢 **SALE TELAH DIMULAI (ACTIVE)!**"

        dex_quote = await sniper_engine.get_dex_quote(0.1)
        dex_status = "🟢 Likuiditas Terdeteksi di Jupiter!" if dex_quote else "⚪ Belum Ada Pool DEX"

        status_text = (
            "📊 **STATUS ON-CHAIN $1WIN TOKEN SALE**\n\n"
            f"🪙 **Token CA**:\n`{state['token_mint']}`\n\n"
            f"⏰ **Waktu Mulai**: {time.ctime(start_ts)} (UTC)\n"
            f"👉 **Hitung Mundur**: {countdown_str}\n"
            f"💰 **Harga Presale**: `${state['price_usdc']:.2f} USDC`\n"
            f"📦 **Alokasi Total**: `{state['emission']:,.0f} $1WIN`\n"
            f"📥 **Total Terkumpul**: `${state['deposits_usdc_contributed']:,.2f} USDC`\n"
            f"⏸ **Status Pause**: {'🔴 YA' if state['paused'] else '🟢 NORMAL'}\n"
            f"🔒 **Pool Fixed**: {'🔴 YA' if state['pool_fixed'] else '🟢 TIDAK'}\n\n"
            f"📈 **Status DEX (Jupiter/Raydium)**: {dex_status}\n"
            f"🤖 **Multi-Worker**: {'🟢 AKTIF (SATPAM & BUY SIAGA)' if sniper_engine.is_auto_running else '⚪ STANDBY'}"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚡ Snipe Presale", callback_data="menu_snipe_presale"),
                InlineKeyboardButton("🚀 Snipe DEX", callback_data="menu_snipe_dex")
            ],
            [
                InlineKeyboardButton("🔴 Jual $1WIN (Sell)", callback_data="menu_sell"),
                InlineKeyboardButton("🔄 Refresh Status", callback_data="check_status")
            ],
            [
                InlineKeyboardButton("🔙 Menu Utama", callback_data="main_menu")
            ]
        ])
        await msg.edit_text(status_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    except Exception as e:
        await msg.edit_text(f"❌ Error memeriksa status: {e}")

async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚙️ **PANEL PENGATURAN CEPAT (1-KLIK)**\n\n"
        f"💵 **Default Beli Presale**: `{config.default_purchase_usdc:.2f} USDC`\n"
        f"🟣 **Default Beli DEX**: `{config.default_snipe_sol:.3f} SOL`\n"
        f"📊 **Slippage DEX**: `{config.slippage_bps / 100:.1f}%`\n"
        f"⚡ **Priority Fee**: `{config.priority_fee_micro_lamports}` microLamports\n\n"
        "💡 *Klik tombol preset di bawah untuk mengubah nominal secara instan, atau klik 'Ketik Manual' tanpa perintah:* "
    )
    if update.callback_query:
        await update.callback_query.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_settings_keyboard()
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_settings_keyboard()
        )

async def show_snipe_presale_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kp = wallet_manager.get_user_keypair(user.id)
    if not kp:
        msg = "⚠️ Anda belum memiliki wallet. Silakan buat baru atau import wallet terlebih dahulu!"
        if update.callback_query:
            await update.callback_query.message.reply_text(msg, reply_markup=get_main_keyboard(user.id))
        else:
            await update.message.reply_text(msg, reply_markup=get_main_keyboard(user.id))
        return

    usdc_mint = Pubkey.from_string(config.usdc_mint)
    usdc_bal, _ = await solana_client.get_token_balance(kp.pubkey(), usdc_mint)
    sol_bal = await solana_client.get_sol_balance(kp.pubkey())

    text = (
        "⚡ **EKSEKUSI PRESALE INSTAN ($0.03 / $1WIN)**\n\n"
        f"📬 **Wallet**: `{kp.pubkey()}`\n"
        f"💵 **Saldo USDC**: `${usdc_bal:.2f} USDC`\n"
        f"🟣 **Saldo Gas (SOL)**: `{sol_bal:.4f} SOL`\n\n"
        "Pilih nominal di bawah untuk langsung mengeksekusi pembelian presale:"
    )
    if update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_snipe_presale_keyboard())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_snipe_presale_keyboard())

async def show_snipe_dex_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kp = wallet_manager.get_user_keypair(user.id)
    if not kp:
        msg = "⚠️ Anda belum memiliki wallet. Silakan buat baru atau import wallet terlebih dahulu!"
        if update.callback_query:
            await update.callback_query.message.reply_text(msg, reply_markup=get_main_keyboard(user.id))
        else:
            await update.message.reply_text(msg, reply_markup=get_main_keyboard(user.id))
        return

    sol_bal = await solana_client.get_sol_balance(kp.pubkey())
    text = (
        "🚀 **EKSEKUSI DEX SWAP INSTAN (JUPITER / RAYDIUM)**\n\n"
        f"📬 **Wallet**: `{kp.pubkey()}`\n"
        f"🟣 **Saldo SOL Tersedia**: `{sol_bal:.4f} SOL`\n"
        f"🎯 **Target Token**: `{config.token_ca}`\n\n"
        "Pilih nominal SOL di bawah untuk langsung swap via Jupiter:"
    )
    if update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_snipe_dex_keyboard())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_snipe_dex_keyboard())

async def show_sell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Worker One-Click Sell menu on Telegram."""
    user = update.effective_user
    kp = wallet_manager.get_user_keypair(user.id)
    if not kp:
        msg = "⚠️ Anda belum memiliki wallet. Buat atau import wallet terlebih dahulu!"
        if update.callback_query:
            await update.callback_query.message.reply_text(msg, reply_markup=get_main_keyboard(user.id))
        else:
            await update.message.reply_text(msg, reply_markup=get_main_keyboard(user.id))
        return

    token_mint = Pubkey.from_string(config.token_ca)
    token_bal, _ = await solana_client.get_token_balance(kp.pubkey(), token_mint)

    text = (
        "🔥 **WORKER ONE-CLICK SELL ($1WIN -> SOL)**\n\n"
        f"📬 **Wallet**: `{kp.pubkey()}`\n"
        f"🪙 **Saldo $1WIN Saat Ini**: `{token_bal:,.2f} $1WIN`\n\n"
        "Pilih persentase penjualan instan via Jupiter Swap:"
    )
    if update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_sell_keyboard())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_sell_keyboard())

async def show_web_terminal_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        "🌐 **1WIN SNIPER TELEGRAM MINI APP**\n\n"
        "Antarmuka Mini App terintegrasi langsung di dalam Telegram:\n"
        "🔗 **Domain**: `https://topnodtools.web.id`\n\n"
        "Keunggulan Telegram Mini App:\n"
        "✅ **Zero-Click In-App Launch**: Buka langsung di dalam Telegram tanpa keluar ke browser luar!\n"
        "✅ **Otomatis Terhubung**: Data wallet & saldo akun Anda langsung aktif seketika.\n"
        "✅ **Multi-Worker Live Monitor**: Pantau status Worker Satpam & Worker Buy secara visual.\n"
        "✅ **One-Click Sell Hub**: Jual token $1WIN 25% / 50% / 100% langsung di dalam aplikasi."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Buka Mini App $1WIN (In-App)", web_app=WebAppInfo(url=f"https://topnodtools.web.id/?auth_id={user.id}"))],
        [InlineKeyboardButton("🔙 Menu Utama", callback_data="main_menu")]
    ])
    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 **PANDUAN LENGKAP 1WIN SNIPER HUB**\n\n"
        "🚀 **Navigasi Cepat (Tanpa Perlu Mengetik Perintah)**:\n"
        "• Gunakan tombol Reply Keyboard di bawah layar untuk navigasi instan.\n"
        "• Klik '🔑 Import Wallet' lalu cukup **PASTE** private key Anda (pesan langsung dihapus demi privasi).\n"
        "• Klik '🔴 Jual $1WIN (Sell)' untuk take profit instan (25%, 50%, 100%).\n"
        "• Klik '🟢 Start Multi-Worker' untuk mengaktifkan Satpam Radar & Buy Executor otomatis.\n\n"
        "🌐 **Web Interface**: `https://topnodtools.web.id`"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# ==============================================================================
# SMART TEXT & STATE HANDLER (NO COMMANDS REQUIRED)
# ==============================================================================

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    raw_text = update.message.text.strip()

    # 1. State Processing
    state_info = user_states.get(user.id)
    if state_info:
        current_state = state_info.get("state")

        # Cancellation
        if raw_text.lower() in ["batal", "cancel", "/cancel"]:
            user_states.pop(user.id, None)
            await update.message.reply_text("❌ Aksi dibatalkan.", reply_markup=get_reply_keyboard())
            await show_main_menu(update, context)
            return

        # STATE: WAITING_IMPORT
        if current_state == "WAITING_IMPORT":
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                pass

            user_states.pop(user.id, None)
            success, result = wallet_manager.import_user_wallet(user.id, raw_text)
            if success:
                text = (
                    "🎉 **WALLET SOLANA BERHASIL DIHUBUNGKAN!**\n\n"
                    f"📬 **Alamat Wallet**:\n`{result}`\n\n"
                    "🛡️ *Pesan Anda yang berisi private key telah otomatis dihapus oleh bot demi keamanan mutlak.*"
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_main_keyboard(user.id)
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ **Gagal Import Wallet**: {result}\n\nPastikan format Base58 Solana Anda benar (32 atau 64 bytes).",
                    reply_markup=get_main_keyboard(user.id)
                )
            return

        # STATE: WAITING_CUSTOM_USDC
        if current_state == "WAITING_CUSTOM_USDC":
            user_states.pop(user.id, None)
            try:
                val = float(raw_text.replace(",", "."))
                if val <= 0:
                    raise ValueError()
                config.default_purchase_usdc = val
                config.save_to_file()
                await update.message.reply_text(
                    f"✅ **Default Presale Berhasil Diubah!**\n\nNominal baru: `{val:.2f} USDC`",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_settings_keyboard()
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ Input tidak valid. Masukkan angka positif (contoh: 50 atau 100.5).",
                    reply_markup=get_settings_keyboard()
                )
            return

        # STATE: WAITING_CUSTOM_SOL
        if current_state == "WAITING_CUSTOM_SOL":
            user_states.pop(user.id, None)
            try:
                val = float(raw_text.replace(",", "."))
                if val <= 0:
                    raise ValueError()
                config.default_snipe_sol = val
                config.save_to_file()
                await update.message.reply_text(
                    f"✅ **Default DEX Swap Berhasil Diubah!**\n\nNominal baru: `{val:.3f} SOL`",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_settings_keyboard()
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ Input tidak valid. Masukkan angka positif (contoh: 0.5 atau 1.2).",
                    reply_markup=get_settings_keyboard()
                )
            return

        # STATE: WAITING_SNIPE_CUSTOM_USDC
        if current_state == "WAITING_SNIPE_CUSTOM_USDC":
            user_states.pop(user.id, None)
            try:
                val = float(raw_text.replace(",", "."))
                if val <= 0:
                    raise ValueError()
                kp = wallet_manager.get_user_keypair(user.id)
                if not kp:
                    await update.message.reply_text("⚠️ Anda belum memiliki wallet.")
                    return
                msg = await update.message.reply_text(f"⚡ Worker Buy mengeksekusi Presale Snipe sebesar {val:.2f} USDC...")
                res = await sniper_engine.execute_presale_snipe(amount_usdc=val, keypair=kp)
                if res.get("success"):
                    await msg.edit_text(
                        f"🎉 **PRESALE SNIPE SUKSES!**\n\n"
                        f"💵 **Jumlah**: `{res.get('amount_usdc')} USDC`\n"
                        f"🔗 **Transaksi**: `{res.get('tx_hash')}`\n"
                        f"🌐 [Cek di Solscan]({res.get('solscan_url')})",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await msg.edit_text(f"❌ **Snipe Gagal**: {res.get('error')}", parse_mode=ParseMode.MARKDOWN)
            except ValueError:
                await update.message.reply_text("❌ Input tidak valid.", reply_markup=get_reply_keyboard())
            return

        # STATE: WAITING_SNIPE_CUSTOM_SOL
        if current_state == "WAITING_SNIPE_CUSTOM_SOL":
            user_states.pop(user.id, None)
            try:
                val = float(raw_text.replace(",", "."))
                if val <= 0:
                    raise ValueError()
                kp = wallet_manager.get_user_keypair(user.id)
                if not kp:
                    await update.message.reply_text("⚠️ Anda belum memiliki wallet.")
                    return
                msg = await update.message.reply_text(f"🚀 Worker Buy mengeksekusi DEX Swap sebesar {val:.3f} SOL...")
                res = await sniper_engine.execute_dex_snipe(amount_sol=val, keypair=kp)
                if res.get("success"):
                    await msg.edit_text(
                        f"🔥 **DEX SWAP SUKSES!**\n\n"
                        f"🟣 **Input**: `{res.get('amount_sol')} SOL`\n"
                        f"🪙 **Estimasi Token**: `{res.get('tokens_received_est'):,.2f} $1WIN`\n"
                        f"🔗 **TX**: `{res.get('tx_hash')}`\n"
                        f"🌐 [Cek di Solscan]({res.get('solscan_url')})",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await msg.edit_text(f"❌ **DEX Swap Gagal**: {res.get('error')}", parse_mode=ParseMode.MARKDOWN)
            except ValueError:
                await update.message.reply_text("❌ Input tidak valid.", reply_markup=get_reply_keyboard())
            return

    # 2. Smart Detection: Cek apakah input adalah Private Key Base58 langsung (tanpa klik tombol import)
    if is_potential_base58_privkey(raw_text):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass
        success, result = wallet_manager.import_user_wallet(user.id, raw_text)
        if success:
            text = (
                "🛡️ **PRIVATE KEY SOLANA TERDETEKSI & BERHASIL DIHUBUNGKAN!**\n\n"
                f"📬 **Alamat Wallet**:\n`{result}`\n\n"
                "🔒 *Pesan private key Anda telah otomatis dihapus seketika demi perlindungan keamanan.*"
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_keyboard(user.id)
            )
            return

    # 3. Persistent Reply Keyboard Text Matches
    if raw_text in ["⚡ Snipe Presale", "/snipe"]:
        await show_snipe_presale_menu(update, context)
        return
    elif raw_text in ["🚀 Snipe DEX", "/snipe_dex"]:
        await show_snipe_dex_menu(update, context)
        return
    elif raw_text in ["🔴 Jual $1WIN (Sell)", "/sell"]:
        await show_sell_menu(update, context)
        return
    elif raw_text in ["💰 Saldo & Wallet", "💰 Cek Saldo & Wallet", "/wallet"]:
        await cmd_wallet(update, context)
        return
    elif raw_text in ["📊 Status Sale", "📊 Status On-Chain", "/status"]:
        await cmd_status(update, context)
        return
    elif raw_text in ["⚙️ Pengaturan Cepat", "⚙️ Pengaturan", "⚙️ Konfigurasi", "/settings"]:
        await show_settings_menu(update, context)
        return
    elif raw_text in ["🎲 Buat Wallet Baru", "/create_wallet"]:
        await cmd_create_wallet(update, context)
        return
    elif raw_text in ["🔑 Import Wallet", "/import"]:
        await prompt_import_action(update, context)
        return
    elif raw_text in ["📤 Export Wallet", "/export"]:
        await cmd_export_wallet(update, context)
        return
    elif raw_text in ["🌐 Web Terminal", "/weblogin"]:
        await show_web_terminal_info(update, context)
        return
    elif raw_text in ["❓ Bantuan", "/help"]:
        await cmd_help(update, context)
        return

    # Fallback to main menu
    await show_main_menu(update, context)

# ==============================================================================
# INLINE CALLBACK DISPATCHER
# ==============================================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    # Navigation
    if data == "main_menu":
        user_states.pop(user.id, None)
        await show_main_menu(update, context)
        return

    elif data == "cancel_action":
        user_states.pop(user.id, None)
        await query.message.reply_text("❌ Aksi dibatalkan.", reply_markup=get_reply_keyboard())
        await show_main_menu(update, context)
        return

    # Wallet management
    elif data == "create_wallet":
        pubkey, priv_b58 = wallet_manager.create_user_wallet(user.id)
        text = (
            "🎉 **WALLET SOLANA BARU BERHASIL DIBUAT!**\n\n"
            f"📬 **Alamat Deposit**:\n`{pubkey}`\n\n"
            f"🔐 **Private Key (Base58)**:\n`{priv_b58}`\n\n"
            "⚠️ *Simpan private key di tempat aman. Anda bisa mengimpornya ke Phantom / Solflare.*"
        )
        await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(user.id))

    elif data == "prompt_import":
        await prompt_import_action(update, context)

    elif data == "export_wallet":
        await cmd_export_wallet(update, context)

    elif data == "check_wallet":
        await cmd_wallet(update, context)

    elif data == "check_status":
        await cmd_status(update, context)

    elif data == "check_settings":
        await show_settings_menu(update, context)

    # Menus
    elif data == "menu_snipe_presale":
        await show_snipe_presale_menu(update, context)

    elif data == "menu_snipe_dex":
        await show_snipe_dex_menu(update, context)

    elif data == "menu_sell":
        await show_sell_menu(update, context)

    # 1-Click Settings Presets
    elif data.startswith("set_usdc_"):
        val = float(data.replace("set_usdc_", ""))
        config.default_purchase_usdc = val
        config.save_to_file()
        await query.message.reply_text(
            f"✅ **Default Presale Berhasil Diubah!**\n\nNominal baru: `{val:.2f} USDC`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_settings_keyboard()
        )

    elif data.startswith("set_sol_"):
        val = float(data.replace("set_sol_", ""))
        config.default_snipe_sol = val
        config.save_to_file()
        await query.message.reply_text(
            f"✅ **Default DEX Swap Berhasil Diubah!**\n\nNominal baru: `{val:.3f} SOL`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_settings_keyboard()
        )

    # Direct Typing Mode (No command needed)
    elif data == "input_custom_usdc":
        user_states[user.id] = {"state": "WAITING_CUSTOM_USDC"}
        await query.message.reply_text(
            "💵 **MASUKKAN NOMINAL PRESALE (USDC)**:\n\n"
            "Silakan langsung ketik angka nominal USDC yang Anda inginkan (contoh: `75` atau `150`):\n\n"
            "*(Ketik `batal` untuk membatalkan)*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cancel_keyboard()
        )

    elif data == "input_custom_sol":
        user_states[user.id] = {"state": "WAITING_CUSTOM_SOL"}
        await query.message.reply_text(
            "🟣 **MASUKKAN NOMINAL DEX SWAP (SOL)**:\n\n"
            "Silakan langsung ketik angka nominal SOL yang Anda inginkan (contoh: `0.75` atau `1.5`):\n\n"
            "*(Ketik `batal` untuk membatalkan)*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cancel_keyboard()
        )

    elif data == "input_snipe_custom_usdc":
        user_states[user.id] = {"state": "WAITING_SNIPE_CUSTOM_USDC"}
        await query.message.reply_text(
            "⚡ **EKSEKUSI PRESALE CUSTOM (USDC)**:\n\n"
            "Silakan langsung ketik nominal USDC untuk pembelian presale kali ini (contoh: `30` atau `80`):\n\n"
            "*(Ketik `batal` untuk membatalkan)*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cancel_keyboard()
        )

    elif data == "input_snipe_custom_sol":
        user_states[user.id] = {"state": "WAITING_SNIPE_CUSTOM_SOL"}
        await query.message.reply_text(
            "🚀 **EKSEKUSI DEX SWAP CUSTOM (SOL)**:\n\n"
            "Silakan langsung ketik nominal SOL untuk swap via Jupiter kali ini (contoh: `0.35` atau `1.2`):\n\n"
            "*(Ketik `batal` untuk membatalkan)*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cancel_keyboard()
        )

    # 1-Click Execution Presets (BUY)
    elif data.startswith("do_snipe_presale_"):
        amount = float(data.replace("do_snipe_presale_", ""))
        kp = wallet_manager.get_user_keypair(user.id)
        if not kp:
            await query.message.reply_text("⚠️ Anda belum memiliki wallet.")
            return
        msg = await query.message.reply_text(f"⚡ Worker Buy mengeksekusi Presale Snipe sebesar {amount:.2f} USDC...")
        res = await sniper_engine.execute_presale_snipe(amount_usdc=amount, keypair=kp)
        if res.get("success"):
            await msg.edit_text(
                f"🎉 **PRESALE SNIPE SUKSES!**\n\n"
                f"💵 **Jumlah**: `{res.get('amount_usdc')} USDC`\n"
                f"🔗 **Transaksi**: `{res.get('tx_hash')}`\n"
                f"🌐 [Cek di Solscan]({res.get('solscan_url')})",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await msg.edit_text(f"❌ **Presale Snipe Gagal**: {res.get('error')}", parse_mode=ParseMode.MARKDOWN)

    elif data.startswith("do_snipe_dex_"):
        amount = float(data.replace("do_snipe_dex_", ""))
        kp = wallet_manager.get_user_keypair(user.id)
        if not kp:
            await query.message.reply_text("⚠️ Anda belum memiliki wallet.")
            return
        msg = await query.message.reply_text(f"🚀 Worker Buy mengeksekusi DEX Swap sebesar {amount:.3f} SOL...")
        res = await sniper_engine.execute_dex_snipe(amount_sol=amount, keypair=kp)
        if res.get("success"):
            await msg.edit_text(
                f"🔥 **DEX SWAP SUKSES!**\n\n"
                f"🟣 **Input**: `{res.get('amount_sol')} SOL`\n"
                f"🪙 **Estimasi Token**: `{res.get('tokens_received_est'):,.2f} $1WIN`\n"
                f"🔗 **TX**: `{res.get('tx_hash')}`\n"
                f"🌐 [Cek di Solscan]({res.get('solscan_url')})",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await msg.edit_text(f"❌ **DEX Swap Gagal**: {res.get('error')}", parse_mode=ParseMode.MARKDOWN)

    # 1-Click Execution Presets (SELL)
    elif data.startswith("do_sell_"):
        pct = float(data.replace("do_sell_", ""))
        kp = wallet_manager.get_user_keypair(user.id)
        if not kp:
            await query.message.reply_text("⚠️ Anda belum memiliki wallet.")
            return
        msg = await query.message.reply_text(f"🔴 Worker Sell mengeksekusi penjualan {pct:.0f}% token $1WIN via Jupiter...")
        res = await sniper_engine.execute_sell_snipe(percentage=pct, keypair=kp)
        if res.get("success"):
            await msg.edit_text(
                f"🎉 **ONE-CLICK SELL BERHASIL!**\n\n"
                f"🪙 **Token Terjual**: `{res.get('tokens_sold'):,.2f} $1WIN` ({pct:.0f}%)\n"
                f"🟣 **Est SOL Diterima**: `{res.get('sol_received_est'):.4f} SOL`\n"
                f"🔗 **TX**: `{res.get('tx_hash')}`\n"
                f"🌐 [Cek di Solscan]({res.get('solscan_url')})",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await msg.edit_text(f"❌ **Sell Gagal**: {res.get('error')}", parse_mode=ParseMode.MARKDOWN)

    # Multi-Worker Toggle
    elif data == "toggle_auto":
        chat_id = query.message.chat_id
        kp = wallet_manager.get_user_keypair(user.id)
        if not kp:
            await query.message.reply_text("⚠️ Hubungkan wallet terlebih dahulu sebelum mengaktifkan Multi-Worker.")
            return

        if sniper_engine.is_auto_running:
            sniper_engine.stop_all_workers()
            await query.message.reply_text("🔴 **Multi-Worker Dinonaktifkan.**", reply_markup=get_main_keyboard(user.id))
        else:
            async def notify(text_msg: str):
                try:
                    await context.bot.send_message(chat_id=chat_id, text=text_msg, parse_mode=ParseMode.MARKDOWN)
                except Exception as e:
                    logger.error(f"Error sending notification: {e}")
            sniper_engine.start_multi_workers(notify, keypair=kp, user_id=user.id)
            await query.message.reply_text(
                "🟢 **Multi-Worker Diaktifkan!**\n"
                "• 🛡️ **Worker Satpam**: Memindai jaringan & CA setiap 250ms\n"
                "• ⚡ **Worker Buy**: Siap tembak sub-milidetik begitu launching!",
                reply_markup=get_main_keyboard(user.id)
            )

# ==============================================================================
# UNIFIED HUB RUNNER
# ==============================================================================

async def run_unified_hub():
    token = config.telegram_bot_token.strip()
    if not token:
        print("=" * 60)
        print("⚠️ PERHATIAN: TELEGRAM_BOT_TOKEN BELUM DIISI!")
        print("=" * 60)
        return

    local_ip = get_local_ip()
    port = 6000

    # 1. Start Web Server
    web_app = create_web_app(sniper_engine, solana_client)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, host=local_ip, port=port)
    await site.start()

    print("=" * 70)
    print("🚀 1WIN TOKEN SALE SNIPER HUB AKTIF & SINKRON")
    print(f"🌐 Backend Web Terminal: http://{local_ip}:{port}")
    print(f"☁️ Cloudflare Ingress   : topnodtools.web.id -> http://{local_ip}:{port}")
    print(f"🤖 Telegram Bot         : @snip1winprimatabot")
    print("=" * 70)

    # 2. Build Telegram Bot
    tg_app = ApplicationBuilder().token(token).build()

    # Register Commands
    tg_app.add_handler(CommandHandler("start", cmd_start))
    tg_app.add_handler(CommandHandler("status", cmd_status))
    tg_app.add_handler(CommandHandler("wallet", cmd_wallet))
    tg_app.add_handler(CommandHandler("create_wallet", cmd_create_wallet))
    tg_app.add_handler(CommandHandler("export", cmd_export_wallet))
    tg_app.add_handler(CommandHandler("settings", show_settings_menu))
    tg_app.add_handler(CommandHandler("sell", show_sell_menu))
    tg_app.add_handler(CommandHandler("help", cmd_help))

    # Register Interactive Callbacks
    tg_app.add_handler(CallbackQueryHandler(callback_handler))

    # Register Smart Text & State Handler (Handles 1-Click Buttons, Direct Numbers, and Raw Private Keys)
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # 3. Concurrent Execution
    async with tg_app:
        await tg_app.start()
        await tg_app.updater.start_polling()

        # Set Telegram Menu Button to Mini App WebApp
        try:
            await tg_app.bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="Sniper App", web_app=WebAppInfo(url="https://topnodtools.web.id"))
            )
        except Exception as e:
            print(f"[MenuButtonWebApp Info] {e}")

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass

        try:
            await stop_event.wait()
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            print("\n[Shutdown] Menghentikan bot Telegram dan Web Server...")
            await tg_app.updater.stop()
            await tg_app.stop()
            await runner.cleanup()
            await solana_client.close()
            await sniper_engine.close()
            print("[Shutdown] Selesai.")

def main():
    try:
        asyncio.run(run_unified_hub())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)

if __name__ == "__main__":
    main()

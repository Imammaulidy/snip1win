# 1WIN Official On-Chain Contract & Token Sale Architecture

Dokumen ini memuat hasil verifikasi on-chain dan dekompilasi Anchor state Solana resmi dari endpoint `1wintoken.com`.

---

## 1. Spesifikasi Token Utama ($1WIN)

| Parameter | Nilai On-Chain | Keterangan |
| :--- | :--- | :--- |
| **Token Name** | 1win Token | Resmi dari 1wintoken.com |
| **Token Symbol** | $1WIN | SPL Token Standard |
| **Contract Address (CA / Mint)** | `FjPKUGnF5zBpdEv18gT8FJCtxh3MKrFkoeYekgYr1win` | Vanity Address berakhiran `1win` |
| **Network** | Solana Mainnet-Beta | SPL Token Program |
| **Decimals** | 8 | 1 $1WIN = 100,000,000 base units |
| **Total Supply** | 1,000,000,000 $1WIN | Pasokan tetap |
| **Sale Allocation** | 130,000,000 $1WIN | 130 juta token |
| **Sale Price** | $0.03 USDC | 30,000 micro-USDC (6 desimal) |
| **Token Program** | `TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA` | Standard SPL Token |

---

## 2. Arsitektur Smart Contract Token Sale (Solana)

Penjualan token dijalankan melalui Anchor Program khusus di jaringan Solana:

- **Sale Program ID**: `GWvQinGBRa7ZUzhXY23MrLjdsx3KfRGxH8yXURBwrz1R`
- **Sale State PDA**: `E9Sdba46tH8KD9PPwZngGwkHVnmrbKL64Qz8PnBMiiAL`
  - Seed: `b"sale_state"`
- **Accepted Payment Currency**: Native Solana USDC
  - Mint: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`
- **Deposit Vault (USDC)**: `HciAS69vfU1ZzfWEczqwkAUfLodpbGFVALLpA1wtA5W2`
- **Token Vault ($1WIN)**: `7zWFaaSu9VgAoWPgXYmgMiS4tNG1gDv4kzHUkbiK4y98`
- **Admin Address**: `G68zSDguycN8BfZLtpQRBDbkBaw62aaMV5EpdoaqsEVm`
- **Owner Authority**: `4K5xxirCw8WD5uKGcu5kP3qdh5ZkBanNbm6BVoKD8vcf`

---

## 3. Parameter Penjualan & Jadwal

- **Sale Start Date**: `1792076400` (15 Oktober 2026, 15:00:00 UTC / 22:00 WIB)
- **Sale End Date**: `1793376000`
- **Min Pembelian per Transaksi**: 10 USDC (`10,000,000` micro-USDC)
- **Max Pembelian per Transaksi**: 250,000 USDC (`250,000,000,000` micro-USDC)
- **Claim Start Date**: `1793462460`
- **Claim Duration**: 365 Hari (`31536000` detik)

---

## 4. Multi-Chain Contracts (BSC Backup)

- **BSC Token Sale Contract**: `0x3077E6b4337099Cad60Da8E73E25b1530396046d`
- **BSC Vesting Contract**: `0xf307b7525131AB31bCf09Bcc38De8f0D318DdeAF`
- **BSC AML Registry**: `0x1bb4c3e2f93BCcA4D68AfA353fc9e3331CD5B100`

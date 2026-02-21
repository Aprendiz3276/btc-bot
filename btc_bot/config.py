"""
config.py — Configuración central del bot
Carga todas las variables desde el archivo .env
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Credenciales del exchange ──────────────────────────────────────────────
API_KEY = os.getenv("API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "")
API_PASSPHRASE = os.getenv("API_PASSPHRASE", "")   # Solo necesario para OKX

# ── Exchange ───────────────────────────────────────────────────────────────
# Opciones soportadas: binanceusdm | bybit | okx
EXCHANGE_NAME = os.getenv("EXCHANGE_NAME", "binanceusdm")

# ── Par y timeframes ───────────────────────────────────────────────────────
SYMBOL = os.getenv("SYMBOL", "BTC/USDT")
TIMEFRAME_1H = "1h"
TIMEFRAME_15M = "15m"

# ── Parámetros de capital y riesgo ─────────────────────────────────────────
CAPITAL_TOTAL = float(os.getenv("CAPITAL_TOTAL", "500"))        # USDT
MARGIN_PCT = float(os.getenv("MARGIN_PCT", "0.20"))          # 20%
LEVERAGE = int(os.getenv("LEVERAGE", "20"))
MAX_RISK_USDT = float(os.getenv("MAX_RISK_USDT", "250")
                      )        # 50% del capital
MIN_RR_RATIO = float(os.getenv("MIN_RR_RATIO", "1.5"))         # R:R mínimo

# Capital efectivo por operación
# 100 USDT por defecto
MARGIN_PER_TRADE = CAPITAL_TOTAL * MARGIN_PCT
NOTIONAL_VALUE = MARGIN_PER_TRADE * \
    LEVERAGE                     # 2000 USDT por defecto

# ── Parámetros de la estrategia Breakout ──────────────────────────────────
LONG_ENTRY_OFFSET = float(
    os.getenv("LONG_ENTRY_OFFSET", "40"))     # entry = resist - 40
LONG_SL_OFFSET = float(os.getenv("LONG_SL_OFFSET", "640")
                       )       # SL = resist - 640
# pullback máx desde resist
LONG_PULLBACK_MAX = float(os.getenv("LONG_PULLBACK_MAX", "300"))

SHORT_ENTRY_OFFSET = float(
    os.getenv("SHORT_ENTRY_OFFSET", "50"))    # entry = support + 50
# SL = support + 650
SHORT_SL_OFFSET = float(os.getenv("SHORT_SL_OFFSET", "650"))
# TP1 = support - 1400
SHORT_TP1_OFFSET = float(os.getenv("SHORT_TP1_OFFSET", "1400"))
# TP2 = support - 2800
SHORT_TP2_OFFSET = float(os.getenv("SHORT_TP2_OFFSET", "2800"))

# ── Gestión de posición abierta ────────────────────────────────────────────
TP1_CLOSE_PCT = float(os.getenv("TP1_CLOSE_PCT", "0.50")
                      )       # Cerrar 50% en TP1
TRAILING_ACTIVATION_PCT = float(
    os.getenv("TRAILING_ACTIVATION_PCT", "0.005"))  # +0.5% sobre TP1
TRAILING_OFFSET_PCT = float(
    os.getenv("TRAILING_OFFSET_PCT", "0.004"))  # trailing 0.4%

# ── Intervalos del loop ────────────────────────────────────────────────────
LOOP_INTERVAL_SECONDS = int(
    os.getenv("LOOP_INTERVAL_SECONDS", "300"))   # 5 minutos
MAINTENANCE_PAUSE_MIN = int(os.getenv("MAINTENANCE_PAUSE_MIN", "10"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# ── Modo paper trading ─────────────────────────────────────────────────────
PAPER_TRADING = os.getenv("PAPER_TRADING", "false").lower() == "true"

# ── Telegram ───────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Archivos de estado ─────────────────────────────────────────────────────
STATE_FILE = "state.json"
LOG_FILE = "bot.log"
TIMEZONE = "America/Bogota"

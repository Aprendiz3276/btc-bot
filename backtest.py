"""
backtest.py — Backtesting básico de la estrategia con datos históricos de ccxt
Descarga datos OHLCV y simula la estrategia vela a vela
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from btc_bot.config import (
    EXCHANGE_NAME, SYMBOL, TIMEFRAME_1H,
    LONG_ENTRY_OFFSET, LONG_SL_OFFSET, LONG_PULLBACK_MAX,
    SHORT_ENTRY_OFFSET, SHORT_SL_OFFSET, SHORT_TP1_OFFSET, SHORT_TP2_OFFSET,
    NOTIONAL_VALUE, MAX_RISK_USDT, MIN_RR_RATIO
)
from btc_bot.logger import log
import math


# ── Descarga de datos históricos ──────────────────────────────────────────────

def fetch_historical_data(days: int = 90) -> pd.DataFrame:
    """Descarga 'days' días de velas 1H desde el exchange público (sin auth)."""
    exchange = getattr(ccxt, EXCHANGE_NAME)({
        "enableRateLimit": True,
        "options": {"defaultType": "future"},
    })
    limit = days * 24 + 72    # +72 para warm-up de niveles
    since_ms = int(
        (datetime.now(timezone.utc).timestamp() - days * 86400) * 1000)
    raw = exchange.fetch_ohlcv(
        SYMBOL, TIMEFRAME_1H, since=since_ms, limit=limit)
    df = pd.DataFrame(
        raw, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df.set_index("ts", inplace=True)
    log.info(f"Datos descargados: {len(df)} velas 1H ({days} días)")
    return df.astype(float)


# ── Lógica de simulación ──────────────────────────────────────────────────────

def run_backtest(days: int = 90):
    """
    Simula la estrategia sobre datos históricos:
    - Itera sobre cada vela con ventana deslizante de 72 velas
    - Detecta señales de breakout LONG y SHORT
    - Calcula resultado de cada trade (hit TP1, TP2 o SL en velas siguientes)
    """
    df = fetch_historical_data(days)
    trades = []
    i = 72  # Inicio con warm-up de 72 velas

    while i < len(df) - 1:
        window = df.iloc[i-72:i]
        candle = df.iloc[i]

        # ── Calcular niveles del día ──────────────────────────────────────
        last_24 = window.iloc[-24:]
        last_48 = window.iloc[-48:-24]
        last_72 = window.iloc[-72:-48]

        resistance_1 = last_24["high"].max()
        support_1 = last_24["low"].min()
        resistance_2 = last_48["high"].max()
        tp2_long = last_72["high"].max()
        tp1_short = math.floor((support_1 - SHORT_TP1_OFFSET) / 200) * 200
        tp2_short = support_1 - (SHORT_TP2_OFFSET)

        prev_close = window.iloc[-1]["close"]
        current = candle["close"]

        signal = None

        # ── Detectar LONG ────────────────────────────────────────────────
        if (prev_close > resistance_1 and
                current > resistance_1 - LONG_PULLBACK_MAX):
            entry = resistance_1 - LONG_ENTRY_OFFSET
            sl = resistance_1 - LONG_SL_OFFSET
            tp1 = resistance_2
            tp2 = tp2_long
            rr = (tp1 - entry) / (entry - sl) if (entry - sl) > 0 else 0
            if rr >= MIN_RR_RATIO:
                signal = {"side": "buy", "entry": entry,
                          "sl": sl, "tp1": tp1, "tp2": tp2}

        # ── Detectar SHORT ───────────────────────────────────────────────
        elif (prev_close < support_1 and current < support_1):
            entry = support_1 + SHORT_ENTRY_OFFSET
            sl = support_1 + SHORT_SL_OFFSET
            tp1 = tp1_short
            tp2 = tp2_short
            rr = (entry - tp1) / (sl - entry) if (sl - entry) > 0 else 0
            if rr >= MIN_RR_RATIO:
                signal = {"side": "sell", "entry": entry,
                          "sl": sl, "tp1": tp1, "tp2": tp2}

        # ── Simular resultado del trade ───────────────────────────────────
        if signal:
            result = _simulate_trade(df, i, signal)
            trades.append(result)
            # Saltar velas consumidas por el trade
            i += result.get("bars_held", 1)
        else:
            i += 1

    # ── Reporte de resultados ─────────────────────────────────────────────
    _print_report(trades)
    return trades


def _simulate_trade(df: pd.DataFrame, entry_idx: int, signal: dict) -> dict:
    """
    Busca en velas futuras si se toca TP1, TP2 o SL primero.
    Retorna un dict con PnL estimado en USDT.
    """
    entry = signal["entry"]
    sl = signal["sl"]
    tp1 = signal["tp1"]
    tp2 = signal["tp2"]
    side = signal["side"]
    qty = NOTIONAL_VALUE / entry

    for j in range(entry_idx + 1, min(entry_idx + 48, len(df))):
        h = df.iloc[j]["high"]
        l = df.iloc[j]["low"]

        if side == "buy":
            if l <= sl:
                pnl = qty * (sl - entry)
                return {**signal, "outcome": "SL",
                        "pnl": round(pnl, 2), "bars_held": j - entry_idx}
            if h >= tp1:
                # Cerrar 50% en TP1 + SL a breakeven para resto
                pnl_partial = (qty * 0.5) * (tp1 - entry)
                # Buscar TP2 o breakeven en el resto
                for k in range(j, min(j + 48, len(df))):
                    hk = df.iloc[k]["high"]
                    lk = df.iloc[k]["low"]
                    if lk <= entry:  # SL breakeven
                        pnl_total = pnl_partial
                        return {**signal, "outcome": "TP1+BE",
                                "pnl": round(pnl_total, 2),
                                "bars_held": k - entry_idx}
                    if hk >= tp2:
                        pnl_total = pnl_partial + (qty * 0.5) * (tp2 - entry)
                        return {**signal, "outcome": "TP1+TP2",
                                "pnl": round(pnl_total, 2),
                                "bars_held": k - entry_idx}
                return {**signal, "outcome": "TP1_only",
                        "pnl": round(pnl_partial, 2), "bars_held": 48}
        else:  # SHORT
            if h >= sl:
                pnl = qty * (entry - sl)
                return {**signal, "outcome": "SL",
                        "pnl": round(pnl, 2), "bars_held": j - entry_idx}
            if l <= tp1:
                pnl_partial = (qty * 0.5) * (entry - tp1)
                for k in range(j, min(j + 48, len(df))):
                    hk = df.iloc[k]["high"]
                    lk = df.iloc[k]["low"]
                    if hk >= entry:
                        pnl_total = pnl_partial
                        return {**signal, "outcome": "TP1+BE",
                                "pnl": round(pnl_total, 2),
                                "bars_held": k - entry_idx}
                    if lk <= tp2:
                        pnl_total = pnl_partial + (qty * 0.5) * (entry - tp2)
                        return {**signal, "outcome": "TP1+TP2",
                                "pnl": round(pnl_total, 2),
                                "bars_held": k - entry_idx}
                return {**signal, "outcome": "TP1_only",
                        "pnl": round(pnl_partial, 2), "bars_held": 48}

    return {**signal, "outcome": "TIMEOUT", "pnl": 0.0, "bars_held": 48}


def _print_report(trades: list):
    """Imprime resumen estadístico del backtest."""
    if not trades:
        print("No se detectaron señales en el período.")
        return

    df = pd.DataFrame(trades)
    wins = df[df["pnl"] > 0]
    losses = df[df["pnl"] <= 0]
    total_pnl = df["pnl"].sum()
    winrate = len(wins) / len(df) * 100 if len(df) > 0 else 0

    print("\n" + "="*50)
    print("       REPORTE DE BACKTEST — BTC BOT")
    print("="*50)
    print(f"  Total trades    : {len(df)}")
    print(f"  Ganadores       : {len(wins)} ({winrate:.1f}%)")
    print(f"  Perdedores      : {len(losses)}")
    print(f"  PnL Total       : {total_pnl:.2f} USDT")
    print(f"  Avg PnL/trade   : {df['pnl'].mean():.2f} USDT")
    print(f"  Max ganancia    : {df['pnl'].max():.2f} USDT")
    print(f"  Max pérdida     : {df['pnl'].min():.2f} USDT")
    print(f"  Longs           : {len(df[df['side']=='buy'])}")
    print(f"  Shorts          : {len(df[df['side']=='sell'])}")
    print("-"*50)
    print(df.groupby("outcome")["pnl"].agg(["count", "sum", "mean"]).round(2))
    print("="*50)


if __name__ == "__main__":
    run_backtest(days=90)

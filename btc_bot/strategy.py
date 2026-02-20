"""
strategy.py — Lógica de la estrategia Breakout Condicional
Calcula niveles dinámicos de resistencia/soporte y genera señales
"""

import pandas as pd
import math
from typing import Optional, Tuple
from btc_bot.config import (
    TIMEFRAME_1H, TIMEFRAME_15M,
    LONG_ENTRY_OFFSET, LONG_SL_OFFSET, LONG_PULLBACK_MAX,
    SHORT_ENTRY_OFFSET, SHORT_SL_OFFSET, SHORT_TP1_OFFSET, SHORT_TP2_OFFSET
)
from btc_bot.logger import log


# ── Utilidades ────────────────────────────────────────────────────────────────

def ohlcv_to_df(raw: list) -> pd.DataFrame:
    """Convierte lista ccxt [ts, open, high, low, close, vol] a DataFrame."""
    df = pd.DataFrame(
        raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)
    return df.astype(float)


def nearest_round_level_below(price: float, step: float = 200.0) -> float:
    """
    Calcula el nivel redondo más cercano por debajo de 'price'.
    Por defecto trabaja en múltiplos de 200 (p.ej. 64200, 64000...).
    """
    return math.floor(price / step) * step


# ── Clase principal de estrategia ─────────────────────────────────────────────

class BreakoutStrategy:
    """
    Implementa la lógica de Breakout Condicional para BTCUSDT:
    - Calcula niveles dinámicos diarios (rango 24H)
    - Detecta breakout de resistencia → señal LONG
    - Detecta ruptura de soporte → señal SHORT
    - Aplica regla de no-trade cuando el precio está en rango
    """

    def __init__(self, exchange_client):
        self.client = exchange_client
        self.levels = {}  # Almacena niveles calculados

    # ── PASO 1: Calcular rango diario dinámico ────────────────────────────────

    def calculate_levels(self) -> dict:
        """
        Obtiene las últimas 72 velas de 1H y calcula:
        - resistance_1 : máximo de las últimas 24H
        - support_1    : mínimo de las últimas 24H
        - resistance_2 : máximo de las últimas 48H (día anterior)
        - tp2_long     : máximo de las últimas 72H (hace 2 días)
        - tp1_short    : nivel redondo más cercano debajo de support_1
        - tp2_short    : support_1 - SHORT_TP2_OFFSET
        """
        raw_1h = self.client.fetch_ohlcv(TIMEFRAME_1H, limit=75)
        df = ohlcv_to_df(raw_1h)

        if len(df) < 48:
            raise ValueError(
                "Datos insuficientes para calcular niveles (< 48 velas 1H)")

        # Últimas 24 velas = "día actual"
        last_24 = df.iloc[-24:]
        last_48 = df.iloc[-48:-24]   # Velas 25-48 = "día anterior"
        last_72 = df.iloc[-72:-48]   # Velas 49-72 = "hace 2 días"

        resistance_1 = float(last_24["high"].max())
        support_1 = float(last_24["low"].min())

        resistance_2 = float(last_48["high"].max()) if len(
            last_48) >= 1 else resistance_1
        tp2_long = float(last_72["high"].max()) if len(
            last_72) >= 1 else resistance_2

        tp1_short = nearest_round_level_below(
            support_1 - SHORT_TP1_OFFSET, step=200)
        tp2_short = support_1 - SHORT_TP2_OFFSET

        self.levels = {
            "resistance_1": resistance_1,
            "support_1":    support_1,
            "resistance_2": resistance_2,
            "tp2_long":     tp2_long,
            "tp1_short":    tp1_short,
            "tp2_short":    tp2_short,
            "last_close_1h": float(df.iloc[-1]["close"]),
            "df_1h":        df,
        }

        log.info(
            f"Niveles calculados → "
            f"Resist1: {resistance_1:.2f} | Support1: {support_1:.2f} | "
            f"Resist2: {resistance_2:.2f} | TP2_Long: {tp2_long:.2f} | "
            f"TP1_Short: {tp1_short:.2f} | TP2_Short: {tp2_short:.2f}"
        )
        return self.levels

    # ── PASO 2: Regla de no-trade ─────────────────────────────────────────────

    def is_in_chop_zone(self, current_price: float) -> bool:
        """
        Retorna True si el precio está DENTRO del rango [support_1, resistance_1].
        En ese caso no se debe abrir ninguna posición.
        """
        s = self.levels["support_1"]
        r = self.levels["resistance_1"]
        if s <= current_price <= r:
            log.info(f"🔶 CHOP ZONE — Precio {current_price:.2f} en rango "
                     f"[{s:.2f} – {r:.2f}]. Sin operación.")
            return True
        return False

    # ── PASO 3: Señal LONG ────────────────────────────────────────────────────

    def check_long_signal(self, current_price: float) -> Optional[dict]:
        """
        Evalúa la condición de breakout alcista:
        1. La última vela 1H cerró POR ENCIMA de resistance_1
        2. El precio actual no cayó más de LONG_PULLBACK_MAX por debajo de resistance_1

        Retorna dict con niveles de la operación o None.
        """
        r1 = self.levels["resistance_1"]
        r2 = self.levels["resistance_2"]
        tp2 = self.levels["tp2_long"]
        last_close = self.levels["last_close_1h"]

        # Condición 1: vela 1H cerró sobre la resistencia
        if last_close <= r1:
            return None

        # Condición 2: el precio no ha retrocedido demasiado
        if current_price < (r1 - LONG_PULLBACK_MAX):
            log.debug(f"LONG: pullback excesivo. Precio {current_price:.2f} < "
                      f"resist - {LONG_PULLBACK_MAX} = {r1 - LONG_PULLBACK_MAX:.2f}")
            return None

        entry = round(r1 - LONG_ENTRY_OFFSET, 2)
        sl = round(r1 - LONG_SL_OFFSET, 2)
        tp1 = round(r2, 2)
        tp2_val = round(tp2, 2)

        log.info(
            f"📈 SEÑAL LONG detectada → "
            f"Entry: {entry:.2f} | SL: {sl:.2f} | "
            f"TP1: {tp1:.2f} | TP2: {tp2_val:.2f}"
        )

        return {
            "side":   "buy",
            "entry":  entry,
            "sl":     sl,
            "tp1":    tp1,
            "tp2":    tp2_val,
            "reason": f"Breakout LONG sobre resist {r1:.2f}",
        }

    # ── PASO 4: Señal SHORT ───────────────────────────────────────────────────

    def check_short_signal(self, current_price: float) -> Optional[dict]:
        """
        Evalúa la condición de ruptura bajista:
        1. La última vela 1H cerró POR DEBAJO de support_1
        2. Confirmación con vela 15M también debajo de support_1
        3. El precio actual sigue por debajo del soporte

        Retorna dict con niveles de la operación o None.
        """
        s1 = self.levels["support_1"]
        tp1 = self.levels["tp1_short"]
        tp2 = self.levels["tp2_short"]
        last_close = self.levels["last_close_1h"]

        # Condición 1: vela 1H cerró bajo el soporte
        if last_close >= s1:
            return None

        # Condición 2: precio actual todavía bajo el soporte
        if current_price >= s1:
            log.debug(f"SHORT: precio recuperó soporte {s1:.2f}. Sin señal.")
            return None

        # Condición 3: confirmación de vela 15M
        raw_15m = self.client.fetch_ohlcv(TIMEFRAME_15M, limit=3)
        df_15m = ohlcv_to_df(raw_15m)
        close_15m = float(df_15m.iloc[-1]["close"])

        if close_15m >= s1:
            log.debug(f"SHORT: vela 15M no confirma ruptura "
                      f"(close 15M = {close_15m:.2f} >= soporte {s1:.2f})")
            return None

        entry = round(s1 + SHORT_ENTRY_OFFSET, 2)
        sl = round(s1 + SHORT_SL_OFFSET, 2)

        log.info(
            f"📉 SEÑAL SHORT detectada → "
            f"Entry: {entry:.2f} | SL: {sl:.2f} | "
            f"TP1: {tp1:.2f} | TP2: {tp2:.2f}"
        )

        return {
            "side":   "sell",
            "entry":  entry,
            "sl":     sl,
            "tp1":    round(tp1, 2),
            "tp2":    round(tp2, 2),
            "reason": f"Ruptura SHORT bajo soporte {s1:.2f}",
        }

    # ── Evaluación completa ───────────────────────────────────────────────────

    def evaluate(self, current_price: float) -> Tuple[Optional[dict], str]:
        """
        Ejecuta toda la lógica de la estrategia en orden:
        1. Calcular niveles
        2. Verificar chop zone
        3. Buscar señal LONG
        4. Buscar señal SHORT

        Retorna (signal_dict | None, motivo_str)
        """
        self.calculate_levels()

        if self.is_in_chop_zone(current_price):
            return None, "CHOP_ZONE"

        signal = self.check_long_signal(current_price)
        if signal:
            return signal, "LONG_BREAKOUT"

        signal = self.check_short_signal(current_price)
        if signal:
            return signal, "SHORT_BREAKOUT"

        return None, "NO_SIGNAL"

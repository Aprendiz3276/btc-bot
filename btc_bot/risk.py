"""
risk.py — Gestión de riesgo: tamaño de posición, R:R y validación
"""

from btc_bot.config import (
    NOTIONAL_VALUE, MAX_RISK_USDT, MIN_RR_RATIO, LEVERAGE
)
from btc_bot.logger import log


class RiskManager:
    """
    Calcula y valida todos los parámetros de riesgo antes de abrir una posición:
    - Tamaño de posición dinámico (cantidad BTC)
    - Riesgo real en USDT
    - Relación Riesgo:Recompensa (R:R)
    """

    def calculate_position_size(self, entry_price: float) -> float:
        """
        Calcula la cantidad de BTC a operar basado en:
        nocional = margen * apalancamiento (definido en config)
        cantidad_BTC = nocional / precio_entrada
        """
        qty = NOTIONAL_VALUE / entry_price
        log.debug(f"Position size → Nocional: {NOTIONAL_VALUE} USDT | "
                  f"Entry: {entry_price:.2f} | Qty: {qty:.6f} BTC")
        return qty

    def calculate_real_risk(self, qty_btc: float,
                            entry: float, stop_loss: float,
                            side: str = "buy") -> float:
        """
        Riesgo real en USDT = qty_BTC * |entry - stop_loss|
        Para LONG: entry > SL
        Para SHORT: SL > entry
        """
        if side == "buy":
            risk = qty_btc * (entry - stop_loss)
        else:
            risk = qty_btc * (stop_loss - entry)
        log.debug(f"Riesgo real: {risk:.2f} USDT")
        return risk

    def calculate_rr(self, entry: float, sl: float,
                     tp: float, side: str = "buy") -> float:
        """
        R:R = reward / risk
        LONG  → (TP - entry) / (entry - SL)
        SHORT → (entry - TP) / (SL - entry)
        """
        if side == "buy":
            reward = tp - entry
            risk = entry - sl
        else:
            reward = entry - tp
            risk = sl - entry

        if risk <= 0:
            return 0.0

        rr = reward / risk
        log.debug(
            f"R:R calculado = {rr:.2f} (reward={reward:.2f}, risk={risk:.2f})")
        return rr

    def validate_trade(self, signal: dict) -> tuple:
        """
        Valida si una señal cumple los requisitos de riesgo:
        1. R:R >= MIN_RR_RATIO (usando TP1 como referencia conservadora)
        2. Riesgo real <= MAX_RISK_USDT

        Retorna (valid: bool, qty_btc: float, motivo: str)
        """
        entry = signal["entry"]
        sl = signal["sl"]
        tp1 = signal["tp1"]
        side = signal["side"]

        # ── 1. Calcular R:R ────────────────────────────────────────────────
        rr = self.calculate_rr(entry, sl, tp1, side)
        if rr < MIN_RR_RATIO:
            msg = (f"[REJECT] R:R insuficiente: {rr:.2f} < {MIN_RR_RATIO} requerido. "
                   f"Operación rechazada.")
            log.warning(msg)
            return False, 0.0, msg

        # ── 2. Calcular tamaño y riesgo real ──────────────────────────────
        qty = self.calculate_position_size(entry)
        real_risk = self.calculate_real_risk(qty, entry, sl, side)

        if real_risk > MAX_RISK_USDT:
            msg = (f"[REJECT] Riesgo real {real_risk:.2f} USDT > "
                   f"máximo permitido {MAX_RISK_USDT} USDT. "
                   f"Operación rechazada.")
            log.warning(msg)
            return False, 0.0, msg

        msg = (f"✅ Validación OK → R:R: {rr:.2f} | "
               f"Qty: {qty:.6f} BTC | Riesgo: {real_risk:.2f} USDT")
        log.info(msg)
        return True, qty, msg

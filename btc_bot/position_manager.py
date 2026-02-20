"""
position_manager.py — Gestión de posición abierta
Maneja TP parcial, breakeven, trailing stop y cierre por SL
"""

import json
import os
from btc_bot.config import (
    STATE_FILE, TP1_CLOSE_PCT,
    TRAILING_ACTIVATION_PCT, TRAILING_OFFSET_PCT
)
from btc_bot.logger import log


class PositionManager:
    """
    Monitorea cada 5 minutos una posición abierta y ejecuta:
    - Cierre parcial (50%) al tocar TP1
    - Mover SL a breakeven tras TP1
    - Cierre total al tocar TP2
    - Cierre de emergencia al tocar SL
    - Trailing stop opcional tras superar TP1 en +0.5%
    """

    def __init__(self, exchange_client, notifier=None):
        self.client = exchange_client
        self.notifier = notifier
        self.state = self._load_state()

    # ── Estado persistente ────────────────────────────────────────────────

    def _load_state(self) -> dict:
        """Carga el estado desde state.json o retorna estado vacío."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        return {
            "position_open": False,
            "side": None,
            "entry_price": None,
            "qty_total": None,
            "qty_remaining": None,
            "sl": None,
            "tp1": None,
            "tp2": None,
            "tp1_hit": False,
            "breakeven_active": False,
            "trailing_active": False,
            "trailing_peak": None,
            "levels": {},
        }

    def save_state(self):
        """Guarda estado actual en state.json (excluye DataFrames)."""
        state_to_save = {k: v for k, v in self.state.items() if k != "df_1h"}
        with open(STATE_FILE, "w") as f:
            json.dump(state_to_save, f, indent=2)

    def open_position(self, signal: dict, qty: float, order: dict):
        """Registra una posición recién abierta en el estado."""
        self.state.update({
            "position_open":    True,
            "side":             signal["side"],
            "entry_price":      signal["entry"],
            "qty_total":        qty,
            "qty_remaining":    qty,
            "sl":               signal["sl"],
            "tp1":              signal["tp1"],
            "tp2":              signal["tp2"],
            "tp1_hit":          False,
            "breakeven_active": False,
            "trailing_active":  False,
            "trailing_peak":    None,
            "order_id":         order.get("id"),
        })
        self.save_state()
        log.info(f"Posición registrada: {signal['side'].upper()} | "
                 f"Entry: {signal['entry']:.2f} | Qty: {qty:.6f} BTC | "
                 f"SL: {signal['sl']:.2f} | TP1: {signal['tp1']:.2f} | "
                 f"TP2: {signal['tp2']:.2f}")

    def has_open_position(self) -> bool:
        return self.state.get("position_open", False)

    # ── Monitor principal ─────────────────────────────────────────────────

    def monitor(self, current_price: float):
        """
        Lógica de monitoreo ejecutada cada 5 minutos.
        Evalúa SL, TP1, TP2 y trailing en orden de prioridad.
        """
        if not self.has_open_position():
            return

        side = self.state["side"]
        entry = self.state["entry_price"]
        sl = self.state["sl"]
        tp1 = self.state["tp1"]
        tp2 = self.state["tp2"]
        qty_rem = self.state["qty_remaining"]
        tp1_hit = self.state["tp1_hit"]

        log.debug(f"Monitor [{side.upper()}] | Precio: {current_price:.2f} | "
                  f"SL: {sl:.2f} | TP1: {tp1:.2f} | TP2: {tp2:.2f}")

        # ── 1. Verificar Stop Loss ────────────────────────────────────────
        sl_triggered = (
            (side == "buy" and current_price <= sl) or
            (side == "sell" and current_price >= sl)
        )
        if sl_triggered:
            self._execute_stop_loss(current_price, qty_rem, side)
            return

        # ── 2. Verificar TP2 (cierre total) ──────────────────────────────
        tp2_triggered = (
            (side == "buy" and current_price >= tp2) or
            (side == "sell" and current_price <= tp2)
        )
        if tp2_triggered and tp1_hit:
            self._execute_tp2(current_price, qty_rem, side)
            return

        # ── 3. Verificar TP1 (cierre parcial 50%) ────────────────────────
        tp1_triggered = (
            (side == "buy" and current_price >= tp1) or
            (side == "sell" and current_price <= tp1)
        )
        if tp1_triggered and not tp1_hit:
            self._execute_tp1(current_price, side, entry)
            return

        # ── 4. Trailing stop (solo si TP1 ya fue alcanzado) ──────────────
        if tp1_hit and self.state.get("trailing_active"):
            self._update_trailing_stop(current_price, side)

    # ── Acciones de cierre ────────────────────────────────────────────────

    def _execute_stop_loss(self, price: float, qty: float, side: str):
        """Cierra posición completa con orden market por SL."""
        close_side = "sell" if side == "buy" else "buy"
        try:
            params = {"reduceOnly": True}
            self.client.create_market_order(close_side, qty, params)
            msg = (f"🛑 STOP LOSS activado @ {price:.2f} | "
                   f"Cerrado {qty:.6f} BTC")
            log.warning(msg)
            if self.notifier:
                self.notifier.send(msg)
        except Exception as e:
            log.error(f"Error al ejecutar SL: {e}")
        finally:
            self._clear_position()

    def _execute_tp1(self, price: float, side: str, entry: float):
        """Cierra 50% de la posición y mueve SL a breakeven."""
        qty_total = self.state["qty_total"]
        qty_close = round(qty_total * TP1_CLOSE_PCT, 6)
        close_side = "sell" if side == "buy" else "buy"

        try:
            params = {"reduceOnly": True}
            self.client.create_market_order(close_side, qty_close, params)

            qty_new = round(qty_total - qty_close, 6)
            new_sl = entry  # Breakeven

            self.state["tp1_hit"] = True
            self.state["qty_remaining"] = qty_new
            self.state["sl"] = new_sl
            self.state["breakeven_active"] = True

            # Activar trailing si el precio superó TP1 en +0.5%
            tp1 = self.state["tp1"]
            if side == "buy" and price >= tp1 * (1 + TRAILING_ACTIVATION_PCT):
                self.state["trailing_active"] = True
                self.state["trailing_peak"] = price
                log.info(f"📍 Trailing stop activado. Peak: {price:.2f}")

            self.save_state()

            msg = (f"✅ TP1 alcanzado @ {price:.2f} | "
                   f"Cerrado {qty_close:.6f} BTC (50%) | "
                   f"SL movido a breakeven: {new_sl:.2f}")
            log.info(msg)
            if self.notifier:
                self.notifier.send(msg)

        except Exception as e:
            log.error(f"Error al ejecutar TP1: {e}")

    def _execute_tp2(self, price: float, qty: float, side: str):
        """Cierra el 100% restante de la posición en TP2."""
        close_side = "sell" if side == "buy" else "buy"
        try:
            params = {"reduceOnly": True}
            self.client.create_market_order(close_side, qty, params)
            msg = (f"[TP2] TP2 alcanzado @ {price:.2f} | "
                   f"Cerrado {qty:.6f} BTC (100% restante)")
            log.info(msg)
            if self.notifier:
                self.notifier.send(msg)
        except Exception as e:
            log.error(f"Error al ejecutar TP2: {e}")
        finally:
            self._clear_position()

    def _update_trailing_stop(self, price: float, side: str):
        """Actualiza el trailing stop dinámico."""
        peak = self.state.get("trailing_peak", price)

        if side == "buy":
            if price > peak:
                self.state["trailing_peak"] = price
                new_sl = round(price * (1 - TRAILING_OFFSET_PCT), 2)
                if new_sl > self.state["sl"]:
                    self.state["sl"] = new_sl
                    log.info(f"📈 Trailing SL actualizado: {new_sl:.2f} "
                             f"(precio peak: {price:.2f})")
                    self.save_state()
        else:  # short
            if price < peak:
                self.state["trailing_peak"] = price
                new_sl = round(price * (1 + TRAILING_OFFSET_PCT), 2)
                if new_sl < self.state["sl"]:
                    self.state["sl"] = new_sl
                    log.info(f"📉 Trailing SL actualizado: {new_sl:.2f} "
                             f"(precio peak: {price:.2f})")
                    self.save_state()

    def _clear_position(self):
        """Limpia el estado al cerrar una posición."""
        self.state = {
            "position_open": False,
            "side": None, "entry_price": None,
            "qty_total": None, "qty_remaining": None,
            "sl": None, "tp1": None, "tp2": None,
            "tp1_hit": False, "breakeven_active": False,
            "trailing_active": False, "trailing_peak": None,
        }
        self.save_state()
        log.info("🔄 Estado de posición limpiado.")

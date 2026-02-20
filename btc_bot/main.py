"""
main.py — Loop principal del bot.
Soporta dos modos:
  - python -m btc_bot.main          → loop infinito (VPS)
  - python -m btc_bot.main --once   → un solo ciclo (GitHub Actions)
"""

import sys
import time
import traceback
from btc_bot.config import LOOP_INTERVAL_SECONDS, PAPER_TRADING
from btc_bot.logger import log
from btc_bot.exchange import ExchangeClient
from btc_bot.strategy import BreakoutStrategy
from btc_bot.risk import RiskManager
from btc_bot.position_manager import PositionManager
from btc_bot.notifier import TelegramNotifier


def execute_cycle(client, strategy, risk, pm, notifier):
    """Un ciclo completo del bot — reutilizable en ambos modos."""
    current_price = client.get_current_price()
    log.info("─── Ciclo | BTC: %.2f USDT ───", current_price)

    if pm.has_open_position():
        log.info("📊 Posición activa — monitoreando niveles...")
        pm.monitor(current_price)
    else:
        signal, reason = strategy.evaluate(current_price)

        if reason == "CHOP_ZONE":
            notifier.send(
                f"🔶 Precio en rango — Sin operación\n"
                f"BTC: <b>{current_price:.2f}</b> USDT"
            )
        elif signal:
            notifier.send(
                f"🔍 Señal: <b>{signal['side'].upper()}</b>\n"
                f"Entry: {signal['entry']:.2f} | SL: {signal['sl']:.2f}\n"
                f"TP1: {signal['tp1']:.2f} | TP2: {signal['tp2']:.2f}"
            )
            valid, qty, msg = risk.validate_trade(signal)
            if not valid:
                notifier.send(f"⚠️ Rechazada:\n{msg}")
            else:
                order = client.create_limit_order(
                    side=signal["side"],
                    amount=qty,
                    price=signal["entry"],
                    params={"timeInForce": "GTC"}
                )
                sl_side = "sell" if signal["side"] == "buy" else "buy"
                client.create_stop_market_order(sl_side, qty, signal["sl"])
                pm.open_position(signal, qty, order)
                notifier.send(
                    f"✅ Orden abierta: <b>{signal['side'].upper()}</b>\n"
                    f"Entry: {signal['entry']:.2f} | Qty: {qty:.6f} BTC\n"
                    f"SL: {signal['sl']:.2f} | TP1: {signal['tp1']:.2f}"
                )
        else:
            log.info("💤 Sin señal (%s)", reason)


def run_once():
    """Ejecuta UN solo ciclo — usado por GitHub Actions."""
    log.info("=" * 50)
    log.info("🔁 Ciclo único | Paper: %s", PAPER_TRADING)
    log.info("=" * 50)

    client = ExchangeClient()
    strategy = BreakoutStrategy(client)
    risk = RiskManager()
    notifier = TelegramNotifier()
    pm = PositionManager(client, notifier)

    client.set_leverage()

    try:
        execute_cycle(client, strategy, risk, pm, notifier)
    except Exception as e:
        log.error("Error en ciclo: %s\n%s", str(e), traceback.format_exc())


def run_bot():
    """Loop infinito — usado en VPS."""
    log.info("=" * 50)
    log.info("🚀 Bot iniciado en loop | Paper: %s", PAPER_TRADING)
    log.info("=" * 50)

    client = ExchangeClient()
    strategy = BreakoutStrategy(client)
    risk = RiskManager()
    notifier = TelegramNotifier()
    pm = PositionManager(client, notifier)

    client.set_leverage()
    client.set_position_mode(hedge=False)

    while True:
        cycle_start = time.time()
        try:
            execute_cycle(client, strategy, risk, pm, notifier)
        except KeyboardInterrupt:
            log.info("🛑 Bot detenido.")
            break
        except Exception as e:
            log.error("Error: %s\n%s", str(e), traceback.format_exc())

        elapsed = time.time() - cycle_start
        wait = max(0, LOOP_INTERVAL_SECONDS - elapsed)
        log.info("⏱️ Próximo ciclo en %.0fs...", wait)
        time.sleep(wait)


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_once()
    else:
        run_bot()

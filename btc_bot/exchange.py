"""
exchange.py — Cliente unificado del exchange usando ccxt
Soporta: binanceusdm | bybit | okx
Incluye retry con backoff exponencial y detección de mantenimiento
"""

import os
import time
import ccxt
from btc_bot.config import (
    API_KEY, API_SECRET, API_PASSPHRASE,
    EXCHANGE_NAME, SYMBOL, LEVERAGE,
    MAX_RETRIES, MAINTENANCE_PAUSE_MIN, PAPER_TRADING
)
from btc_bot.logger import log


# Mapeo de nombre → clase ccxt y opciones específicas
EXCHANGE_CONFIG = {
    "binanceusdm": {
        "class": "binanceusdm",
        "options": {"defaultType": "future"},
    },
    "bybit": {
        "class": "bybit",
        "options": {"defaultType": "swap"},
    },
    "okx": {
        "class": "okx",
        "options": {"defaultType": "swap"},
    },
}


class ExchangeClient:
    """
    Wrapper sobre ccxt que encapsula:
    - Conexión y autenticación
    - Configuración de apalancamiento
    - fetch_ohlcv, fetch_ticker, fetch_balance
    - create_order, cancel_order, fetch_open_orders
    - fetch_positions
    - Retry con backoff exponencial
    """

    def __init__(self):
        cfg = EXCHANGE_CONFIG.get(EXCHANGE_NAME)
        if cfg is None:
            raise ValueError(f"Exchange no soportado: {EXCHANGE_NAME}. "
                             f"Usa: {list(EXCHANGE_CONFIG.keys())}")

        exchange_class = getattr(ccxt, cfg["class"])

        init_params = {
            "apiKey": API_KEY,
            "secret": API_SECRET,
            "enableRateLimit": True,
            "options": cfg["options"],
        }

        # OKX requiere passphrase
        if EXCHANGE_NAME == "okx" and API_PASSPHRASE:
            init_params["password"] = API_PASSPHRASE

        self.exchange = exchange_class(init_params)

        # ── OKX DEMO: header obligatorio para demo trading ─────────────
        # OKX requiere: x-simulated-trading: 1 para llamadas de demo
        if EXCHANGE_NAME == "okx" and os.getenv("OKX_DEMO", "false").lower() == "true":
            self.exchange.headers = self.exchange.headers or {}
            self.exchange.headers["x-simulated-trading"] = "1"
            log.info("OKX_DEMO activo → header x-simulated-trading=1 habilitado")

        if PAPER_TRADING:
            # Activar sandbox si el exchange lo soporta
            if hasattr(self.exchange, "set_sandbox_mode"):
                self.exchange.set_sandbox_mode(True)
                log.info("[PAPER] PAPER TRADING activo — modo sandbox habilitado")
            else:
                log.warning("[PAPER] PAPER TRADING: exchange sin sandbox, "
                            "órdenes serán simuladas localmente")

        log.info("Exchange inicializado: %s | Symbol: %s | Leverage: %sx",
                 EXCHANGE_NAME, SYMBOL, LEVERAGE)

    # ── Retry helper ────────────────────────────────────────────────────────
    def _call_with_retry(self, func, *args, **kwargs):
        """Ejecuta func con hasta MAX_RETRIES intentos y backoff exponencial."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except ccxt.OnMaintenance:
                log.warning("Exchange en mantenimiento. "
                            "Pausando %s min...", MAINTENANCE_PAUSE_MIN)
                time.sleep(MAINTENANCE_PAUSE_MIN * 60)
                # No contar como intento fallido
            except (ccxt.NetworkError, ccxt.RequestTimeout) as e:
                wait = 2 ** attempt   # 2, 4, 8 segundos
                log.warning("Error de red (intento %s/%s): %s. Reintentando en %ss...",
                            attempt, MAX_RETRIES, str(e), wait)
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(wait)
            except ccxt.ExchangeError as e:
                log.error("Error del exchange: %s", str(e))
                raise

    # ── Datos de mercado ────────────────────────────────────────────────────
    def fetch_ohlcv(self, timeframe: str, limit: int = 100) -> list:
        """Descarga velas OHLCV. Retorna lista de [ts, open, high, low, close, vol]."""
        return self._call_with_retry(
            self.exchange.fetch_ohlcv,
            SYMBOL, timeframe, limit=limit
        )

    def fetch_ticker(self) -> dict:
        """Precio actual y datos del ticker."""
        return self._call_with_retry(self.exchange.fetch_ticker, SYMBOL)

    def fetch_balance(self) -> dict:
        return self._call_with_retry(self.exchange.fetch_balance)

    def fetch_positions(self) -> list:
        """Retorna posiciones abiertas del símbolo actual."""
        positions = self._call_with_retry(
            self.exchange.fetch_positions, [SYMBOL]
        )
        # Filtrar posición activa (contratos > 0)
        return [p for p in positions
                if float(p.get("contracts", 0) or 0) > 0]

    def fetch_open_orders(self) -> list:
        return self._call_with_retry(
            self.exchange.fetch_open_orders, SYMBOL
        )

    # ── Configuración del contrato ──────────────────────────────────────────
    def set_leverage(self):
        """Configura el apalancamiento para el símbolo."""
        try:
            self._call_with_retry(
                self.exchange.set_leverage,
                LEVERAGE, SYMBOL
            )
            log.info("Apalancamiento configurado: %sx en %s", LEVERAGE, SYMBOL)
        except ccxt.ExchangeError as e:
            # Algunos exchanges no permiten cambiar apalancamiento vía API
            log.warning("No se pudo configurar apalancamiento: %s", str(e))

    def set_position_mode(self, hedge: bool = False):
        """Configura hedge mode (True) u one-way mode (False). Solo Binance."""
        if EXCHANGE_NAME == "binanceusdm":
            try:
                self._call_with_retry(
                    self.exchange.fapiPrivatePostPositionSideDual,
                    {"dualSidePosition": "true" if hedge else "false"}
                )
                mode = "hedge" if hedge else "one-way"
                log.info("Modo de posición configurado: %s", mode)
            except ccxt.ExchangeError as e:
                log.warning(
                    "set_position_mode: %s (puede ya estar configurado)", str(e))

    # ── Gestión de órdenes ──────────────────────────────────────────────────
    def create_limit_order(self, side: str, amount: float,
                           price: float, params: dict = None) -> dict:
        """
        Crea orden limit.
        side: 'buy' | 'sell'
        amount: cantidad en BTC
        price: precio límite en USDT
        """
        params = params or {}
        if PAPER_TRADING and not hasattr(self.exchange, "set_sandbox_mode"):
            log.info("[PAPER] Orden LIMIT %s | "
                     "Qty: %.6f BTC @ %.2f USDT | params: %s",
                     side.upper(), amount, price, params)
            return {"id": "PAPER_ORDER", "side": side,
                    "amount": amount, "price": price, "status": "open"}

        return self._call_with_retry(
            self.exchange.create_limit_order,
            SYMBOL, side, amount, price, params
        )

    def create_market_order(self, side: str, amount: float,
                            params: dict = None) -> dict:
        """Crea orden market para cierre de posición inmediato."""
        params = params or {}
        if PAPER_TRADING and not hasattr(self.exchange, "set_sandbox_mode"):
            ticker = self.fetch_ticker()
            price = ticker["last"]
            log.info("[PAPER] Orden MARKET %s | "
                     "Qty: %.6f BTC @ ~%.2f USDT",
                     side.upper(), amount, price)
            return {"id": "PAPER_MARKET", "side": side,
                    "amount": amount, "price": price, "status": "closed"}

        return self._call_with_retry(
            self.exchange.create_market_order,
            SYMBOL, side, amount, params
        )

    def create_stop_market_order(self, side: str, amount: float,
                                 stop_price: float) -> dict:
        """Crea orden stop-market para stop loss."""
        if PAPER_TRADING and not hasattr(self.exchange, "set_sandbox_mode"):
            log.info("[PAPER] Stop-Market %s @ %.2f", side.upper(), stop_price)
            return {"id": "PAPER_STOP", "stopPrice": stop_price}

        # Params diferenciados por exchange
        if EXCHANGE_NAME == "binanceusdm":
            params = {"stopPrice": stop_price, "type": "STOP_MARKET",
                      "reduceOnly": True}
            return self._call_with_retry(
                self.exchange.create_order,
                SYMBOL, "STOP_MARKET", side, amount, None, params
            )
        elif EXCHANGE_NAME == "bybit":
            params = {"triggerPrice": stop_price, "reduceOnly": True}
            return self._call_with_retry(
                self.exchange.create_order,
                SYMBOL, "market", side, amount, None, params
            )
        else:  # okx y otros
            params = {"triggerPrice": stop_price, "reduceOnly": True}
            return self._call_with_retry(
                self.exchange.create_order,
                SYMBOL, "market", side, amount, None, params
            )

    def cancel_order(self, order_id: str) -> dict:
        """Cancela una orden por ID."""
        return self._call_with_retry(
            self.exchange.cancel_order, order_id, SYMBOL
        )

    def cancel_all_orders(self):
        """Cancela todas las órdenes abiertas del símbolo."""
        open_orders = self.fetch_open_orders()
        for order in open_orders:
            try:
                self.cancel_order(order["id"])
                log.info("Orden cancelada: %s", order['id'])
            except ccxt.ExchangeError as e:
                log.warning("No se pudo cancelar orden %s: %s",
                            order['id'], str(e))

    def get_current_price(self) -> float:
        """Devuelve el último precio del ticker."""
        ticker = self.fetch_ticker()
        return float(ticker["last"])

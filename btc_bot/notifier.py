"""
notifier.py — Notificaciones por Telegram
"""

import requests
from btc_bot.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from btc_bot.logger import log


class TelegramNotifier:
    """Envía mensajes al chat de Telegram configurado."""

    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)
        if not self.enabled:
            log.warning(
                "Telegram no configurado — notificaciones desactivadas.")

    def send(self, message: str):
        """Envía un mensaje. Falla silenciosamente si Telegram no está configurado."""
        if not self.enabled:
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text":    f"[BOT] BTC Bot\n\n{message}",
            "parse_mode": "HTML",
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if not resp.ok:
                log.warning(f"Telegram error: {resp.text}")
        except Exception as e:
            log.warning(f"Telegram no disponible: {e}")

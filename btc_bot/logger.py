"""
logger.py — Sistema de logging con timezone Colombia (UTC-5)
Salida simultánea a consola y archivo bot.log con rotación diaria
"""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import pytz
from btc_bot.config import LOG_FILE, TIMEZONE

# Zona horaria Colombia
TZ_BOGOTA = pytz.timezone(TIMEZONE)


class BogotaFormatter(logging.Formatter):
    """Formateador que usa la hora local de Colombia (UTC-5) en todos los registros."""

    converter = None  # Sobreescribimos con método propio

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=TZ_BOGOTA)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def get_logger(name: str = "btc_bot") -> logging.Logger:
    """
    Devuelve un logger configurado con:
    - Handler de consola (nivel INFO)
    - Handler de archivo con rotación diaria (nivel DEBUG)
    """
    logger = logging.getLogger(name)

    # Evitar duplicar handlers si se llama varias veces
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = BogotaFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(module)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S COT"
    )

    # ── Consola ────────────────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    # ── Archivo rotatorio (nuevos archivos cada día a medianoche Colombia) ─
    file_handler = TimedRotatingFileHandler(
        filename=LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Instancia global para uso directo: from btc_bot.logger import log
log = get_logger("btc_bot")

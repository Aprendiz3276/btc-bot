# BTC Bot

Trading bot automatizado para Bitcoin usando CCXT.

## Características

- ✅ Soporte multi-exchange (Binance, Bybit, OKX)
- ✅ Estrategia Breakout con niveles dinámicos
- ✅ Gestión automática de riesgo
- ✅ Notificaciones por Telegram
- ✅ Modo Paper Trading y Demo
- ✅ Retry automático con backoff exponencial
- ✅ Despliegue en GitHub Actions

## Quick Start

```bash
git clone https://github.com/Aprendiz3276/btc-bot
cd btc-bot
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m btc_bot.main --once
```

## Documentación

Ver la [guía de setup](setup.md) para configuración completa.

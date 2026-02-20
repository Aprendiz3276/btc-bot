# Configuración

## Variables de Entorno

### Exchange
- `EXCHANGE_NAME`: okx | binanceusdm | bybit
- `API_KEY`: Tu API key
- `API_SECRET`: Tu API secret
- `API_PASSPHRASE`: Solo para OKX

### Trading
- `SYMBOL`: Par a operar (ej: BTC/USDT:USDT)
- `CAPITAL_TOTAL`: Capital disponible en USDT
- `MARGIN_PCT`: Porcentaje para margen (0.20 = 20%)
- `LEVERAGE`: Apalancamiento (10x, 20x, etc)
- `MAX_RISK_USDT`: Riesgo máximo por operación

### Estrategia Breakout
- `LONG_ENTRY_OFFSET`: Offset para entry LONG
- `LONG_SL_OFFSET`: Offset para SL LONG
- `LONG_PULLBACK_MAX`: Pullback máximo aceptado
- `SHORT_ENTRY_OFFSET`: Offset para entry SHORT
- `SHORT_SL_OFFSET`: Offset para SL SHORT
- `SHORT_TP1_OFFSET`: TP1 SHORT
- `SHORT_TP2_OFFSET`: TP2 SHORT

### Modos
- `PAPER_TRADING`: true | false (paper trading)
- `OKX_DEMO`: true | false (modo demo OKX)

### Notificaciones
- `TELEGRAM_TOKEN`: Token del bot de Telegram
- `TELEGRAM_CHAT_ID`: ID del chat para notificaciones

### Sistema
- `LOOP_INTERVAL_SECONDS`: Intervalo entre ciclos (300 = 5 min)

## Archivo .env

```env
EXCHANGE_NAME=okx
API_KEY=tu_api_key
API_SECRET=tu_api_secret
API_PASSPHRASE=tu_passphrase
SYMBOL=BTC/USDT:USDT
CAPITAL_TOTAL=500
MARGIN_PCT=0.20
LEVERAGE=20
MAX_RISK_USDT=250
MIN_RR_RATIO=1.5
LONG_ENTRY_OFFSET=40
LONG_SL_OFFSET=640
LONG_PULLBACK_MAX=300
SHORT_ENTRY_OFFSET=50
SHORT_SL_OFFSET=650
SHORT_TP1_OFFSET=1400
SHORT_TP2_OFFSET=2800
LOOP_INTERVAL_SECONDS=300
PAPER_TRADING=false
OKX_DEMO=true
TELEGRAM_TOKEN=tu_token
TELEGRAM_CHAT_ID=tu_chat_id
```

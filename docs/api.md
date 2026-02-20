# API Reference

## ExchangeClient

Cliente unificado para interactuar con exchanges.

### Métodos

#### `fetch_ohlcv(timeframe, limit=100)`
Obtiene velas OHLCV.

```python
candles = client.fetch_ohlcv('1h', limit=100)
```

#### `fetch_ticker()`
Obtiene datos del ticker actual.

```python
ticker = client.fetch_ticker()
price = ticker['last']
```

#### `fetch_positions()`
Obtiene posiciones abiertas.

```python
positions = client.fetch_positions()
```

#### `create_limit_order(side, amount, price, params)`
Crea orden limit.

```python
order = client.create_limit_order('buy', 0.01, 65000)
```

#### `create_market_order(side, amount, params)`
Crea orden market.

```python
order = client.create_market_order('sell', 0.01)
```

#### `cancel_order(order_id)`
Cancela una orden.

```python
client.cancel_order('12345')
```

## BreakoutStrategy

Estrategia de breakout con soporte y resistencia dinámicos.

### Métodos

#### `evaluate(current_price)`
Evalúa si hay señal de entrada.

```python
signal, reason = strategy.evaluate(67668.00)
if signal:
    print(f"Señal {signal['side']}: Entry={signal['entry']}")
```

## RiskManager

Gestiona el riesgo de las operaciones.

### Métodos

#### `validate_trade(signal)`
Valida si la operación cumple criterios de riesgo.

```python
valid, qty, msg = risk.validate_trade(signal)
if valid:
    print(f"Quantity validada: {qty}")
```

## TelegramNotifier

Envía notificaciones por Telegram.

### Métodos

#### `send(message)`
Envía mensaje de notificación.

```python
notifier.send("Señal LONG detectada 🚀")
```

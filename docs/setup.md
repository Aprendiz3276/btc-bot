# Setup

## Instalación

### Requisitos
- Python 3.11+
- pip
- Git

### Pasos

1. **Clonar repositorio**
```bash
git clone https://github.com/Aprendiz3276/btc-bot
cd btc-bot
```

2. **Crear virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar credenciales**
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

5. **Ejecutar bot**
```bash
# Un solo ciclo
python -m btc_bot.main --once

# Loop infinito
python -m btc_bot.main
```

## Docker (opcional)

```bash
docker build -t btc-bot .
docker run -e EXCHANGE_NAME=okx -e API_KEY=xxx btc-bot
```

## GitHub Actions

Configura los secrets en Settings → Secrets and variables → Actions para ejecutar automáticamente.

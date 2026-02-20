#!/usr/bin/env python3
"""
Script para obtener tu CHAT_ID de Telegram
1. Reemplaza TOKEN con tu token de bot
2. Ejecuta el script
3. Envía cualquier mensaje a tu bot
4. Verás tu CHAT_ID en la salida
"""

import requests
import json

TOKEN = input("Ingresa tu TELEGRAM_TOKEN: ").strip()

if not TOKEN:
    print("Token vacio. Exiting.")
    exit(1)

print(f"\n✓ Token OK. Esperando mensajes...")
print("→ Abre Telegram y envía un mensaje a tu bot: https://t.me/botfather")
print("→ Luego regresa aquí y presiona Enter...\n")

input("Presiona Enter después de enviar un mensaje al bot...")

try:
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url)
    data = response.json()

    if data.get("ok") and data.get("result"):
        for update in data["result"]:
            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                username = update["message"]["chat"].get("username", "N/A")
                print(f"\n✓ CHAT_ID encontrado: {chat_id}")
                print(f"  Usuario: @{username}")
                print(f"\nGuarda este valor en GitHub:")
                print(
                    f"  gh secret set TELEGRAM_CHAT_ID --body \"{chat_id}\" --repo Aprendiz3276/btc-bot")
                break
    else:
        print("❌ No se encontraron mensajes. Asegúrate de enviar un mensaje al bot.")

except Exception as e:
    print(f"❌ Error: {e}")

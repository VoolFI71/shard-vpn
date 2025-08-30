import os
import requests
import time
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv('BOT_TOKEN', '')
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in .env")
last_update_id = 0  # Отслеживаем последнее обновление

while True:
    updates = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}").json()
    
    if "result" in updates:
        for update in updates["result"]:
            if "message" in update and "effect_id" in update["message"]:
                print("Effect ID:", update["message"]["effect_id"])
            last_update_id = update["update_id"]
    
    time.sleep(1)  # Пауза 1 сек между запросами
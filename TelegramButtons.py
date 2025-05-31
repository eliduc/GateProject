import requests
import time
import json
import configparser
import os
import pandas as pd

from translations import get_translations_cached as load_translations, get_message

def load_config():
    config = configparser.ConfigParser()
    config.read('gpp.ini')
    return (
        config['TelegramButtons']['TOKEN'].strip('"'),
        config['TelegramButtons']['chat_id'].strip('"'),
        int(config['TelegramButtons']['N_to_buttons'])
    )

TOKEN, chat_id, N_to_buttons = load_config()

def send_message_with_buttons(message, image_path, buttons, translations):
    if image_path and os.path.exists(image_path):
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        with open(image_path, "rb") as image_file:
            files = {"photo": image_file}
            data = {
                "chat_id": chat_id,
                "caption": message,
            }
            if buttons:
                keyboard = {
                    "inline_keyboard": [
                        [{"text": get_message(7, translations), "callback_data": "open_gate"}],  # Opening gate...
                        [{"text": get_message(23, translations), "callback_data": "cancel"}]  # Cancel
                    ]
                }
                data["reply_markup"] = json.dumps(keyboard)
            response = requests.post(url, data=data, files=files)
    else:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
        }
        if buttons:
            keyboard = {
                "inline_keyboard": [
                    [{"text": get_message(7, translations), "callback_data": "open_gate"}],  # Opening gate...
                    [{"text": get_message(23, translations), "callback_data": "cancel"}]  # Cancel
                ]
            }
            data["reply_markup"] = json.dumps(keyboard)
        response = requests.post(url, data=data)
    
    return response.json()['result']['message_id']

def get_updates(offset, timeout=1):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": timeout}
    response = requests.get(url, params=params)
    return response.json()

def get_latest_update_id():
    updates = get_updates(0)
    if not updates.get("result"):
        return 0
    return max(update["update_id"] for update in updates["result"])

def answer_callback_query(callback_query_id):
    url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
    data = {"callback_query_id": callback_query_id}
    requests.post(url, data=data)

def telegram_button_handler(message, path, buttons, user_lang):
    translations = load_translations('gate_project_translations.md', user_lang)
    message_id = send_message_with_buttons(message, path, buttons, translations)
    
    if not buttons:
        return "0"  # No buttons, so we return immediately
    
    offset = get_latest_update_id() + 1
    start_time = time.time()
    
    while True:
        current_time = time.time()
        if current_time - start_time > N_to_buttons:
            return "0"  # Timeout occurred
        
        updates = get_updates(offset, timeout=1)
        
        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            if "callback_query" in update:
                callback_query = update["callback_query"]
                
                if callback_query["message"]["message_id"] == message_id:
                    callback_data = callback_query["data"]
                    answer_callback_query(callback_query["id"])
                    
                    if callback_data == "open_gate":
                        return "+1"
                    elif callback_data == "cancel":
                        return "-1"

if __name__ == "__main__":
    user_lang = "EN"  # Default language for testing
    translations = load_translations('gate_project_translations.md', user_lang)
    test_message = get_message(1, translations)  # Welcome to Gate System
    test_path = "lev.jpg"
    result = telegram_button_handler(test_message, test_path, buttons=False, user_lang=user_lang)
    print(f"TelegramButtons test result: {result}")
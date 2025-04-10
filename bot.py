import os
import logging
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

# Пример анкет
profiles = [
    {"name": "Анна", "age": 23, "gender": "female"},
    {"name": "Дима", "age": 25, "gender": "male"},
    {"name": "Саша", "age": 23, "gender": "female"}
]

user_states = {}  # временное хранилище для пользователя

def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def handle_filters(chat_id, text):
    state = user_states.get(chat_id, {})

    if "gender" not in state:
        state["gender"] = text.lower()
        user_states[chat_id] = state
        send_message(chat_id, "Укажи возраст:")
        return

    if "age" not in state:
        state["age"] = text
        user_states[chat_id] = state

        # Поиск совпадений
        filters = state
        matches = [p for p in profiles if
                   p["gender"] == filters["gender"] and str(p["age"]) == str(filters["age"])]

        if matches:
            result = "\n".join([f"{p['name']}, {p['age']}, {p['gender']}" for p in matches])
        else:
            result = "Совпадений не найдено."

        send_message(chat_id, result)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

        if text == "/start":
            user_states[chat_id] = {}
            send_message(chat_id, "Привет! Укажи пол (male/female):")

        elif text.startswith("/find"):
            # Пример: /find age=23 gender=female
            criteria = {}
            try:
                parts = text.split()[1:]
                for part in parts:
                    key, value = part.split("=")
                    criteria[key] = value

                matches = [p for p in profiles if all(str(p.get(k)) == v for k, v in criteria.items())]

                if matches:
                    result = "\n".join([f"{p['name']}, {p['age']}, {p['gender']}" for p in matches])
                else:
                    result = "Совпадений не найдено."
            except Exception:
                result = "Неверный формат. Пример: /find age=23 gender=female"

            send_message(chat_id, result)

        else:
            handle_filters(chat_id, text)

    return "OK"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

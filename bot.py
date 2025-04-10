import os
import logging
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

user_states = {}

def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def send_profile(chat_id, profile):
    text = (
        f"Имя: {profile['name']}"
"
        f"Пол: {profile['gender']}
"
        f"Возраст: {profile['age']}
"
        f"Город: {profile['city']}
"
        f"Цель: {profile['goal']}
"
        f"О себе: {profile['about']}"
    )
    send_message(chat_id, text)
    # отправка фото
    if "photo" in profile:
        requests.post(f"{API_URL}/sendPhoto", json={
            "chat_id": chat_id,
            "photo": profile["photo"]
        })

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]

        if "text" in message:
            text = message["text"]
            if text == "/start":
                user_states[chat_id] = {}
                send_message(chat_id, "Привет! Давай создадим анкету. Как тебя зовут?")
            else:
                handle_user_response(chat_id, text)

        elif "photo" in message:
            file_id = message["photo"][-1]["file_id"]
            state = user_states.get(chat_id, {})
            if "photo" not in state:
                state["photo"] = f"https://api.telegram.org/file/bot{TOKEN}/{file_id}"
                user_states[chat_id] = state
                send_message(chat_id, "Спасибо! Твоя анкета полностью создана:")
                send_profile(chat_id, state)
            else:
                send_message(chat_id, "Фото уже добавлено.")
    return "OK"

def handle_user_response(chat_id, text):
    state = user_states.get(chat_id, {})

    if "name" not in state:
        state["name"] = text
        send_message(chat_id, "Укажи пол (мужской/женский):")
    elif "gender" not in state:
        if text.lower() not in ["мужской", "женский"]:
            send_message(chat_id, "Пожалуйста, укажи 'мужской' или 'женский':")
            return
        state["gender"] = text.lower()
        send_message(chat_id, "Сколько тебе лет?")
    elif "age" not in state:
        if not text.isdigit():
            send_message(chat_id, "Укажи возраст числом:")
            return
        state["age"] = int(text)
        send_message(chat_id, "Из какого ты города?")
    elif "city" not in state:
        state["city"] = text
        send_message(chat_id, "Какая у тебя цель знакомства? (дружба, отношения, общение и т.д.)")
    elif "goal" not in state:
        state["goal"] = text
        send_message(chat_id, "Напиши немного о себе:")
    elif "about" not in state:
        state["about"] = text
        send_message(chat_id, "Теперь отправь своё фото:")
    else:
        send_message(chat_id, "Анкета уже заполнена. Напиши /start, чтобы начать заново.")

    user_states[chat_id] = state

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

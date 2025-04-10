import os
import logging
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

user_states = {}  # Хранение данных анкеты пользователя

def send_message(chat_id, text):
    requests.post(API_URL, json={
        "chat_id": chat_id,
        "text": text
    })

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

        if text == "/start":
            user_states[chat_id] = {}
            send_message(chat_id, "Привет! Давай создадим анкету.\nКак тебя зовут?")
        else:
            handle_user_response(chat_id, text)

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
        send_message(chat_id, "Спасибо! Твоя анкета создана.")
        show_profile(chat_id, state)
    else:
        send_message(chat_id, "Анкета уже заполнена. Напиши /start, чтобы начать заново.")

    user_states[chat_id] = state

def show_profile(chat_id, profile):
    text = (
        f"Имя: {profile['name']}\n"
        f"Пол: {profile['gender']}\n"
        f"Возраст: {profile['age']}\n"
        f"Город: {profile['city']}\n"
        f"Цель: {profile['goal']}"
    )
    send_message(chat_id, text)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

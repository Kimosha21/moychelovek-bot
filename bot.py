
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
    {"name": "Анна", "age": 23, "gender": "жен", "city": "Москва", "about": "Люблю кино и кофе"},
    {"name": "Дима", "age": 25, "gender": "муж", "city": "Сочи", "about": "Хожу в зал и путешествую"},
    {"name": "Саша", "age": 23, "gender": "жен", "city": "Казань", "about": "Рисую и катаюсь на велике"},
]

user_states = {}  # временное хранилище для пользователей

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
    elif "age" not in state:
        try:
            state["age"] = int(text)
            user_states[chat_id] = state
            send_message(chat_id, "Из какого ты города?")
        except:
            send_message(chat_id, "Пожалуйста, введи возраст цифрой:")
    elif "city" not in state:
        state["city"] = text
        user_states[chat_id] = state
        profile = find_match(state)
        if profile:
            send_message(chat_id, format_profile(profile))
        else:
            send_message(chat_id, "К сожалению, подходящих анкет не найдено.")
        user_states.pop(chat_id)  # очистим данные

def format_profile(profile):
    return f"Имя: {profile['name']}\nВозраст: {profile['age']}\nГород: {profile['city']}\nО себе: {profile['about']}"

def find_match(filters):
    for profile in profiles:
        if (profile["gender"] == filters["gender"]
            and profile["age"] == filters["age"]
            and profile["city"].lower() == filters["city"].lower()):
            return profile
    return None

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

        if text == "/start": 
            user_states[chat_id] = {}
            send_message(chat_id, "Привет! Укажи пол (муж/жен):")
        else:
            handle_filters(chat_id, text)
    return "OK" 
elif text.startswith("/find"):
    # Пример: /find age=23 gender=female
    criteria = {}
    try:
        parts = text.split()[1:]  # Пропускаем "/find"
        for part in parts:
            key, value = part.split("=")
            criteria[key] = value

        # Поиск совпадений
        matches = [p for p in profiles if all(str(p.get(k)) == v for k, v in criteria.items())]

        if matches:
            result = "\n".join([f"{p['name']}, {p['age']} лет, {p['gender']}" for p in matches])
        else:
            result = "Совпадений не найдено."

    except Exception as e:
        result = "Неверный формат. Пример: /find age=23 gender=female"

    requests.post(API_URL + "sendMessage", json={
        "chat_id": chat_id,
        "text": result
    })

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

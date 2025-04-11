
import os
import json
import logging
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

DATA_DIR = "data"
PROFILE_FILE = os.path.join(DATA_DIR, "profiles.json")
LIKES_FILE = os.path.join(DATA_DIR, "likes.json")
COINS_FILE = os.path.join(DATA_DIR, "coins.json")

# Загрузка/сохранение данных
def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users = {}
profiles = load_json(PROFILE_FILE, [])
likes = load_json(LIKES_FILE, {})
coins = load_json(COINS_FILE, {})

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{API_URL}/sendMessage", json=payload)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    global profiles, likes, coins
    update = request.get_json()

    if "message" in update:
        message = update["message"]
        chat_id = str(message["chat"]["id"])
        text = message.get("text", "")
        photo = message.get("photo")

        user = users.get(chat_id, {"step": "name"})

        if text == "/start":
            users[chat_id] = {"step": "name"}
            send_message(chat_id, "Привет! Как тебя зовут?")
        elif user["step"] == "name":
            user["name"] = text
            user["step"] = "gender"
            send_message(chat_id, "Укажи пол (мужской/женский):")
        elif user["step"] == "gender":
            user["gender"] = text
            user["step"] = "age"
            send_message(chat_id, "Сколько тебе лет?")
        elif user["step"] == "age":
            user["age"] = text
            user["step"] = "city"
            send_message(chat_id, "Из какого ты города?")
        elif user["step"] == "city":
            user["city"] = text
            user["step"] = "goal"
            send_message(chat_id, "Какова цель знакомства?")
        elif user["step"] == "goal":
            user["goal"] = text
            user["step"] = "about"
            send_message(chat_id, "Расскажи немного о себе:")
        elif user["step"] == "about":
            user["about"] = text
            user["step"] = "photo"
            send_message(chat_id, "Отправь своё фото:")
        elif user["step"] == "photo" and photo:
            photo_id = photo[-1]["file_id"]
            profile = {
                "id": chat_id,
                "name": user["name"],
                "gender": user["gender"],
                "age": user["age"],
                "city": user["city"],
                "goal": user["goal"],
                "about": user["about"],
                "photo": photo_id
            }
            profiles.append(profile)
            coins[chat_id] = coins.get(chat_id, 5)
            users[chat_id]["step"] = "done"
            save_json(PROFILE_FILE, profiles)
            save_json(COINS_FILE, coins)
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔍 Поиск анкет", "callback_data": "search"}],
                    [{"text": "✏️ Редактировать анкету", "callback_data": "edit"}],
                    [{"text": "♻️ Начать заново", "callback_data": "restart"}]
                ]
            }
            send_message(chat_id, "Анкета сохранена! Выбери действие:", reply_markup=keyboard)

        users[chat_id] = user

    elif "callback_query" in update:
        query = update["callback_query"]
        data = query["data"]
        chat_id = str(query["from"]["id"])

        if data == "restart" or data == "edit":
            users[chat_id] = {"step": "name"}
            send_message(chat_id, "Начнём заново. Как тебя зовут?")
        elif data == "search":
            for p in profiles:
                if p["id"] != chat_id:
                    caption = f"Имя: {p['name']}
Возраст: {p['age']}
Город: {p['city']}
О себе: {p['about']}"
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "❤️", "callback_data": f"like_{p['id']}"}],
                            [{"text": "⏭", "callback_data": "search"}]
                        ]
                    }
                    requests.post(f"{API_URL}/sendPhoto", json={
                        "chat_id": chat_id,
                        "photo": p["photo"],
                        "caption": caption,
                        "reply_markup": keyboard
                    })
                    break
        elif data.startswith("like_"):
            liked_id = data.split("_")[1]
            likes.setdefault(liked_id, []).append(chat_id)
            save_json(LIKES_FILE, likes)
            send_message(chat_id, "Лайк отправлен!")

    return "OK"

@app.route("/", methods=["GET"])
def index():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

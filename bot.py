import os
import json
from flask import Flask, request
import requests

app = Flask(__name__)

TOKEN = "YOUR_BOT_TOKEN"
API_URL = f"https://api.telegram.org/bot{TOKEN}"

users = {}
profiles = []
likes = {}
daily_likes = {}
VIP_USERS = set()
ADMIN_ID = 123456789  # замените на ваш Telegram ID

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API_URL}/sendMessage", json=payload)

def check_gender_match(user_gender, profile_gender):
    user_gender = user_gender.lower()
    profile_gender = profile_gender.lower()
    return (user_gender == "мужской" and profile_gender == "женский") or \
           (user_gender == "женский" and profile_gender == "мужской")

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        photo = message.get("photo")

        user = users.get(chat_id, {"state": "start"})
        state = user["state"]

        if text == "/start":
            users[chat_id] = {"state": "name"}
            send_message(chat_id, "Привет! Введи своё имя:")
            return "ok"

        if state == "name":
            user["name"] = text
            user["state"] = "gender"
            send_message(chat_id, "Укажи свой пол (мужской/женский):")

        elif state == "gender":
            user["gender"] = text
            user["state"] = "age"
            send_message(chat_id, "Сколько тебе лет?")

        elif state == "age":
            user["age"] = text
            user["state"] = "city"
            send_message(chat_id, "Из какого ты города?")

        elif state == "city":
            user["city"] = text
            user["state"] = "goal"
            send_message(chat_id, "Какова цель знакомства?")

        elif state == "goal":
            user["goal"] = text
            user["state"] = "about"
            send_message(chat_id, "Расскажи немного о себе:")

        elif state == "about":
            user["about"] = text
            user["state"] = "photo"
            send_message(chat_id, "Отправь своё фото:")

        elif state == "photo" and photo:
            file_id = photo[-1]["file_id"]
            user["photo_id"] = file_id
            user["state"] = "done"
            users[chat_id] = user
            profiles.append(chat_id)
            daily_likes.setdefault(chat_id, 10)
            send_profile(chat_id, chat_id, own=True)
            show_main_menu(chat_id)
            return "ok"

        users[chat_id] = user

    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["from"]["id"]
        data = query["data"]

        if data == "start":
            users[chat_id] = {"state": "name"}
            send_message(chat_id, "Давай начнем заново! Введи своё имя:")
        elif data == "profile":
            send_profile(chat_id, chat_id, own=True)
        elif data == "like":
            show_next_profile(chat_id)
        elif data == "vip":
            VIP_USERS.add(chat_id)
            send_message(chat_id, "Теперь ты VIP! Лайков без ограничений.")
        elif data == "stats" and chat_id == ADMIN_ID:
            send_message(chat_id, f"Пользователей: {len(profiles)}")

    return "ok"

def send_profile(to_chat_id, user_id, own=False):
    user = users[user_id]
    caption = (
        f"<b>Имя:</b> {user['name']}\n"
        f"<b>Пол:</b> {user['gender']}\n"
        f"<b>Возраст:</b> {user['age']}\n"
        f"<b>Город:</b> {user['city']}\n"
        f"<b>Цель:</b> {user['goal']}\n"
        f"<b>О себе:</b> {user['about']}\n"
    )
    if user_id in VIP_USERS:
        caption += "<b>VIP:</b> Да\n"

    keyboard = {"inline_keyboard": []}
    if own:
        keyboard["inline_keyboard"].append([
            {"text": "🔁 Начать заново", "callback_data": "start"},
            {"text": "🧾 Моя анкета", "callback_data": "profile"},
            {"text": "⭐ VIP", "callback_data": "vip"}
        ])
    else:
        keyboard["inline_keyboard"].append([
            {"text": "❤️ Лайк", "callback_data": "like"}
        ])

    requests.post(API_URL + "/sendPhoto", json={
        "chat_id": to_chat_id,
        "photo": user["photo_id"],
        "caption": caption,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(keyboard)
    })

def show_next_profile(chat_id):
    user_gender = users[chat_id].get("gender", "").lower()
    for user_id in profiles:
        if user_id != chat_id and chat_id not in likes.get(user_id, []):
            profile_gender = users[user_id].get("gender", "").lower()
            if not check_gender_match(user_gender, profile_gender):
                continue
            if chat_id not in VIP_USERS and daily_likes.get(chat_id, 0) <= 0:
                send_message(chat_id, "У тебя закончились лайки на сегодня.")
                return
            likes.setdefault(user_id, []).append(chat_id)
            if chat_id not in VIP_USERS:
                daily_likes[chat_id] -= 1
            send_profile(chat_id, user_id)
            return
    send_message(chat_id, "Пока нет новых анкет. Попробуй позже.")

def show_main_menu(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔁 Начать заново", "callback_data": "start"}],
            [{"text": "🧾 Моя анкета", "callback_data": "profile"}],
            [{"text": "⭐ VIP", "callback_data": "vip"}]
        ]
    }
    send_message(chat_id, "Выбери действие:", reply_markup=keyboard)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

import os
import json
import requests
from flask import Flask, request
from datetime import datetime, timedelta

app = Flask(__name__)

TOKEN = "YOUR_BOT_TOKEN"  # Замените на свой токен
API_URL = f"https://api.telegram.org/bot{TOKEN}"

users = {}
profiles = []
likes = {}
vip_users = set()
coins = {}
matches = set()
like_timestamps = {}
ADMIN_ID = 123456789  # Замените на свой Telegram ID
MAX_LIKES = 10

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API_URL}/sendMessage", json=payload)

def send_photo(chat_id, file_id, caption, reply_markup=None):
    payload = {"chat_id": chat_id, "photo": file_id, "caption": caption, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API_URL}/sendPhoto", json=payload)

def reset_likes():
    now = datetime.utcnow()
    for chat_id in like_timestamps:
        if (now - like_timestamps[chat_id]).days >= 1:
            like_timestamps[chat_id] = now
            likes[chat_id] = 0
            def get_opposite_gender(gender):
    gender = gender.lower()
    if gender == "мужской":
        return "женский"
    elif gender == "женский":
        return "мужской"
    return None

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        photo = message.get("photo")

        user = users.get(chat_id, {"state": "start"})

        if text == "/start":
            users[chat_id] = {"state": "name"}
            coins.setdefault(chat_id, 10)
            likes.setdefault(chat_id, 0)
            like_timestamps.setdefault(chat_id, datetime.utcnow())
            send_message(chat_id, "Привет! Давай создадим твою анкету.\nКак тебя зовут?")
            return "ok"

        state = user["state"]

        if state == "name":
            user["name"] = text
            user["state"] = "gender"
            send_message(chat_id, "Укажи свой пол (мужской/женский):")
        elif state == "gender":
            user["gender"] = text.lower()
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
        elif state == "photo":
            if not photo:
                send_message(chat_id, "Пожалуйста, отправь именно ФОТО, а не текст.")
                return "ok"
            file_id = photo[-1]["file_id"]
            user["photo_id"] = file_id
            user["state"] = "done"
            users[chat_id] = user
            if chat_id not in [p["id"] for p in profiles]:
                profiles.append({"id": chat_id, **user})
            send_message(chat_id, "Твоя анкета успешно создана!")
            show_profile(chat_id, chat_id, own=True)
            return "ok"

        users[chat_id] = user

    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["from"]["id"]
        data = query["data"]

        if data == "start":
            users[chat_id] = {"state": "name"}
            send_message(chat_id, "Давай начнем заново. Как тебя зовут?")
        elif data == "profile":
            show_profile(chat_id, chat_id, own=True)
        elif data == "search":
            show_next_profile(chat_id)
        elif data == "like":
            handle_like(chat_id)
        elif data == "vip":
            buy_vip(chat_id)
        elif data == "edit":
            users[chat_id] = {"state": "name"}
            send_message(chat_id, "Редактируем анкету. Как тебя зовут?")
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Бот работает"

def show_profile(to_chat_id, user_id, own=False):
    user = users.get(user_id)
    if not user:
        for p in profiles:
            if p["id"] == user_id:
                user = p
                break
    if not user:
        send_message(to_chat_id, "Анкета не найдена.")
        return

    caption = (
        f"<b>{user['name']}, {user['age']}</b>\n"
        f"Город: {user['city']}\n"
        f"Цель: {user['goal']}\n"
        f"О себе: {user['about']}\n"
    )
    if user_id in vip_users:
        caption += "💎 <b>VIP</b>\n"

    buttons = []
    if own:
        buttons = [
            [{"text": "🔍 Поиск анкет", "callback_data": "search"}],
            [{"text": "✏️ Редактировать", "callback_data": "edit"}],
            [{"text": "💎 VIP", "callback_data": "vip"}]
        ]
    else:
        buttons = [[{"text": "❤️ Лайк", "callback_data": "like"}]]

    send_photo(to_chat_id, user["photo_id"], caption, reply_markup={"inline_keyboard": buttons})
    def show_next_profile(chat_id):
    user = users.get(chat_id)
    if not user or "gender" not in user:
        send_message(chat_id, "Сначала создай анкету.")
        return

    target_gender = get_opposite_gender(user["gender"])
    for profile in profiles:
        if profile["id"] == chat_id:
            continue
        if profile["gender"] != target_gender:
            continue
        if chat_id in likes.get(profile["id"], []):
            continue
        show_profile(chat_id, profile["id"])
        return

    send_message(chat_id, "Пока нет новых анкет подходящего пола.")

def handle_like(chat_id):
    user = users.get(chat_id)
    if not user:
        send_message(chat_id, "Создай анкету сначала.")
        return

    last_profile = next((p for p in profiles if p["id"] != chat_id and get_opposite_gender(user["gender"]) == p["gender"] and chat_id not in likes.get(p["id"], [])), None)

    if not last_profile:
        send_message(chat_id, "Нет анкет для лайка.")
        return

    target_id = last_profile["id"]

    if chat_id not in vip_users:
        reset_likes()
        if likes.get(chat_id, 0) >= MAX_LIKES:
            send_message(chat_id, "Ты использовал все 10 лайков сегодня.")
            return
        likes[chat_id] = likes.get(chat_id, 0) + 1

    likes.setdefault(target_id, []).append(chat_id)

    if chat_id in likes.get(target_id, []):
        if (chat_id, target_id) not in matches and (target_id, chat_id) not in matches:
            matches.add((chat_id, target_id))
            send_message(chat_id, "У вас взаимный лайк!")
            send_message(target_id, "У вас взаимный лайк!")
            def show_next_profile(chat_id):
    user = users.get(chat_id)
    if not user or "gender" not in user:
        send_message(chat_id, "Сначала создай анкету.")
        return

    target_gender = get_opposite_gender(user["gender"])
    for profile in profiles:
        if profile["id"] == chat_id:
            continue
        if profile["gender"] != target_gender:
            continue
        if chat_id in likes.get(profile["id"], []):
            continue
        show_profile(chat_id, profile["id"])
        return

    send_message(chat_id, "Пока нет новых анкет подходящего пола.")

def handle_like(chat_id):
    user = users.get(chat_id)
    if not user:
        send_message(chat_id, "Создай анкету сначала.")
        return

    last_profile = next((p for p in profiles if p["id"] != chat_id and get_opposite_gender(user["gender"]) == p["gender"] and chat_id not in likes.get(p["id"], [])), None)

    if not last_profile:
        send_message(chat_id, "Нет анкет для лайка.")
        return

    target_id = last_profile["id"]

    if chat_id not in vip_users:
        reset_likes()
        if likes.get(chat_id, 0) >= MAX_LIKES:
            send_message(chat_id, "Ты использовал все 10 лайков сегодня.")
            return
        likes[chat_id] = likes.get(chat_id, 0) + 1

    likes.setdefault(target_id, []).append(chat_id)

    if chat_id in likes.get(target_id, []):
        if (chat_id, target_id) not in matches and (target_id, chat_id) not in matches:
            matches.add((chat_id, target_id))
            send_message(chat_id, "У вас взаимный лайк!")
            send_message(target_id, "У вас взаимный лайк!")

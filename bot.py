import os
import json
import random
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

users = {}
profiles = []
likes = {}
coins = {}
vip_users = set()

ADMIN_ID = os.getenv("ADMIN_ID", "123456789")  # Заменить на ID админа

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(API_URL + "/sendMessage", json=payload)

def send_photo(chat_id, photo_path, caption=None, reply_markup=None):
    with open(photo_path, "rb") as photo:
        data = {"chat_id": chat_id, "caption": caption}
        files = {"photo": photo}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        requests.post(API_URL + "/sendPhoto", data=data, files=files)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text")
        photo = msg.get("photo")
        state = users.get(chat_id, {}).get("state")

        if text == "/start":
            users[chat_id] = {"state": "name"}
            send_message(chat_id, "Привет! Давай создадим анкету.\nКак тебя зовут?")
            return "OK"

        if state == "name":
            users[chat_id]["name"] = text
            users[chat_id]["state"] = "gender"
            send_message(chat_id, "Укажи свой пол (мужской/женский):")
        elif state == "gender":
            users[chat_id]["gender"] = text
            users[chat_id]["state"] = "age"
            send_message(chat_id, "Сколько тебе лет?")
        elif state == "age":
            users[chat_id]["age"] = text
            users[chat_id]["state"] = "city"
            send_message(chat_id, "Из какого ты города?")
        elif state == "city":
            users[chat_id]["city"] = text
            users[chat_id]["state"] = "goal"
            send_message(chat_id, "Какова цель знакомства?")
        elif state == "goal":
            users[chat_id]["goal"] = text
            users[chat_id]["state"] = "about"
            send_message(chat_id, "Расскажи немного о себе:")
        elif state == "about":
            users[chat_id]["about"] = text
            users[chat_id]["state"] = "photo"
            send_message(chat_id, "Отправь своё фото:")
        elif state == "photo" and photo:
            file_id = photo[-1]["file_id"]
            file_info = requests.get(API_URL + f"/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            img_data = requests.get(file_url).content
            photo_path = f"{chat_id}.jpg"
            with open(photo_path, "wb") as f:
                f.write(img_data)

            profile = {
                "id": chat_id,
                "name": users[chat_id]["name"],
                "gender": users[chat_id]["gender"],
                "age": users[chat_id]["age"],
                "city": users[chat_id]["city"],
                "goal": users[chat_id]["goal"],
                "about": users[chat_id]["about"],
                "photo_path": photo_path
            }
            profiles.append(profile)
            users[chat_id]["state"] = "menu"

            caption = (
                f"Имя: {profile['name']}\n"
                f"Пол: {profile['gender']}\n"
                f"Возраст: {profile['age']}\n"
                f"Город: {profile['city']}\n"
                f"Цель: {profile['goal']}\n"
                f"О себе: {profile['about']}"
            )

            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔍 Поиск анкет", "callback_data": "search"}],
                    [{"text": "✏️ Редактировать", "callback_data": "edit"}],
                    [{"text": "💰 Купить VIP (5 монет)", "callback_data": "buy_vip"}]
                ]
            }
            send_photo(chat_id, photo_path, caption, reply_markup=keyboard)
            return "OK"

    if "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["from"]["id"]
        data = query["data"]

        if data == "search":
            for profile in profiles:
                if profile["id"] != chat_id:
                    caption = (
                        f"Имя: {profile['name']}\n"
                        f"Пол: {profile['gender']}\n"
                        f"Возраст: {profile['age']}\n"
                        f"Город: {profile['city']}\n"
                        f"Цель: {profile['goal']}\n"
                        f"О себе: {profile['about']}"
                    )

                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "❤️ Лайк", "callback_data": f"like_{profile['id']}"}],
                            [{"text": "⏭ Пропустить", "callback_data": "search"}]
                        ]
                    }
                    send_photo(chat_id, profile["photo_path"], caption, reply_markup=keyboard)
                    return "OK"
            send_message(chat_id, "Анкет больше нет.")
        elif data.startswith("like_"):
            liked_id = int(data.split("_")[1])
            likes.setdefault(liked_id, []).append(chat_id)
            send_message(chat_id, "Ты поставил(а) лайк!")
        elif data == "buy_vip":
            if coins.get(chat_id, 0) >= 5:
                coins[chat_id] -= 5
                vip_users.add(chat_id)
                send_message(chat_id, "Ты купил VIP-доступ!")
            else:
                send_message(chat_id, "Недостаточно монет. Нужно 5.")

    return "OK"

@app.route("/")
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

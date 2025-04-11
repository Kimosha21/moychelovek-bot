import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.getenv("TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}/"
users = {}
profiles = []
likes = {}
coins = {}
vip_users = set()

def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    requests.post(API_URL + "sendMessage", json=data)

def send_photo(chat_id, photo_path, caption=None, reply_markup=None):
    url = API_URL + "sendPhoto"
    with open(photo_path, "rb") as photo:
        files = {"photo": photo}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        requests.post(url, data=data, files=files)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        photo = message.get("photo")
        state = users.get(chat_id, {}).get("state")

        if text == "/start":
            users[chat_id] = {"state": "name"}
            send_message(chat_id, "Привет! Как тебя зовут?")
            return "OK"

        if state == "name":
            users[chat_id]["name"] = text
            users[chat_id]["state"] = "gender"
            send_message(chat_id, "Укажи пол (мужской/женский):")
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
            file_path = f"{chat_id}.jpg"
            file_info = requests.get(API_URL + f"getFile?file_id={file_id}").json()
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info['result']['file_path']}"
            img_data = requests.get(file_url).content
            with open(file_path, "wb") as f:
                f.write(img_data)

            profile = {
                "chat_id": chat_id,
                "name": users[chat_id]["name"],
                "gender": users[chat_id]["gender"],
                "age": users[chat_id]["age"],
                "city": users[chat_id]["city"],
                "goal": users[chat_id]["goal"],
                "about": users[chat_id]["about"],
                "photo_path": file_path
            }
            profiles.append(profile)
            coins[chat_id] = 10

            send_message(chat_id, "Спасибо! Твоя анкета сохранена.")
            show_menu(chat_id)
        elif text == "Моя анкета":
            show_profile(chat_id)
        return "OK"

    if "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        data = query["data"]

        if data == "menu":
            show_menu(chat_id)
        elif data == "view":
            show_random_profile(chat_id)
        elif data == "like":
            handle_like(chat_id)
        elif data == "skip":
            show_random_profile(chat_id)
        elif data == "vip":
            if coins.get(chat_id, 0) >= 5:
                coins[chat_id] -= 5
                vip_users.add(chat_id)
                send_message(chat_id, "Теперь ты VIP!")
            else:
                send_message(chat_id, "Недостаточно монет.")
        return "OK"

    return "OK"

def show_menu(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "Моя анкета", "callback_data": "menu"}],
            [{"text": "Поиск анкет", "callback_data": "view"}],
            [{"text": "Получить VIP (5 монет)", "callback_data": "vip"}]
        ]
    }
    send_message(chat_id, "Выбери действие:", reply_markup=keyboard)

def show_profile(chat_id):
    for profile in profiles:
        if profile["chat_id"] == chat_id:
            caption = (
                f"Имя: {profile['name']}\n"
                f"Пол: {profile['gender']}\n"
                f"Возраст: {profile['age']}\n"
                f"Город: {profile['city']}\n"
                f"Цель: {profile['goal']}\n"
                f"О себе: {profile['about']}\n"
                f"VIP: {'Да' if chat_id in vip_users else 'Нет'}\n"
                f"Монеты: {coins.get(chat_id, 0)}"
            )
            send_photo(chat_id, profile["photo_path"], caption=caption)
            return

def show_random_profile(chat_id):
    for profile in profiles:
        if profile["chat_id"] != chat_id:
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
                    [{"text": "❤️ Лайк", "callback_data": "like"}],
                    [{"text": "⏭ Пропустить", "callback_data": "skip"}]
                ]
            }
            users[chat_id]["current"] = profile["chat_id"]
            send_photo(chat_id, profile["photo_path"], caption=caption, reply_markup=keyboard)
            return
    send_message(chat_id, "Пока нет анкет для показа.")

def handle_like(chat_id):
    target_id = users.get(chat_id, {}).get("current")
    if not target_id:
        send_message(chat_id, "Ошибка. Попробуй ещё раз.")
        return
    if target_id in likes and chat_id in likes[target_id]:
        send_message(chat_id, "У вас взаимная симпатия!")
        send_message(target_id, "У вас взаимная симпатия!")
    likes.setdefault(chat_id, []).append(target_id)
    coins[chat_id] = coins.get(chat_id, 0) - 1
    show_random_profile(chat_id)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

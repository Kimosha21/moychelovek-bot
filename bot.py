import os
import logging
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"
users = {}
profiles = []
likes = {}

def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    requests.post(f"{API_URL}/sendMessage", json=data)

def send_profile(chat_id, profile):
    text = f"Имя: {profile['name']}\nПол: {profile['gender']}\nВозраст: {profile['age']}\nГород: {profile['city']}\nЦель: {profile['goal']}\nО себе: {profile['about']}"
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "❤️ Лайк", "callback_data": f"like_{profile['chat_id']}"},
                {"text": "⏭ Пропустить", "callback_data": "skip"}
            ]
        ]
    }
    requests.post(f"{API_URL}/sendPhoto", data={"chat_id": chat_id, "caption": text, "reply_markup": json.dumps(keyboard)}, files={"photo": open(profile["photo_path"], "rb")})

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
if "callback_query" in update:
    query = update["callback_query"]
    chat_id = query["message"]["chat"]["id"]
    data = query["data"]

    if data == "start":
        users[chat_id] = {"state": "name"}
        send_message(chat_id, "Привет! Давай заполним анкету. Как тебя зовут?")
    elif data == "edit":
        users[chat_id] = {"state": "name"}
        send_message(chat_id, "Давай отредактируем анкету. Введи своё имя:")
    elif data == "search":
        send_message(chat_id, "Скоро добавим поиск анкет. В разработке.")
    return "OK"
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]

        if "text" in message:
            text = message["text"]
            state = users.get(chat_id, {}).get("state")

            if text == "/start":
                users[chat_id] = {"state": "name"}
                send_message(chat_id, "Привет! Давай создадим анкету. Как тебя зовут?")
                return "OK"

            if state == "name":
                users[chat_id] = {"name": text, "state": "gender"}
                send_message(chat_id, "Укажи свой пол (мужской/женский):")
            elif state == "gender":
                users[chat_id]["gender"] = text
                users[chat_id]["state"] = "age"
                send_message(chat_id, "Укажи свой возраст:")
            elif state == "age":
                users[chat_id]["age"] = text
                users[chat_id]["state"] = "city"
                send_message(chat_id, "Из какого ты города?")
            elif state == "city":
                users[chat_id]["city"] = text
                users[chat_id]["state"] = "goal"
                send_message(chat_id, "Какая цель знакомства?")
            elif state == "goal":
                users[chat_id]["goal"] = text
                users[chat_id]["state"] = "about"
                send_message(chat_id, "Напиши немного о себе:")
            elif state == "about":
                users[chat_id]["about"] = text
                users[chat_id]["state"] = "photo"
                send_message(chat_id, "Теперь отправь свою фотографию:")
            else:
                send_message(chat_id, "Напиши /start, чтобы начать заново.")

        if "photo" in message and users.get(chat_id, {}).get("state") == "photo":
            file_id = message["photo"][-1]["file_id"]
            users[chat_id]["photo"] = file_id
            profile = {
                "chat_id": chat_id,
                "name": users[chat_id]["name"],
                "gender": users[chat_id]["gender"],
                "age": users[chat_id]["age"],
                "city": users[chat_id]["city"],
                "goal": users[chat_id]["goal"],
                "about": users[chat_id]["about"],
                "photo_path": f"{chat_id}.jpg"
            }
            profiles.append(profile)
            send_message(chat_id, "Спасибо! Твоя анкета сохранена.")
            keyboard = {
    "inline_keyboard": [
        [{"text": "🔍 Поиск анкет", "callback_data": "search"}],
        [{"text": "✏️ Редактировать анкету", "callback_data": "edit"}],
        [{"text": "🔁 Начать заново", "callback_data": "start"}]
    ]
}

requests.post(API_URL + "/sendMessage", json={
    "chat_id": chat_id,
    "text": "Выбери действие:",
    "reply_markup": keyboard
})
return "OK"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

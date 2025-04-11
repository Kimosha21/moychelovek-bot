
import os
import logging
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

profiles = []
users = {}

def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    requests.post(f"{API_URL}/sendMessage", json=data)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    # Обработка кнопок (callback_query)
    if "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        data = query["data"]

        if data == "start":
            users[chat_id] = {"state": "name"}
            send_message(chat_id, "Начнём заново. Как тебя зовут?")
        elif data == "edit":
            users[chat_id] = {"state": "name"}
            send_message(chat_id, "Редактируем анкету. Введи имя:")
        elif data == "search":
            found = False
            for profile in profiles:
                if profile["chat_id"] != chat_id:
                    text = f"Имя: {profile['name']}
Пол: {profile['gender']}
Возраст: {profile['age']}
Город: {profile['city']}
Цель: {profile['goal']}
О себе: {profile['about']}"
                    requests.post(f"{API_URL}/sendPhoto", json={
                        "chat_id": chat_id,
                        "photo": profile["photo"],  # используем file_id
                        "caption": text
                    })
                    found = True
                    break
            if not found:
                send_message(chat_id, "Пока нет анкет для показа.")
        return "OK"

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]

        if "text" in message:
            text = message["text"]
            state = users.get(chat_id, {}).get("state")

            if text == "/start":
                users[chat_id] = {"state": "name"}
                send_message(chat_id, "Привет! Как тебя зовут?")
                return "OK"

            if state == "name":
                users[chat_id]["name"] = text
                users[chat_id]["state"] = "gender"
                send_message(chat_id, "Укажи пол (мужской/женский):")
                return "OK"
            elif state == "gender":
                users[chat_id]["gender"] = text
                users[chat_id]["state"] = "age"
                send_message(chat_id, "Сколько тебе лет?")
                return "OK"
            elif state == "age":
                users[chat_id]["age"] = text
                users[chat_id]["state"] = "city"
                send_message(chat_id, "Из какого ты города?")
                return "OK"
            elif state == "city":
                users[chat_id]["city"] = text
                users[chat_id]["state"] = "goal"
                send_message(chat_id, "Какая цель знакомства?")
                return "OK"
            elif state == "goal":
                users[chat_id]["goal"] = text
                users[chat_id]["state"] = "about"
                send_message(chat_id, "Напиши немного о себе:")
                return "OK"
            elif state == "about":
                users[chat_id]["about"] = text
                users[chat_id]["state"] = "photo"
                send_message(chat_id, "Отправь своё фото:")
                return "OK"

        if "photo" in message:
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
                "photo": users[chat_id]["photo"]
            }
            profiles.append(profile)

            send_message(chat_id, "Спасибо! Твоя анкета сохранена.")

            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔍 Поиск анкет", "callback_data": "search"}],
                    [{"text": "✏️ Редактировать анкету", "callback_data": "edit"}],
                    [{"text": "♻️ Начать заново", "callback_data": "start"}]
                ]
            }

            send_message(chat_id, "Выбери действие:", reply_markup=keyboard)
            users[chat_id]["state"] = None
            return "OK"

    return "OK"

@app.route("/", methods=["GET"])
def home():
    return "Бот работает!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

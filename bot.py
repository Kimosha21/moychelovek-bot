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

def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(f"{API_URL}/sendMessage", json=data)

def save_photo(file_id, chat_id):
    file_info = requests.get(f"{API_URL}/getFile?file_id={file_id}").json()
    file_path = file_info["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    photo = requests.get(file_url).content
    file_name = f"{chat_id}.jpg"
    with open(file_name, "wb") as f:
        f.write(photo)
    return file_name

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        state = users.get(chat_id, {}).get("state")

        if "text" in message:
            text = message["text"]

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
                send_message(chat_id, "Укажи возраст:")
            elif state == "age":
                users[chat_id]["age"] = text
                users[chat_id]["state"] = "city"
                send_message(chat_id, "Укажи город:")
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
                send_message(chat_id, "Теперь отправь свою фотографию:")
        elif "photo" in message and state == "photo":
            photo = message["photo"][-1]
            file_id = photo["file_id"]
            photo_path = save_photo(file_id, chat_id)

            profile = {
                "name": users[chat_id]["name"],
                "gender": users[chat_id]["gender"],
                "age": users[chat_id]["age"],
                "city": users[chat_id]["city"],
                "goal": users[chat_id]["goal"],
                "about": users[chat_id]["about"],
                "photo_path": photo_path
            }
            profiles.append(profile)

            send_message(chat_id, "Спасибо! Твоя анкета сохранена.")

            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔍 Поиск анкет", "callback_data": "search"}],
                    [{"text": "✏️ Редактировать анкету", "callback_data": "edit"}],
                    [{"text": "♻️ Начать заново", "callback_data": "restart"}]
                ]
            }

            send_message(chat_id, "Выбери действие:", keyboard)
    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        data = query["data"]

        if data == "restart":
            users[chat_id] = {"state": "name"}
            send_message(chat_id, "Начнем сначала! Как тебя зовут?")
        elif data == "edit":
            users[chat_id]["state"] = "name"
            send_message(chat_id, "Редактирование анкеты. Как тебя зовут?")
        elif data == "search":
            if profiles:
                result = []
                for p in profiles:
                    text = (
                        f"Имя: {p['name']}\n"
                        f"Пол: {p['gender']}\n"
                        f"Возраст: {p['age']}\n"
                        f"Город: {p['city']}\n"
                        f"Цель: {p['goal']}\n"
                        f"О себе: {p['about']}"
                    )
                    result.append(text)
                send_message(chat_id, "\n\n".join(result))
            else:
                send_message(chat_id, "Пока нет анкет для показа.")
    return "OK"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

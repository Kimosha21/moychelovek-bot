import os
import logging
import sqlite3
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"
DATABASE = "database.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS profiles (
        chat_id INTEGER PRIMARY KEY,
        name TEXT,
        gender TEXT,
        age INTEGER,
        city TEXT,
        goal TEXT,
        about TEXT,
        photo_path TEXT,
        is_vip INTEGER DEFAULT 0,
        coins INTEGER DEFAULT 10
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user INTEGER,
        to_user INTEGER,
        UNIQUE(from_user, to_user)
    )''')
    conn.commit()
    conn.close()

init_db()

users = {}

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
                return "OK"

            if state == "gender":
                users[chat_id]["gender"] = text
                users[chat_id]["state"] = "age"
                send_message(chat_id, "Сколько тебе лет?")
                return "OK"

            if state == "age":
                users[chat_id]["age"] = text
                users[chat_id]["state"] = "city"
                send_message(chat_id, "Из какого ты города?")
                return "OK"

            if state == "city":
                users[chat_id]["city"] = text
                users[chat_id]["state"] = "goal"
                send_message(chat_id, "Какова цель знакомства?")
                return "OK"

            if state == "goal":
                users[chat_id]["goal"] = text
                users[chat_id]["state"] = "about"
                send_message(chat_id, "Расскажи немного о себе:")
                return "OK"

            if state == "about":
                users[chat_id]["about"] = text
                users[chat_id]["state"] = "photo"
                send_message(chat_id, "Теперь отправь свою фотографию:")
                return "OK"

        if "photo" in message and state == "photo":
            photo = message["photo"][-1]
            file_id = photo["file_id"]
            file_path_resp = requests.get(f"{API_URL}/getFile?file_id={file_id}").json()
            file_path = file_path_resp["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            photo_data = requests.get(file_url).content

            photo_filename = f"{chat_id}.jpg"
            with open(photo_filename, "wb") as f:
                f.write(photo_data)

            users[chat_id]["photo_path"] = photo_filename

            # Сохранение анкеты
            profile = users[chat_id]
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("REPLACE INTO profiles (chat_id, name, gender, age, city, goal, about, photo_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                chat_id,
                profile["name"],
                profile["gender"],
                int(profile["age"]),
                profile["city"],
                profile["goal"],
                profile["about"],
                photo_filename
            ))
            conn.commit()
            conn.close()

            send_message(chat_id, "Спасибо! Твоя анкета сохранена.")
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔍 Поиск анкет", "callback_data": "search"}],
                    [{"text": "✏️ Редактировать анкету", "callback_data": "edit"}],
                    [{"text": "♻️ Начать заново", "callback_data": "restart"}]
                ]
            }
            send_message(chat_id, "Выбери действие:", reply_markup=keyboard)
            return "OK"

    if "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["from"]["id"]
        data = query["data"]

        if data == "stats":
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM profiles")
            total_users = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM likes")
            total_likes = c.fetchone()[0]
            conn.close()
            msg = f"Пользователей: {total_users}\nЛайков: {total_likes}"
            send_message(chat_id, msg)
            return "OK"

    return "OK"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

import os
import logging
import sqlite3
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

# Подключение к базе
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    name TEXT, gender TEXT, age TEXT, city TEXT,
    goal TEXT, about TEXT, photo TEXT, step TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS likes (
    from_id INTEGER, to_id INTEGER
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS vip (
    chat_id INTEGER PRIMARY KEY
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS coins (
    chat_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0
)""")

conn.commit()

# Шаги анкеты
steps = ["name", "gender", "age", "city", "goal", "about", "photo"]

def send_message(chat_id, text, buttons=None):
    data = {"chat_id": chat_id, "text": text}
    if buttons:
        data["reply_markup"] = {"keyboard": buttons, "resize_keyboard": True}
    requests.post(f"{API_URL}/sendMessage", json=data)

def send_inline(chat_id, text, keyboard):
    requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {"inline_keyboard": keyboard}
    })

def send_photo(chat_id, file_id, caption, inline_keyboard=None):
    payload = {
        "chat_id": chat_id,
        "photo": file_id,
        "caption": caption
    }
    if inline_keyboard:
        payload["reply_markup"] = {"inline_keyboard": inline_keyboard}
    requests.post(f"{API_URL}/sendPhoto", json=payload)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        photo = message.get("photo", None)

        # START
        if text == "/start":
            cursor.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
            cursor.execute("INSERT OR REPLACE INTO users (chat_id, step) VALUES (?, ?)", (chat_id, "name"))
            conn.commit()
            send_message(chat_id, "Привет! Как тебя зовут?")
            return "OK"

        # ADMIN
        if text == "/admin":
            total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            total_likes = cursor.execute("SELECT COUNT(*) FROM likes").fetchone()[0]
            total_matches = cursor.execute("SELECT COUNT(*) FROM (SELECT from_id FROM likes GROUP BY from_id, to_id HAVING COUNT(*) > 1)").fetchone()[0]
            total_vip = cursor.execute("SELECT COUNT(*) FROM vip").fetchone()[0]
            total_coins = cursor.execute("SELECT SUM(balance) FROM coins").fetchone()[0] or 0
            msg = f"Пользователей: {total_users}
Лайков: {total_likes}
Совпадений: {total_matches}
VIP: {total_vip}
Монет всего: {total_coins}"
            send_message(chat_id, msg)
            return "OK"

        # Обработка анкеты
        user = cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,)).fetchone()
        if user:
            step = user[-1]
            col = steps[steps.index(step)]
            if step != "photo":
                cursor.execute(f"UPDATE users SET {col} = ?, step = ? WHERE chat_id = ?",
                               (text, steps[steps.index(step)+1] if step != "about" else "photo", chat_id))
                conn.commit()
                prompts = {
                    "gender": "Укажи пол:",
                    "age": "Сколько тебе лет?",
                    "city": "Из какого ты города?",
                    "goal": "Какая цель знакомства?",
                    "about": "Расскажи немного о себе:",
                    "photo": "Теперь отправь фото:"
                }
                send_message(chat_id, prompts.get(steps[steps.index(step)+1], ""))
            elif photo:
                file_id = photo[-1]["file_id"]
                cursor.execute("UPDATE users SET photo = ?, step = NULL WHERE chat_id = ?", (file_id, chat_id))
                cursor.execute("INSERT OR IGNORE INTO coins (chat_id, balance) VALUES (?, ?)", (chat_id, 5))
                conn.commit()
                send_message(chat_id, "Анкета сохранена!", buttons=[
                    [{"text": "🔍 Поиск анкет"}, {"text": "♻️ Начать заново"}],
                    [{"text": "✏️ Редактировать"}, {"text": "💰 Баланс"}]
                ])
            return "OK"

        # Команды после анкеты
        if text == "♻️ Начать заново":
            cursor.execute("UPDATE users SET step = 'name' WHERE chat_id = ?", (chat_id,))
            send_message(chat_id, "Как тебя зовут?")
            return "OK"

        if text == "✏️ Редактировать":
            cursor.execute("UPDATE users SET step = 'name' WHERE chat_id = ?", (chat_id,))
            send_message(chat_id, "Редактируем. Как тебя зовут?")
            return "OK"

        if text == "💰 Баланс":
            coins = cursor.execute("SELECT balance FROM coins WHERE chat_id = ?", (chat_id,)).fetchone()
            vip = cursor.execute("SELECT 1 FROM vip WHERE chat_id = ?", (chat_id,)).fetchone()
            msg = f"Монет: {coins[0] if coins else 0}
VIP: {'Да' if vip else 'Нет'}"
            send_message(chat_id, msg)
            return "OK"

        if text == "🔍 Поиск анкет":
            shown = []
            liked = cursor.execute("SELECT to_id FROM likes WHERE from_id = ?", (chat_id,)).fetchall()
            shown = [x[0] for x in liked]
            candidates = cursor.execute("SELECT * FROM users WHERE chat_id != ? AND step IS NULL", (chat_id,)).fetchall()
            for c in candidates:
                if c[0] not in shown:
                    text = f"Имя: {c[1]}
Пол: {c[2]}
Возраст: {c[3]}
Город: {c[4]}
Цель: {c[5]}
О себе: {c[6]}"
                    inline = [[
                        {"text": "❤️", "callback_data": f"like_{c[0]}"},
                        {"text": "⏭", "callback_data": "skip"}
                    ]]
                    send_photo(chat_id, c[7], text, inline)
                    return "OK"
            send_message(chat_id, "Анкет больше нет.")
            return "OK"

    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["from"]["id"]
        data = query["data"]

        if data.startswith("like_"):
            liked_id = int(data.split("_")[1])
            cursor.execute("INSERT INTO likes (from_id, to_id) VALUES (?, ?)", (chat_id, liked_id))
            conn.commit()
            # Проверка на взаимность
            match = cursor.execute("SELECT 1 FROM likes WHERE from_id = ? AND to_id = ?", (liked_id, chat_id)).fetchone()
            if match:
                send_message(chat_id, "Это взаимно!")
                send_message(liked_id, "Это взаимно!")
                cursor.execute("UPDATE coins SET balance = balance + 1 WHERE chat_id = ?", (chat_id,))
                cursor.execute("UPDATE coins SET balance = balance + 1 WHERE chat_id = ?", (liked_id,))
                conn.commit()
            send_message(chat_id, "Лайк отправлен!")
        elif data == "skip":
            send_message(chat_id, "Пропущено.")
        return "OK"

    return "OK"

@app.route("/", methods=["GET"])
def index():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

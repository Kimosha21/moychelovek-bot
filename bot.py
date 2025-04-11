import os
import json
import time
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
like_limits = {}
search_filters = {}

MAX_LIKES_PER_DAY = 10

def reset_likes_daily():
    current_day = int(time.time() // 86400)
    if like_limits.get("day") != current_day:
        like_limits.clear()
        like_limits["day"] = current_day

def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API_URL}/sendMessage", json=data)

def send_photo(chat_id, photo_path, caption=None, reply_markup=None):
    with open(photo_path, "rb") as photo:
        data = {"chat_id": chat_id, "caption": caption}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        files = {"photo": photo}
        requests.post(f"{API_URL}/sendPhoto", data=data, files=files)
        @app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    reset_likes_daily()

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        user = users.get(chat_id, {})
        state = user.get("state")

        if "text" in message:
            text = message["text"]

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
                            elif state == "filter_gender":
                search_filters[chat_id] = {"gender": text}
                users[chat_id]["state"] = "filter_age"
                send_message(chat_id, "Укажи возрастной диапазон (например, 20-30):")
            elif state == "filter_age":
                try:
                    min_age, max_age = map(int, text.split("-"))
                    search_filters[chat_id]["min_age"] = min_age
                    search_filters[chat_id]["max_age"] = max_age
                    users[chat_id]["state"] = "filter_city"
                    send_message(chat_id, "Укажи город (или напиши 'любой'):")
                except:
                    send_message(chat_id, "Неверный формат. Введи возраст как 20-30:")
            elif state == "filter_city":
                search_filters[chat_id]["city"] = text
                users[chat_id]["state"] = "done"
                show_profile(chat_id)

        elif "photo" in message and state == "photo":
            file_id = message["photo"][-1]["file_id"]
            file_info = requests.get(f"{API_URL}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            photo_data = requests.get(file_url).content
            photo_filename = f"{chat_id}.jpg"
            with open(photo_filename, "wb") as f:
                f.write(photo_data)
            profile = {
                "chat_id": chat_id,
                "name": users[chat_id]["name"],
                "gender": users[chat_id]["gender"],
                "age": users[chat_id]["age"],
                "city": users[chat_id]["city"],
                "goal": users[chat_id]["goal"],
                "about": users[chat_id]["about"],
                "photo_path": photo_filename
            }
            profiles.append(profile)
            coins[chat_id] = 10
            caption = f"Имя: {profile['name']}\nПол: {profile['gender']}\nВозраст: {profile['age']}\nГород: {profile['city']}\nЦель: {profile['goal']}\nО себе: {profile['about']}"
            send_photo(chat_id, photo_filename, caption)
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔍 Поиск анкет", "callback_data": "search"}],
                    [{"text": "✏️ Редактировать анкету", "callback_data": "edit"}],
                    [{"text": "♻️ Начать заново", "callback_data": "reset"}],
                    [{"text": "⭐ Купить VIP (5 монет)", "callback_data": "buy_vip"}]
                ]
            }
            send_message(chat_id, "Твоя анкета сохранена. Выбери действие:", reply_markup=keyboard)
            users[chat_id]["state"] = "done"
                elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        data = query["data"]

        if data == "reset":
            users[chat_id] = {"state": "name"}
            send_message(chat_id, "Анкета сброшена. Введи имя:")
        elif data == "search":
            users[chat_id]["state"] = "filter_gender"
            send_message(chat_id, "Кого ты хочешь найти? (мужской/женский)")
        elif data == "like":
            handle_like(chat_id)
        elif data == "edit":
            users[chat_id]["state"] = "name"
            send_message(chat_id, "Редактирование анкеты. Введи имя:")
        elif data == "buy_vip":
            if coins.get(chat_id, 0) >= 5:
                coins[chat_id] -= 5
                vip_users.add(chat_id)
                send_message(chat_id, "Ты приобрёл VIP-доступ!")
            else:
                send_message(chat_id, "Недостаточно монет. Нужно 5 монет.")

    return "OK"

def show_profile(chat_id):
    f = search_filters.get(chat_id, {})
    for profile in profiles:
        if profile["chat_id"] == chat_id:
            continue
        if f:
            if f["gender"].lower() != profile["gender"].lower():
                continue
            try:
                age = int(profile["age"])
                if not (f["min_age"] <= age <= f["max_age"]):
                    continue
            except:
                continue
            if f["city"].lower() != "любой" and f["city"].lower() != profile["city"].lower():
                continue
        caption = f"Имя: {profile['name']}\nПол: {profile['gender']}\nВозраст: {profile['age']}\nГород: {profile['city']}\nЦель: {profile['goal']}\nО себе: {profile['about']}"
        if profile["chat_id"] in vip_users:
            caption = "💎 VIP\n" + caption
        keyboard = {
            "inline_keyboard": [
                [{"text": "❤️ Лайк", "callback_data": "like"}],
                [{"text": "🔍 Следующий", "callback_data": "search"}]
            ]
        }
        send_photo(chat_id, profile["photo_path"], caption, reply_markup=keyboard)
        return
    send_message(chat_id, "Нет анкет по твоим фильтрам.")
def handle_like(chat_id):
    if chat_id in vip_users:
        send_message(chat_id, "Лайк засчитан! (VIP)")
    else:
        likes[chat_id] = likes.get(chat_id, 0) + 1
        remaining = MAX_LIKES_PER_DAY - likes[chat_id]
        if likes[chat_id] > MAX_LIKES_PER_DAY:
            send_message(chat_id, "Лимит лайков исчерпан. Купи VIP или подожди до завтра.")
            return
        send_message(chat_id, f"Ты поставил лайк! Осталось {remaining} из {MAX_LIKES_PER_DAY}.")
    show_profile(chat_id)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

import os
import json
import requests
import datetime
from flask import Flask, request

app = Flask(__name__)

TOKEN = "7559665369:AAEgac1ckHucHDKYr9zyiEcjnDMQGIkME8M"
API_URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL_USERNAME = "moychelovek61"
BOT_USERNAME = "moychelovek_bot"
DATA_DIR = "data"

os.makedirs(DATA_DIR, exist_ok=True)

def load_json(filename, default):
    path = os.path.join(DATA_DIR, filename)
    return json.load(open(path, "r", encoding="utf-8")) if os.path.exists(path) else default

def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users = load_json("users.json", {})
profiles = load_json("profiles.json", [])
likes = load_json("likes.json", {})
coins = load_json("coins.json", {})
vip_list = load_json("vip.json", [])
VIP_USERS = set(vip_list)
referrals = load_json("referrals.json", {})
daily_likes = {}
last_reset = datetime.date.today()

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API_URL}/sendMessage", json=payload)

def is_subscribed(user_id):
    resp = requests.get(f"{API_URL}/getChatMember?chat_id=@{CHANNEL_USERNAME}&user_id={user_id}")
    result = resp.json()
    return result.get("result", {}).get("status") in ["member", "creator", "administrator"]

def reset_likes_if_needed():
    global last_reset
    today = datetime.date.today()
    if today != last_reset:
        for uid in users:
            daily_likes[uid] = 10
        last_reset = today

def check_gender_match(user_gender, profile_gender):
    return (user_gender == "мужской" and profile_gender == "женский") or \
           (user_gender == "женский" and profile_gender == "мужской")
    @app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    reset_likes_if_needed()
    update = request.get_json()

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        photo = msg.get("photo")
        user = users.get(chat_id, {"state": "start"})
        state = user["state"]

        if not is_subscribed(chat_id):
            send_message(chat_id, "Пожалуйста, подпишись на канал @moychelovek61 чтобы пользоваться ботом.")
            return "ok"

        if text.startswith("/start") and "=" in text:
            ref_id = text.split("=")[1]
            if ref_id != str(chat_id) and str(chat_id) not in referrals:
                coins.setdefault(int(ref_id), 0)
                coins[int(ref_id)] += 3
                referrals[str(chat_id)] = ref_id
                save_json("coins.json", coins)
                save_json("referrals.json", referrals)

        if text == "/start":
            users[chat_id] = {"state": "name"}
            save_json("users.json", users)
            send_message(chat_id, "Привет! Введи своё имя:")
            return "ok"

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
        elif state == "photo" and photo:
            file_id = photo[-1]["file_id"]
            user["photo_id"] = file_id
            user["state"] = "done"
            users[chat_id] = user
            if chat_id not in profiles:
                profiles.append(chat_id)
            daily_likes[chat_id] = 10
            coins.setdefault(chat_id, 0)
            save_all()
            send_profile(chat_id, chat_id, own=True)
            return "ok"

        users[chat_id] = user
        save_json("users.json", users)

    elif "callback_query" in update:
        q = update["callback_query"]
        chat_id = q["from"]["id"]
        data = q["data"]

        if data == "start":
            users[chat_id] = {"state": "name"}
            save_json("users.json", users)
            send_message(chat_id, "Анкета сброшена. Введи имя:")
        elif data == "profile":
            send_profile(chat_id, chat_id, own=True)
        elif data == "like":
            show_next_profile(chat_id)
        elif data == "vip":
            if coins.get(chat_id, 0) >= 5:
                coins[chat_id] -= 5
                VIP_USERS.add(chat_id)
                save_json("coins.json", coins)
                save_json("vip.json", list(VIP_USERS))
                send_message(chat_id, "Поздравляем! Вы стали VIP.")
            else:
                send_message(chat_id, "Недостаточно монет (нужно 5).")
        elif data == "search":
            show_next_profile(chat_id)
        elif data == "edit":
            users[chat_id]["state"] = "name"
            save_json("users.json", users)
            send_message(chat_id, "Редактирование анкеты. Введи имя:")

    return "ok"

def show_next_profile(chat_id):
    user_gender = users[chat_id].get("gender", "").lower()
    age = users[chat_id].get("age", "")
    city = users[chat_id].get("city", "")
    for user_id in profiles:
        if user_id == chat_id:
            continue
        u = users.get(user_id)
        if not u: continue
        if chat_id in likes.get(user_id, []): continue
        if not check_gender_match(user_gender, u.get("gender", "")): continue
        if u.get("age", "") != age or u.get("city", "").lower() != city.lower(): continue

        if chat_id not in VIP_USERS and daily_likes.get(chat_id, 0) <= 0:
            send_message(chat_id, "У тебя закончились лайки на сегодня.")
            return
        likes.setdefault(user_id, []).append(chat_id)
        daily_likes[chat_id] -= 1
        coins[chat_id] += 1
        save_all()
        send_profile(chat_id, user_id)

        # Уведомление о взаимной симпатии
        if chat_id in likes.get(user_id, []):
            send_message(chat_id, "У вас взаимная симпатия!")
            send_message(user_id, "У вас взаимная симпатия!")
        return

    send_message(chat_id, "Анкет больше нет. Попробуй позже.")

def send_profile(chat_id, uid, own=False):
    u = users[uid]
    caption = f"<b>Имя:</b> {u['name']}\n<b>Пол:</b> {u['gender']}\n<b>Возраст:</b> {u['age']}\n<b>Город:</b> {u['city']}\n<b>Цель:</b> {u['goal']}\n<b>О себе:</b> {u['about']}\n"
    if uid in VIP_USERS: caption += "<b>VIP:</b> Да\n"
    caption += f"<b>Монеты:</b> {coins.get(uid, 0)}"

    keyboard = {"inline_keyboard": []}
    if own:
        keyboard["inline_keyboard"] += [
            [{"text": "🔍 Поиск", "callback_data": "search"}],
            [{"text": "✏️ Редактировать", "callback_data": "edit"}],
            [{"text": "♻️ Сбросить", "callback_data": "start"}],
            [{"text": "⭐ VIP (5 монет)", "callback_data": "vip"}]
        ]
    else:
        keyboard["inline_keyboard"].append([{"text": "❤️ Лайк", "callback_data": "like"}])

    requests.post(f"{API_URL}/sendPhoto", json={
        "chat_id": chat_id,
        "photo": u["photo_id"],
        "caption": caption,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(keyboard)
    })

def save_all():
    save_json("users.json", users)
    save_json("profiles.json", profiles)
    save_json("likes.json", likes)
    save_json("coins.json", coins)
    save_json("vip.json", list(VIP_USERS))
    save_json("referrals.json", referrals)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

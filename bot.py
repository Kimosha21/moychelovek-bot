
import os
import json
import logging
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"
DATA_FILE = "data/users.json"

users = {}
profiles = []
likes = {}
coins = {}
vip_users = set()

def load_data():
    global profiles, coins, vip_users
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            profiles.extend(data.get("profiles", []))
            coins.update(data.get("coins", {}))
            vip_users.update(data.get("vip_users", []))

def save_data():
    data = {
        "profiles": profiles,
        "coins": coins,
        "vip_users": list(vip_users)
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API_URL}/sendMessage", json=data)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        photo = message.get("photo")

        user = users.get(chat_id, {"step": "name"})
        step = user["step"]

        if text == "/start":
            users[chat_id] = {"step": "name"}
            send_message(chat_id, "ÐÑÐ¸Ð²ÐµÑ! ÐÐ°Ðº ÑÐµÐ±Ñ Ð·Ð¾Ð²ÑÑ?")
        elif step == "name":
            user["name"] = text
            user["step"] = "gender"
            send_message(chat_id, "Ð£ÐºÐ°Ð¶Ð¸ Ð¿Ð¾Ð» (Ð¼ÑÐ¶ÑÐºÐ¾Ð¹/Ð¶ÐµÐ½ÑÐºÐ¸Ð¹):")
        elif step == "gender":
            user["gender"] = text
            user["step"] = "age"
            send_message(chat_id, "Ð£ÐºÐ°Ð¶Ð¸ Ð²Ð¾Ð·ÑÐ°ÑÑ:")
        elif step == "age":
            user["age"] = text
            user["step"] = "city"
            send_message(chat_id, "ÐÐ· ÐºÐ°ÐºÐ¾Ð³Ð¾ ÑÑ Ð³Ð¾ÑÐ¾Ð´Ð°?")
        elif step == "city":
            user["city"] = text
            user["step"] = "goal"
            send_message(chat_id, "ÐÐ°ÐºÐ¾Ð²Ð° ÑÐµÐ»Ñ Ð·Ð½Ð°ÐºÐ¾Ð¼ÑÑÐ²Ð°?")
        elif step == "goal":
            user["goal"] = text
            user["step"] = "about"
            send_message(chat_id, "Ð Ð°ÑÑÐºÐ°Ð¶Ð¸ Ð½ÐµÐ¼Ð½Ð¾Ð³Ð¾ Ð¾ ÑÐµÐ±Ðµ:")
        elif step == "about":
            user["about"] = text
            user["step"] = "photo"
            send_message(chat_id, "Ð¢ÐµÐ¿ÐµÑÑ Ð¾ÑÐ¿ÑÐ°Ð²Ñ ÑÐ²Ð¾Ñ ÑÐ¾ÑÐ¾Ð³ÑÐ°ÑÐ¸Ñ:")
        elif photo and step == "photo":
            file_id = photo[-1]["file_id"]
            user["photo"] = file_id
            user["step"] = "done"
            profile = {
                "id": chat_id,
                "name": user["name"],
                "gender": user["gender"],
                "age": user["age"],
                "city": user["city"],
                "goal": user["goal"],
                "about": user["about"],
                "photo": user["photo"]
            }
            profiles.append(profile)
            coins[str(chat_id)] = 5  # ÑÑÐ°ÑÑÐ¾Ð²ÑÐµ Ð¼Ð¾Ð½ÐµÑÑ
            msg = (
                f"ÐÐ½ÐºÐµÑÐ° ÑÐ¾ÑÑÐ°Ð½ÐµÐ½Ð°!

"
                f"ÐÐ¼Ñ: {profile['name']}
"
                f"ÐÐ¾Ð»: {profile['gender']}
"
                f"ÐÐ¾Ð·ÑÐ°ÑÑ: {profile['age']}
"
                f"ÐÐ¾ÑÐ¾Ð´: {profile['city']}
"
                f"Ð¦ÐµÐ»Ñ: {profile['goal']}
"
                f"Ð ÑÐµÐ±Ðµ: {profile['about']}"
            )
            send_message(chat_id, msg)
            keyboard = {
                "inline_keyboard": [
                    [{"text": "ð ÐÐ¾Ð¸ÑÐº Ð°Ð½ÐºÐµÑ", "callback_data": "search"}],
                    [{"text": "âï¸ Ð ÐµÐ´Ð°ÐºÑÐ¸ÑÐ¾Ð²Ð°ÑÑ Ð°Ð½ÐºÐµÑÑ", "callback_data": "edit"}],
                    [{"text": "â»ï¸ ÐÐ°ÑÐ°ÑÑ Ð·Ð°Ð½Ð¾Ð²Ð¾", "callback_data": "restart"}]
                ]
            }
            send_message(chat_id, "ÐÑÐ±ÐµÑÐ¸ Ð´ÐµÐ¹ÑÑÐ²Ð¸Ðµ:", reply_markup=keyboard)
        users[chat_id] = user

    elif "callback_query" in update:
        query = update["callback_query"]
        data = query["data"]
        chat_id = query["message"]["chat"]["id"]

        if data == "search":
            for profile in profiles:
                if profile["id"] != chat_id:
                    msg = (
                        f"ÐÐ¼Ñ: {profile['name']}
"
                        f"ÐÐ¾Ð·ÑÐ°ÑÑ: {profile['age']}
"
                        f"ÐÐ¾ÑÐ¾Ð´: {profile['city']}
"
                        f"Ð ÑÐµÐ±Ðµ: {profile['about']}"
                    )
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "â¤ï¸", "callback_data": f"like_{profile['id']}"}],
                            [{"text": "â­", "callback_data": "search"}]
                        ]
                    }
                    requests.post(f"{API_URL}/sendPhoto", json={
                        "chat_id": chat_id,
                        "photo": profile["photo"],
                        "caption": msg,
                        "reply_markup": json.dumps(keyboard)
                    })
                    break
        elif data.startswith("like_"):
            liked_id = int(data.split("_")[1])
            likes.setdefault(liked_id, []).append(chat_id)
            send_message(chat_id, "Ð¢Ñ Ð»Ð°Ð¹ÐºÐ½ÑÐ» Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»Ñ!")
        elif data == "restart":
            users[chat_id] = {"step": "name"}
            send_message(chat_id, "ÐÐ½ÐºÐµÑÐ° ÑÐ±ÑÐ¾ÑÐµÐ½Ð°. ÐÐ°Ðº ÑÐµÐ±Ñ Ð·Ð¾Ð²ÑÑ?")
        elif data == "edit":
            users[chat_id] = {"step": "name"}
            send_message(chat_id, "Ð ÐµÐ´Ð°ÐºÑÐ¸ÑÑÐµÐ¼ Ð°Ð½ÐºÐµÑÑ. ÐÐ°Ðº ÑÐµÐ±Ñ Ð·Ð¾Ð²ÑÑ?")

    save_data()
    return "OK"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

if __name__ == "__main__":
    load_data()
    app.run(host="0.0.0.0", port=10000)

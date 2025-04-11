import os
import json
import logging
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"
ADMIN_ID = os.getenv("ADMIN_ID", "123456789")

DATA_FILE = "data.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"users": {}, "profiles": [], "likes": {}, "vip": [], "coins": {}}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
    data = load_data()

    if "message" in update:
        message = update["message"]
        chat_id = str(message["chat"]["id"])
        text = message.get("text", "")
        photo = message.get("photo")

        if text == "/start":
            data["users"][chat_id] = {"state": "name"}
            send_message(chat_id, "ÐÑÐ¸Ð²ÐµÑ! ÐÐ°Ðº ÑÐµÐ±Ñ Ð·Ð¾Ð²ÑÑ?")
            save_data(data)
            return "OK"

        if text == "/stats" and chat_id == ADMIN_ID:
            msg = f"ÐÐ¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»ÐµÐ¹: {len(data['users'])}
ÐÐ½ÐºÐµÑ: {len(data['profiles'])}"
            send_message(chat_id, msg)
            return "OK"

        user = data["users"].get(chat_id, {})
        state = user.get("state")

        if state == "name":
            user["name"] = text
            user["state"] = "gender"
            send_message(chat_id, "Ð£ÐºÐ°Ð¶Ð¸ Ð¿Ð¾Ð» (Ð¼ÑÐ¶ÑÐºÐ¾Ð¹/Ð¶ÐµÐ½ÑÐºÐ¸Ð¹):")
        elif state == "gender":
            user["gender"] = text
            user["state"] = "age"
            send_message(chat_id, "Ð¡ÐºÐ¾Ð»ÑÐºÐ¾ ÑÐµÐ±Ðµ Ð»ÐµÑ?")
        elif state == "age":
            user["age"] = text
            user["state"] = "city"
            send_message(chat_id, "ÐÐ· ÐºÐ°ÐºÐ¾Ð³Ð¾ ÑÑ Ð³Ð¾ÑÐ¾Ð´Ð°?")
        elif state == "city":
            user["city"] = text
            user["state"] = "goal"
            send_message(chat_id, "ÐÐ°ÐºÐ¾Ð²Ð° ÑÐµÐ»Ñ Ð·Ð½Ð°ÐºÐ¾Ð¼ÑÑÐ²Ð°?")
        elif state == "goal":
            user["goal"] = text
            user["state"] = "about"
            send_message(chat_id, "Ð Ð°ÑÑÐºÐ°Ð¶Ð¸ Ð½ÐµÐ¼Ð½Ð¾Ð³Ð¾ Ð¾ ÑÐµÐ±Ðµ:")
        elif state == "about":
            user["about"] = text
            user["state"] = "photo"
            send_message(chat_id, "Ð¢ÐµÐ¿ÐµÑÑ Ð¾ÑÐ¿ÑÐ°Ð²Ñ ÑÐ²Ð¾Ñ ÑÐ¾ÑÐ¾Ð³ÑÐ°ÑÐ¸Ñ:")
        elif state == "photo":
            send_message(chat_id, "ÐÐ´Ñ ÑÐ¾ÑÐ¾Ð³ÑÐ°ÑÐ¸Ñ...")
        else:
            send_message(chat_id, "ÐÐ°Ð¶Ð¼Ð¸ /start ÑÑÐ¾Ð±Ñ ÑÐ¾Ð·Ð´Ð°ÑÑ Ð°Ð½ÐºÐµÑÑ.")
        data["users"][chat_id] = user
        save_data(data)

    elif "photo" in update.get("message", {}):
        chat_id = str(update["message"]["chat"]["id"])
        photo_id = update["message"]["photo"][-1]["file_id"]
        user = data["users"].get(chat_id)

        if user and user.get("state") == "photo":
            profile = {
                "id": chat_id,
                "name": user["name"],
                "gender": user["gender"],
                "age": user["age"],
                "city": user["city"],
                "goal": user["goal"],
                "about": user["about"],
                "photo_id": photo_id
            }
            data["profiles"].append(profile)
            user["state"] = "done"
            send_message(chat_id, "Ð¡Ð¿Ð°ÑÐ¸Ð±Ð¾! Ð¢Ð²Ð¾Ñ Ð°Ð½ÐºÐµÑÐ° ÑÐ¾ÑÑÐ°Ð½ÐµÐ½Ð°.")
            keyboard = {
                "inline_keyboard": [
                    [{"text": "ð ÐÐ¾Ð¸ÑÐº Ð°Ð½ÐºÐµÑ", "callback_data": "search"}],
                    [{"text": "âï¸ Ð ÐµÐ´Ð°ÐºÑÐ¸ÑÐ¾Ð²Ð°ÑÑ Ð°Ð½ÐºÐµÑÑ", "callback_data": "edit"}],
                    [{"text": "â»ï¸ ÐÐ°ÑÐ°ÑÑ Ð·Ð°Ð½Ð¾Ð²Ð¾", "callback_data": "reset"}]
                ]
            }
            send_message(chat_id, "ÐÑÐ±ÐµÑÐ¸ Ð´ÐµÐ¹ÑÑÐ²Ð¸Ðµ:", reply_markup=keyboard)
            save_data(data)
            return "OK"

    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = str(query["message"]["chat"]["id"])
        data_value = query["data"]
        user = data["users"].get(chat_id, {})

        if data_value == "reset":
            data["users"][chat_id] = {"state": "name"}
            send_message(chat_id, "ÐÐ½ÐºÐµÑÐ° ÑÐ±ÑÐ¾ÑÐµÐ½Ð°. ÐÐ°Ðº ÑÐµÐ±Ñ Ð·Ð¾Ð²ÑÑ?")
        elif data_value == "edit":
            data["users"][chat_id] = {"state": "name"}
            send_message(chat_id, "ÐÐ°Ð²Ð°Ð¹ Ð¸Ð·Ð¼ÐµÐ½Ð¸Ð¼ Ð°Ð½ÐºÐµÑÑ. ÐÐ°Ðº ÑÐµÐ±Ñ Ð·Ð¾Ð²ÑÑ?")
        elif data_value == "search":
            matches = [p for p in data["profiles"] if p["id"] != chat_id]
            if matches:
                profile = matches[0]
                caption = f"ÐÐ¼Ñ: {profile['name']}
ÐÐ¾Ð·ÑÐ°ÑÑ: {profile['age']}
ÐÐ¾ÑÐ¾Ð´: {profile['city']}
Ð ÑÐµÐ±Ðµ: {profile['about']}"
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "â¤ï¸", "callback_data": f"like_{profile['id']}"}],
                        [{"text": "â­", "callback_data": "next"}]
                    ]
                }
                requests.post(f"{API_URL}/sendPhoto", json={
                    "chat_id": chat_id,
                    "photo": profile["photo_id"],
                    "caption": caption,
                    "reply_markup": keyboard
                })
            else:
                send_message(chat_id, "ÐÐ½ÐºÐµÑÑ Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½Ñ.")
        elif data_value.startswith("like_"):
            liked_id = data_value.split("_")[1]
            likes = data["likes"].setdefault(liked_id, [])
            if chat_id not in likes:
                likes.append(chat_id)
                send_message(chat_id, "Ð¢Ñ Ð»Ð°Ð¹ÐºÐ½ÑÐ» Ð°Ð½ÐºÐµÑÑ!")
                if chat_id in data["likes"].get(liked_id, []):
                    send_message(chat_id, "Ð£ Ð²Ð°Ñ Ð²Ð·Ð°Ð¸Ð¼Ð½ÑÐ¹ Ð»Ð°Ð¹Ðº!")
                    send_message(liked_id, "Ð£ Ð²Ð°Ñ Ð²Ð·Ð°Ð¸Ð¼Ð½ÑÐ¹ Ð»Ð°Ð¹Ðº!")
        elif data_value == "next":
            send_message(chat_id, "ÐÐ¾ÐºÐ°Ð·ÑÐ²Ð°Ñ ÑÐ»ÐµÐ´ÑÑÑÑÑ Ð°Ð½ÐºÐµÑÑ...")
        save_data(data)
    return "OK"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

import os
from flask import Flask, request
import requests

app = Flask(__name__)
TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

user_states = {}
profiles = []
likes = {}

def send_message(chat_id, text, buttons=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if buttons:
        data["reply_markup"] = {
            "keyboard": buttons,
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
    requests.post(f"{API_URL}/sendMessage", json=data)

def send_profile(chat_id, profile, with_buttons=True):
    caption = (
        f"Имя: {profile['name']}
"
        f"Пол: {profile['gender']}
"
        f"Возраст: {profile['age']}
"
        f"Город: {profile['city']}
"
        f"Цель: {profile['goal']}
"
        f"О себе: {profile['about']}"
    )
    buttons = [[
        {"text": "❤️ Лайк"},
        {"text": "⏭ Пропустить"}
    ]] if with_buttons else None
    requests.post(f"{API_URL}/sendPhoto", json={
        "chat_id": chat_id,
        "photo": profile["photo"],
        "caption": caption,
        "reply_markup": {"keyboard": buttons, "resize_keyboard": True} if buttons else None
    })

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if "message" in update:
        handle_message(update["message"])
    elif "callback_query" in update:
        handle_callback(update["callback_query"])
    return "OK"

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text")
    photo = message.get("photo")

    state = user_states.get(chat_id, {})
    step = state.get("step")

    if text == "/start" or text == "Старт заново":
        user_states[chat_id] = {"step": "name"}
        send_message(chat_id, "Привет! Как тебя зовут?", [["Редактировать анкету"]])
        return

    if text == "Редактировать анкету":
        user_states[chat_id] = {"step": "name"}
        send_message(chat_id, "Хорошо, начнём заново. Как тебя зовут?")
        return

    if text == "/поиск":
        show_next_profile(chat_id)
        return

    if step == "name":
        state["name"] = text
        state["step"] = "gender"
        send_message(chat_id, "Укажи пол (мужской/женский):")
    elif step == "gender":
        state["gender"] = text
        state["step"] = "age"
        send_message(chat_id, "Сколько тебе лет?")
    elif step == "age":
        state["age"] = text
        state["step"] = "city"
        send_message(chat_id, "Из какого ты города?")
    elif step == "city":
        state["city"] = text
        state["step"] = "goal"
        send_message(chat_id, "Какая у тебя цель знакомства?")
    elif step == "goal":
        state["goal"] = text
        state["step"] = "about"
        send_message(chat_id, "Расскажи немного о себе:")
    elif step == "about":
        state["about"] = text
        state["step"] = "photo"
        send_message(chat_id, "Теперь отправь своё фото.")
    elif step == "photo" and photo:
        file_id = photo[-1]["file_id"]
        state["photo"] = file_id
        state["chat_id"] = chat_id
        profiles.append(state)
        send_profile(chat_id, state, with_buttons=False)
        send_message(chat_id, "Анкета сохранена!", [["/поиск"]])
        user_states.pop(chat_id)
    elif text in ["❤️ Лайк", "⏭ Пропустить"]:
        handle_action(chat_id, text)

    user_states[chat_id] = state

def show_next_profile(chat_id):
    shown = likes.get(chat_id, {}).get("shown", [])
    candidates = [p for p in profiles if p["chat_id"] != chat_id and p["chat_id"] not in shown]
    if not candidates:
        send_message(chat_id, "Больше анкет пока нет.")
        return
    profile = candidates[0]
    send_profile(chat_id, profile)
    if chat_id not in likes:
        likes[chat_id] = {"shown": [], "liked": []}
    likes[chat_id]["shown"].append(profile["chat_id"])
    likes[chat_id]["last"] = profile["chat_id"]

def handle_action(chat_id, action):
    last = likes.get(chat_id, {}).get("last")
    if not last:
        send_message(chat_id, "Сначала начни с /поиск")
        return
    if action == "❤️ Лайк":
        likes[chat_id]["liked"].append(last)
        # проверим взаимность
        if last in likes and chat_id in likes[last]["liked"]:
            send_message(chat_id, "У вас взаимная симпатия!")
            send_message(last, "У вас взаимная симпатия!")
        else:
            send_message(chat_id, "Лайк отправлен!")
    elif action == "⏭ Пропустить":
        send_message(chat_id, "Анкета пропущена.")
    show_next_profile(chat_id)

@app.route("/", methods=["GET"])
def home():
    return "Бот работает"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


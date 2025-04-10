import os
import logging
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

user_states = {}
user_profiles = []

def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def send_photo(chat_id, photo_id, caption=""):
    requests.post(f"{API_URL}/sendPhoto", json={
        "chat_id": chat_id,
        "photo": photo_id,
        "caption": caption
    })

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]

        if "text" in message:
            text = message["text"]
            handle_text(chat_id, text)
        elif "photo" in message:
            handle_photo(chat_id, message)

    return "OK"

def handle_text(chat_id, text):
    state = user_states.get(chat_id, {"step": 0})

    if text == "/start":
        user_states[chat_id] = {"step": 1}
        send_message(chat_id, "Привет! Давай создадим твою анкету.\nКак тебя зовут?")
        return

    step = state["step"]

    if step == 1:
        state["name"] = text
        state["step"] = 2
        send_message(chat_id, "Укажи свой пол (мужской/женский):")

    elif step == 2:
        state["gender"] = text.lower()
        state["step"] = 3
        send_message(chat_id, "Сколько тебе лет?")

    elif step == 3:
        if not text.isdigit():
            send_message(chat_id, "Пожалуйста, введи число.")
            return
        state["age"] = int(text)
        state["step"] = 4
        send_message(chat_id, "Из какого ты города?")

    elif step == 4:
        state["city"] = text
        state["step"] = 5
        send_message(chat_id, "Какая у тебя цель знакомства?")

    elif step == 5:
        state["goal"] = text
        state["step"] = 6
        send_message(chat_id, "Напиши немного о себе:")

    elif step == 6:
        state["about"] = text
        state["step"] = 7
        send_message(chat_id, "Теперь отправь своё фото для анкеты:")

    elif step == 7:
        send_message(chat_id, "Пожалуйста, отправь фотографию, а не текст.")
        return

    user_states[chat_id] = state

def handle_photo(chat_id, message):
    state = user_states.get(chat_id)

    if not state or state.get("step") != 7:
        send_message(chat_id, "Пожалуйста, начни с команды /start")
        return

    photo = message["photo"][-1]  # Берём фото самого большого размера
    photo_id = photo["file_id"]
    state["photo_id"] = photo_id

    profile = {
        "name": state["name"],
        "gender": state["gender"],
        "age": state["age"],
        "city": state["city"],
        "goal": state["goal"],
        "about": state["about"],
        "photo_id": state["photo_id"]
    }

    user_profiles.append(profile)

    caption = (
        f"Анкета сохранена!\n\n"
        f"Имя: {profile['name']}\n"
        f"Пол: {profile['gender']}\n"
        f"Возраст: {profile['age']}\n"
        f"Город: {profile['city']}\n"
        f"Цель: {profile['goal']}\n"
        f"О себе: {profile['about']}"
    )

    send_photo(chat_id, profile['photo_id'], caption)
    send_message(chat_id, "Спасибо! Твоя анкета сохранена.")
    user_states.pop(chat_id)

@app.route("/", methods=["GET"])
def home():
    return "Бот работает"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

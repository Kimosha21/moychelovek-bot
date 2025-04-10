import os
import logging
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

user_states = {}  # Хранение промежуточных состояний
profiles = []     # Хранение готовых анкет


def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })


def send_photo(chat_id, photo_id, caption=None):
    requests.post(f"{API_URL}/sendPhoto", json={
        "chat_id": chat_id,
        "photo": photo_id,
        "caption": caption
    })


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" not in update:
        return "ok"

    message = update["message"]
    chat_id = message["chat"]["id"]

    if chat_id not in user_states:
        user_states[chat_id] = {"step": "name"}
        send_message(chat_id, "Привет! Давай создадим анкету. Как тебя зовут?")
        return "ok"

    state = user_states[chat_id]

    # Обработка фото
    if "photo" in message and state["step"] == "photo":
        photo_id = message["photo"][-1]["file_id"]
        state["photo"] = photo_id
        profiles.append(state.copy())

        caption = (
            f"Анкета сохранена!\n\n"
            f"Имя: {state['name']}\n"
            f"Пол: {state['gender']}\n"
            f"Возраст: {state['age']}\n"
            f"Город: {state['city']}\n"
            f"Цель: {state['goal']}\n"
            f"О себе: {state['about']}"
        )

        send_photo(chat_id, photo_id, caption)
        send_message(chat_id, "Спасибо! Твоя анкета сохранена.")
        user_states.pop(chat_id)
        return "ok"

    # Обработка текста
    if "text" in message:
        text = message["text"]

        if text == "/start":
            user_states[chat_id] = {"step": "name"}
            send_message(chat_id, "Привет! Как тебя зовут?")
            return "ok"

        if text == "/поиск":
            for profile in profiles:
                if profile["photo"] and profile["name"]:
                    caption = (
                        f"Имя: {profile['name']}\n"
                        f"Пол: {profile['gender']}\n"
                        f"Возраст: {profile['age']}\n"
                        f"Город: {profile['city']}\n"
                        f"Цель: {profile['goal']}\n"
                        f"О себе: {profile['about']}"
                    )
                    send_photo(chat_id, profile["photo"], caption)
                    return "ok"
            send_message(chat_id, "Пока нет анкет для показа.")
            return "ok"

        step = state["step"]

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
            send_message(chat_id, "Какова цель знакомства?")
        elif step == "goal":
            state["goal"] = text
            state["step"] = "about"
            send_message(chat_id, "Напиши немного о себе:")
        elif step == "about":
            state["about"] = text
            state["step"] = "photo"
            send_message(chat_id, "Теперь отправь своё фото для анкеты.")
        else:
            send_message(chat_id, "Ожидаю фото для завершения анкеты.")
    return "ok"


@app.route("/", methods=["GET"])
def home():
    return "Бот работает!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

import telebot
from telebot import types
from flask import Flask, request
import json
import os
import datetime

TOKEN = TOKEN = '7559665369:AAEgaC1ckHucHDKYr9zyiEcjnDMQGIkME8M'
CHANNEL_USERNAME = '@moychelovek'
DATA_FILE = 'moychelovek_data_20250415.json'

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({'profiles': {}, 'likes': {}, 'vip': {}, 'coins': {}, 'daily_likes': {}}, f)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def is_user_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'creator', 'administrator']
    except:
        return False

@app.route('/', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_json(force=True), bot)
    bot.process_new_updates([update])
    return 'ok'

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    data = load_data()

    if not is_user_subscribed(user_id):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        bot.send_message(chat_id, "Пожалуйста, подпишись на наш канал перед использованием бота.", reply_markup=keyboard)
        return

    if user_id not in data['coins']:
        data['coins'][str(user_id)] = 20  # стартовые монеты
    if str(user_id) not in data['daily_likes']:
        data['daily_likes'][str(user_id)] = {'count': 0, 'date': str(datetime.date.today())}
    save_data(data)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("Создать анкету", callback_data="create_profile"),
        types.InlineKeyboardButton("Поиск анкет", callback_data="search_profiles"),
    )
    keyboard.add(
        types.InlineKeyboardButton("Купить VIP (50 монет)", callback_data="buy_vip"),
        types.InlineKeyboardButton("Boosty / Поддержать", url="https://boosty.to/твоя_ссылка")
    )
    bot.send_message(chat_id, "Добро пожаловать в «Мой человек»!", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = str(call.from_user.id)
    chat_id = call.message.chat.id
    data = load_data()

    if call.data == "create_profile":
        msg = bot.send_message(chat_id, "Введи имя:")
        bot.register_next_step_handler(msg, lambda m: save_name(m, user_id))

    elif call.data == "search_profiles":
        show_next_profile(chat_id, user_id)

    elif call.data.startswith("like_"):
        liked_id = call.data.split("_")[1]
        today = str(datetime.date.today())
        daily = data['daily_likes'].get(user_id, {'count': 0, 'date': today})
        if daily['date'] != today:
            daily = {'count': 0, 'date': today}

        is_vip = data['vip'].get(user_id, False)
        if not is_vip and daily['count'] >= 10:
            bot.send_message(chat_id, "У тебя закончились лайки на сегодня. Купи VIP или подожди завтра.")
            return
        if liked_id not in data['likes'].get(user_id, []):
            data['likes'].setdefault(user_id, []).append(liked_id)
            if user_id in data['likes'].get(liked_id, []):
                bot.send_message(chat_id, "Взаимный лайк!")
        daily['count'] += 1
        data['daily_likes'][user_id] = daily
        save_data(data)
        show_next_profile(chat_id, user_id)

    elif call.data == "buy_vip":
        coins = data['coins'].get(user_id, 0)
        if coins >= 50:
            data['coins'][user_id] -= 50
            data['vip'][user_id] = True
            save_data(data)
            bot.send_message(chat_id, "Поздравляем! Ты стал VIP-пользователем.")
        else:
            bot.send_message(chat_id, f"Недостаточно монет. У тебя {coins}, нужно 50.")

def save_name(message, user_id):
    data = load_data()
    data['profiles'].setdefault(user_id, {})['name'] = message.text
    save_data(data)
    msg = bot.send_message(message.chat.id, "Введи возраст:")
    bot.register_next_step_handler(msg, lambda m: save_age(m, user_id))

def save_age(message, user_id):
    data = load_data()
    data['profiles'][user_id]['age'] = message.text
    save_data(data)
    msg = bot.send_message(message.chat.id, "Укажи город:")
    bot.register_next_step_handler(msg, lambda m: save_city(m, user_id))

def save_city(message, user_id):
    data = load_data()
    data['profiles'][user_id]['city'] = message.text
    save_data(data)
    bot.send_message(message.chat.id, "Анкета успешно создана!")

def show_next_profile(chat_id, current_user_id):
    data = load_data()
    for user_id, profile in data['profiles'].items():
        if user_id != current_user_id:
            text = f"Имя: {profile.get('name')}\nВозраст: {profile.get('age')}\nГород: {profile.get('city')}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("❤️ Лайк", callback_data=f"like_{user_id}"))
            bot.send_message(chat_id, text, reply_markup=keyboard)
            return
    bot.send_message(chat_id, "Пока нет доступных анкет.")
if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

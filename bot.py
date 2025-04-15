import telebot
from telebot import types
from flask import Flask, request
import json
import os
import datetime

TOKEN = '7559665369:AAEXLReINkB0r87FsvfHWmnHw7pwCgLUUi0'
CHANNEL_USERNAME = '@moychelovek61'
DATA_FILE = 'moychelovek_data.json'

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({
            'profiles': {}, 'likes': {}, 'vip': {},
            'coins': {}, 'daily_likes': {}, 'referrals': {}
        }, f)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def is_user_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

@app.route('/', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_json(force=True))
    if update.message:
        handle_message(update.message)
    elif update.callback_query:
        handle_callback(update.callback_query)
    return 'ok'

def handle_message(message):
    user_id = str(message.from_user.id)
    data = load_data()
    if message.text and message.text.startswith('/start'):
        if not is_user_subscribed(user_id):
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
            bot.send_message(message.chat.id, "Пожалуйста, подпишитесь на канал:", reply_markup=keyboard)
            return

        if user_id not in data['coins']:
            data['coins'][user_id] = 20
        if user_id not in data['vip']:
            data['vip'][user_id] = False
        if user_id not in data['daily_likes']:
            data['daily_likes'][user_id] = {'count': 0, 'date': str(datetime.date.today())}

        if message.text.startswith("/start ") and user_id not in data['referrals']:
            ref_id = message.text.split()[1]
            if ref_id != user_id:
                data['coins'][ref_id] = data['coins'].get(ref_id, 0) + 10
                data['referrals'][user_id] = ref_id
                bot.send_message(int(ref_id), "По твоей ссылке зарегистрировался пользователь! +10 монет")

        save_data(data)
        show_main_menu(message.chat.id)

    elif message.photo:
        data['profiles'][user_id]['photo'] = message.photo[-1].file_id
        save_data(data)
        bot.send_message(message.chat.id, "Фото получено и анкета сохранена!")
        show_main_menu(message.chat.id)

def show_main_menu(chat_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Создать анкету", callback_data="create"))
    keyboard.add(types.InlineKeyboardButton("Поиск анкет", callback_data="search"))
    keyboard.add(types.InlineKeyboardButton("Моя анкета", callback_data="my_profile"))
    keyboard.add(types.InlineKeyboardButton("Купить VIP (50 монет)", callback_data="buy_vip"))
    bot.send_message(chat_id, "Главное меню:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = str(call.from_user.id)
    chat_id = call.message.chat.id
    data = load_data()

    if call.data == "create":
        data['profiles'][user_id] = {}
        save_data(data)
        bot.send_message(chat_id, "Введи имя:")
        bot.register_next_step_handler_by_chat_id(chat_id, lambda m: save_field(m, user_id, "name"))
    elif call.data == "search":
        show_next_profile(chat_id, user_id)
    elif call.data == "my_profile":
        show_profile(chat_id, user_id)
    elif call.data.startswith("like_"):
        liked_id = call.data.split("_")[1]
        today = str(datetime.date.today())
        daily = data['daily_likes'].get(user_id, {'count': 0, 'date': today})
        if daily['date'] != today:
            daily = {'count': 0, 'date': today}
        is_vip = data['vip'].get(user_id, False)
        if not is_vip and daily['count'] >= 10:
            bot.send_message(chat_id, "У тебя закончились лайки на сегодня.")
            return
        data['likes'].setdefault(user_id, [])
        if liked_id not in data['likes'][user_id]:
            data['likes'][user_id].append(liked_id)
            if user_id in data['likes'].get(liked_id, []):
                bot.send_message(chat_id, "Это взаимный лайк!")
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
            bot.send_message(chat_id, "Поздравляем, теперь ты VIP!")
        else:
            bot.send_message(chat_id, f"Не хватает монет. У тебя: {coins}")

def save_field(message, user_id, field):
    data = load_data()
    data['profiles'].setdefault(user_id, {})[field] = message.text
    save_data(data)

    next_fields = {
        "name": "age",
        "age": "city",
        "city": "goal",
        "goal": "bio",
        "bio": "photo"
    }

    if field in next_fields:
        next_field = next_fields[field]
        if next_field == "photo":
            bot.send_message(message.chat.id, "Отправь своё фото:")
        else:
            bot.send_message(message.chat.id, f"Введи {next_field}:")
            bot.register_next_step_handler(message, lambda m: save_field(m, user_id, next_field))

def show_profile(chat_id, user_id):
    data = load_data()
    profile = data['profiles'].get(user_id)
    if not profile:
        bot.send_message(chat_id, "Анкета не найдена.")
        return
    text = (
        f"Имя: {profile.get('name')}\n"
        f"Возраст: {profile.get('age')}\n"
        f"Город: {profile.get('city')}\n"
        f"Цель: {profile.get('goal')}\n"
        f"Описание: {profile.get('bio')}\n"
        f"VIP: {'Да' if data['vip'].get(user_id) else 'Нет'}\n"
        f"Монеты: {data['coins'].get(user_id, 0)}"
    )
    if 'photo' in profile:
        bot.send_photo(chat_id, profile['photo'], caption=text)
    else:
        bot.send_message(chat_id, text)

def show_next_profile(chat_id, current_user_id):
    data = load_data()
    for user_id, profile in data['profiles'].items():
        if user_id != current_user_id and 'photo' in profile:
            text = (
                f"Имя: {profile.get('name')}\n"
                f"Возраст: {profile.get('age')}\n"
                f"Город: {profile.get('city')}\n"
                f"Цель: {profile.get('goal')}\n"
                f"Описание: {profile.get('bio')}\n"
                f"VIP: {'Да' if data['vip'].get(user_id) else 'Нет'}"
            )
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("❤️ Лайк", callback_data=f"like_{user_id}"))
            bot.send_photo(chat_id, profile['photo'], caption=text, reply_markup=keyboard)
            return
    bot.send_message(chat_id, "Анкет больше нет.")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

import os
import telebot
from flask import Flask, request
import sqlite3
import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и Flask
bot = telebot.TeleBot(os.environ['BOT_TOKEN'])
app = Flask(__name__)

# Пригласительная ссылка на канал
CHANNEL_INVITE_LINK = "https://t.me/+_58D1Ea_0WxjZTYy"

# Инициализация базы данных
def init_db():
    try:
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS applications
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER,
                     username TEXT,
                     first_name TEXT,
                     last_name TEXT,
                     date TEXT,
                     status TEXT DEFAULT 'new')''')
        conn.commit()
        conn.close()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка базы данных: {e}")

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user = message.from_user
        
        # Сохраняем заявку в базу
        application_id = save_application(user)
        
        welcome_text = """
🎉 Добро пожаловать в сеть ONIX!

Присоединяйтесь к нашему каналу:
"""
        
        # Создаем кнопку с ссылкой на канал
        markup = telebot.types.InlineKeyboardMarkup()
        channel_btn = telebot.types.InlineKeyboardButton(
            "📢 Перейти в канал ONIX", 
            url=CHANNEL_INVITE_LINK
        )
        markup.add(channel_btn)
        
        bot.send_message(
            message.chat.id, 
            welcome_text, 
            reply_markup=markup,
            disable_web_page_preview=True
        )
        
        logger.info(f"📨 Приглашение отправлено пользователю {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в send_welcome: {e}")
        bot.send_message(message.chat.id, "🎉 Добро пожаловать в сеть ONIX!")

# Обработка любого текстового сообщения
@bot.message_handler(content_types=['text'])
def handle_any_message(message):
    try:
        # Пропускаем команды
        if message.text.startswith('/'):
            return
        
        user = message.from_user
        
        # Сохраняем заявку в базу
        application_id = save_application(user)
        
        response_text = """
🎉 Добро пожаловать в сеть ONIX!

Присоединяйтесь к нашему каналу:
"""
        
        # Создаем кнопку с ссылкой на канал
        markup = telebot.types.InlineKeyboardMarkup()
        channel_btn = telebot.types.InlineKeyboardButton(
            "📢 Перейти в канал ONIX", 
            url=CHANNEL_INVITE_LINK
        )
        markup.add(channel_btn)
        
        bot.send_message(
            message.chat.id, 
            response_text, 
            reply_markup=markup,
            disable_web_page_preview=True
        )
        
        logger.info(f"📨 Приглашение отправлено пользователю {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_any_message: {e}")
        bot.send_message(message.chat.id, "🎉 Добро пожаловать в сеть ONIX!")

# Сохранение заявки в базу данных
def save_application(user):
    try:
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        
        # Проверяем, нет ли уже заявки от этого пользователя сегодня
        today = datetime.datetime.now().date().isoformat()
        c.execute("SELECT id FROM applications WHERE user_id = ? AND date LIKE ?", 
                 (user.id, f'{today}%'))
        
        existing_application = c.fetchone()
        
        if existing_application:
            conn.close()
            return existing_application[0]
        
        # Создаем новую заявку
        c.execute("""INSERT INTO applications 
                    (user_id, username, first_name, last_name, date) 
                    VALUES (?, ?, ?, ?, ?)""",
                (user.id, 
                 user.username, 
                 user.first_name, 
                 user.last_name,
                 datetime.datetime.now().isoformat()))
        
        application_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return application_id
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения заявки: {e}")
        return 0

# Webhook маршруты для Flask
@app.route('/')
def home():
    return "🤖 ONIX Network Bot is running on Render!"

@app.route('/health')
def health_check():
    return "✅ ONIX Bot is healthy and running!"

@app.route('/debug')
def debug_info():
    bot_token_set = bool(os.environ.get('BOT_TOKEN'))
    
    return f"""
🐛 ONIX Bot Debug:
✅ Server: Running
🤖 Bot Token: {'✅ SET' if bot_token_set else '❌ MISSING'}
📢 Channel Link: {CHANNEL_INVITE_LINK}
"""

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Invalid content type', 403

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    try:
        # Получаем домен из переменной окружения Render
        render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
        if not render_url:
            return "RENDER_EXTERNAL_URL not set"
        
        webhook_url = f"{render_url}/webhook"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        return f"✅ Webhook установлен: {webhook_url}"
    except Exception as e:
        return f"❌ Ошибка установки webhook: {e}"

# Инициализация при запуске
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 ONIX Bot starting on port {port}")
    app.run(host='0.0.0.0', port=port)

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

# ID канала (нужно заменить на реальный)
CHANNEL_ID = os.environ.get('CHANNEL_ID', '-1001234567890')

# Инициализация базы данных для отслеживания заявок
def init_db():
    try:
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS user_applications
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER UNIQUE,
                     username TEXT,
                     first_name TEXT,
                     date TEXT)''')
        conn.commit()
        conn.close()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка базы данных: {e}")

# Проверка, подавал ли пользователь уже заявку
def has_user_applied(user_id):
    try:
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM user_applications WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"❌ Ошибка проверки заявки: {e}")
        return False

# Сохранение информации о подаче заявки
def save_application(user):
    try:
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO user_applications 
                    (user_id, username, first_name, date) 
                    VALUES (?, ?, ?, ?)""",
                (user.id, 
                 user.username, 
                 user.first_name,
                 datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения заявки: {e}")
        return False

# Создание рабочей пригласительной ссылки
def create_invite_link():
    try:
        # Создаем новую пригласительную ссылку БЕЗ member_limit
        invite_link = bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            creates_join_request=True  # Только запрос на вступление
        )
        return invite_link.invite_link
    except Exception as e:
        logger.error(f"❌ Ошибка создания ссылки: {e}")
        return None

# Команда /start - создает и отправляет рабочую ссылку
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user = message.from_user
        
        # Если уже подавал заявку - не отвечаем
        if has_user_applied(user.id):
            logger.info(f"🔇 Пользователь {user.id} уже получал ссылку - игнорируем")
            return
        
        # Создаем рабочую ссылку
        invite_link = create_invite_link()
        
        if not invite_link:
            bot.send_message(message.chat.id, "❌ Ошибка создания ссылки. Попробуйте позже.")
            return
        
        # Сохраняем информацию о заявке
        save_application(user)
        
        welcome_text = """
🎉 Добро пожаловать в сеть ONIX!

Нажмите на ссылку ниже чтобы подать заявку.
Бот автоматически примет вас в канал!
"""
        
        # Создаем кнопку с ссылкой
        markup = telebot.types.InlineKeyboardMarkup()
        channel_btn = telebot.types.InlineKeyboardButton(
            "📢 Подать заявку в ONIX", 
            url=invite_link
        )
        markup.add(channel_btn)
        
        bot.send_message(
            message.chat.id, 
            welcome_text, 
            reply_markup=markup
        )
        
        logger.info(f"📨 Ссылка отправлена пользователю {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в send_welcome: {e}")

# Обработчик заявок на вступление в канал
@bot.chat_join_request_handler()
def approve_join_request(chat_join_request):
    try:
        user = chat_join_request.from_user
        chat = chat_join_request.chat
        
        # Автоматически одобряем заявку
        bot.approve_chat_join_request(chat.id, user.id)
        
        logger.info(f"✅ Заявка одобрена для пользователя {user.id}")
        
        # Отправляем приветствие
        welcome_dm = "🎉 Поздравляем! Ваша заявка одобрена! Добро пожаловать в ONIX!"
        bot.send_message(user.id, welcome_dm)
        
    except Exception as e:
        logger.error(f"❌ Ошибка одобрения заявки: {e}")

# Обработка других сообщений - игнорируем
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_other_messages(message):
    try:
        user = message.from_user
        
        # Если уже получал ссылку - не отвечаем
        if has_user_applied(user.id):
            return
        
        # Перенаправляем на /start
        bot.send_message(message.chat.id, "Отправьте команду /start чтобы получить ссылку")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_other_messages: {e}")

# Webhook маршруты для Flask
@app.route('/')
def home():
    return "🤖 ONIX Network Bot is running!"

@app.route('/health')
def health_check():
    return "✅ ONIX Bot is healthy and running!"

@app.route('/debug')
def debug_info():
    bot_token_set = bool(os.environ.get('BOT_TOKEN'))
    channel_id_set = bool(CHANNEL_ID)
    
    return f"""
🐛 ONIX Bot Debug:
✅ Server: Running
🤖 Bot Token: {'✅ SET' if bot_token_set else '❌ MISSING'}
📢 Channel ID: {'✅ SET' if channel_id_set else '❌ MISSING'}
✅ Auto-approve: Enabled
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

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

# Фиксированная ссылка на канал
CHANNEL_INVITE_LINK = "https://t.me/+SuiqfrQqf0I2MGVi"

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

# Команда /start - показывает кнопку только если еще не подавал заявку
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user = message.from_user
        
        # Если уже подавал заявку - не отвечаем
        if has_user_applied(user.id):
            logger.info(f"🔇 Пользователь {user.id} уже подавал заявку - игнорируем")
            return
        
        welcome_text = """
🎉 Добро пожаловать в сеть ONIX!

Нажмите кнопку ниже чтобы подать заявку на вступление в канал.
Бот автоматически примет вашу заявку!

⚠️ Заявку можно подать только один раз.
"""
        
        # Создаем клавиатуру с кнопкой "Подать заявку"
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        application_btn = telebot.types.KeyboardButton('📝 Подать заявку')
        markup.add(application_btn)
        
        bot.send_message(
            message.chat.id, 
            welcome_text, 
            reply_markup=markup
        )
        
        logger.info(f"👤 Пользователь {user.id} запустил бота")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в send_welcome: {e}")

# Обработка кнопки "Подать заявку" - только один раз
@bot.message_handler(func=lambda message: message.text == '📝 Подать заявку')
def handle_application(message):
    try:
        user = message.from_user
        
        # Если уже подавал заявку - не отвечаем
        if has_user_applied(user.id):
            logger.info(f"🔇 Пользователь {user.id} уже подавал заявку - игнорируем")
            return
        
        # Сохраняем информацию о заявке
        save_application(user)
        
        success_text = """
✅ Заявка принята!

Теперь нажмите на ссылку ниже чтобы вступить в канал ONIX.
Бот автоматически примет вашу заявку в течение 1-2 секунд!
"""
        
        # Создаем кнопку с фиксированной ссылкой на канал
        markup = telebot.types.InlineKeyboardMarkup()
        channel_btn = telebot.types.InlineKeyboardButton(
            "📢 Вступить в ONIX", 
            url=CHANNEL_INVITE_LINK
        )
        markup.add(channel_btn)
        
        # Убираем клавиатуру с кнопкой "Подать заявку"
        remove_markup = telebot.types.ReplyKeyboardRemove()
        
        bot.send_message(
            message.chat.id, 
            success_text, 
            reply_markup=remove_markup
        )
        
        # Отправляем кнопку с ссылкой
        bot.send_message(
            message.chat.id,
            "Нажмите на кнопку ниже:",
            reply_markup=markup
        )
        
        logger.info(f"📨 Заявка сохранена для пользователя {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_application: {e}")

# Обработчик заявок на вступление в канал
@bot.chat_join_request_handler()
def approve_join_request(chat_join_request):
    try:
        user = chat_join_request.from_user
        chat = chat_join_request.chat
        
        # Автоматически одобряем заявку
        bot.approve_chat_join_request(chat.id, user.id)
        
        logger.info(f"✅ Заявка одобрена для пользователя {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка одобрения заявки: {e}")

# Обработка других текстовых сообщений - игнорируем если уже подавал заявку
@bot.message_handler(content_types=['text'])
def handle_other_messages(message):
    try:
        user = message.from_user
        
        # Пропускаем команды
        if message.text.startswith('/'):
            return
        
        # Если уже подавал заявку - не отвечаем
        if has_user_applied(user.id):
            logger.info(f"🔇 Пользователь {user.id} уже подавал заявку - игнорируем")
            return
        
        # Если пользователь пишет что-то кроме кнопки, показываем инструкцию
        instruction_text = """
ℹ️ Для подачи заявки в канал ONIX нажмите кнопку "📝 Подать заявку"

Если кнопка не видна, отправьте команду /start

⚠️ Заявку можно подать только один раз.
"""
        
        # Создаем клавиатуру с кнопкой "Подать заявку"
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        application_btn = telebot.types.KeyboardButton('📝 Подать заявку')
        markup.add(application_btn)
        
        bot.send_message(
            message.chat.id, 
            instruction_text, 
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_other_messages: {e}")

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
✅ Auto-approve: Enabled
✅ One-time application: Enabled
🔇 No repeat messages: Enabled
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

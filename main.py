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
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        application_btn = telebot.types.KeyboardButton('📝 Оставить заявку')
        markup.add(application_btn)
        
        welcome_text = """
🤖 Добро пожаловать!

Это бот для приема заявок. 

Для подачи заявки просто нажмите кнопку ниже ⬇️

*Ничего заполнять не нужно* - ваши данные передадутся автоматически.
        """
        
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')
        logger.info(f"User {message.from_user.id} started the bot")
    except Exception as e:
        logger.error(f"Error in send_welcome: {e}")

# Обработка кнопки "Оставить заявку"
@bot.message_handler(func=lambda message: message.text == '📝 Оставить заявку')
def handle_application(message):
    try:
        user = message.from_user
        
        # Сохраняем заявку в базу
        application_id = save_application(user)
        
        # Отправляем подтверждение пользователю
        success_text = f"""
✅ *Заявка принята!*

Спасибо, {user.first_name if user.first_name else 'пользователь'}! Ваша заявка *#{application_id}* успешно зарегистрирована.

Наш менеджер свяжется с вами в ближайшее время для уточнения деталей.

🕐 *Время подачи:* {datetime.datetime.now().strftime('%H:%M %d.%m.%Y')}
        """
        
        bot.send_message(message.chat.id, success_text, parse_mode='Markdown')
        
        # Уведомляем администратора
        notify_admin(user, application_id)
        
        logger.info(f"New application #{application_id} from user {user.id}")
        
    except Exception as e:
        logger.error(f"Error in handle_application: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка при отправке заявки. Попробуйте позже.")

# Сохранение заявки в базу данных
def save_application(user):
    try:
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        
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
        logger.error(f"Error saving application: {e}")
        return 0

# Уведомление администратора
def notify_admin(user, application_id):
    try:
        admin_chat_id = os.environ.get('ADMIN_CHAT_ID')
        
        if not admin_chat_id:
            logger.warning("ADMIN_CHAT_ID not set")
            return
        
        admin_message = f"""
🚀 *НОВАЯ ЗАЯВКА!* #{application_id}

👤 *Клиент:* {user.first_name or ''} {user.last_name or ''}
📱 *Username:* @{user.username if user.username else 'не указан'}
🆔 *User ID:* {user.id}
📅 *Время:* {datetime.datetime.now().strftime('%H:%M %d.%m.%Y')}

*Срочно связаться!*
        """
        
        bot.send_message(admin_chat_id, admin_message, parse_mode='Markdown')
        logger.info(f"Admin notified about application #{application_id}")
        
    except Exception as e:
        logger.error(f"Error notifying admin: {e}")

# Команда для администратора - статистика
@bot.message_handler(commands=['stats'])
def show_stats(message):
    try:
        admin_chat_id = os.environ.get('ADMIN_CHAT_ID')
        
        if str(message.chat.id) != admin_chat_id:
            return
        
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        
        # Общее количество заявок
        c.execute("SELECT COUNT(*) FROM applications")
        total_applications = c.fetchone()[0]
        
        # Заявки за сегодня
        today = datetime.datetime.now().date().isoformat()
        c.execute("SELECT COUNT(*) FROM applications WHERE date LIKE ?", (f'{today}%',))
        today_applications = c.fetchone()[0]
        
        conn.close()
        
        stats_text = f"""
📊 *Статистика заявок*

📈 *Всего заявок:* {total_applications}
📅 *За сегодня:* {today_applications}
⏰ *Обновлено:* {datetime.datetime.now().strftime('%H:%M %d.%m.%Y')}
        """
        
        bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in show_stats: {e}")

# Webhook маршруты для Flask
@app.route('/')
def home():
    return "🤖 Telegram Application Bot is running!"

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
        # Получаем домен из переменной окружения
        railway_url = os.environ.get('RAILWAY_STATIC_URL', '')
        if not railway_url:
            return "RAILWAY_STATIC_URL not set"
        
        webhook_url = f"https://{railway_url}/webhook"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        return f"Webhook set to: {webhook_url}"
    except Exception as e:
        return f"Error setting webhook: {e}"

# Инициализация при запуске
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

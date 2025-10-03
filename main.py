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
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка базы данных: {e}")

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        # Автоматически создаем заявку при /start
        user = message.from_user
        application_id = save_application(user)
        
        welcome_text = """
🎉 Добро пожаловать в сеть ONIX!

Ваша заявка принята автоматически. 
Наш специалист свяжется с вами в ближайшее время.

Благодарим за выбор нашей сети!
        """
        
        bot.send_message(message.chat.id, welcome_text)
        
        # Уведомляем администратора
        notify_admin(user, application_id)
        
        logger.info(f"📨 Автоматическая заявка #{application_id} от {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в send_welcome: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте позже.")

# Обработка кнопки "Оставить заявку" (если нужно оставить)
@bot.message_handler(func=lambda message: message.text == '📝 Оставить заявку')
def handle_application(message):
    try:
        user = message.from_user
        
        # Сохраняем заявку в базу
        application_id = save_application(user)
        
        # Отправляем сообщение пользователю
        success_text = """
🎉 Добро пожаловать в сеть ONIX!

Ваша заявка принята. 
Наш специалист свяжется с вами в ближайшее время.

Благодарим за выбор нашей сети!
        """
        
        bot.send_message(message.chat.id, success_text)
        
        # Уведомляем администратора
        notify_admin(user, application_id)
        
        logger.info(f"📨 Новая заявка #{application_id} от пользователя {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_application: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте позже.")

# Обработка любого текстового сообщения (автоматическое создание заявки)
@bot.message_handler(content_types=['text'])
def handle_any_message(message):
    try:
        # Пропускаем команды и кнопки
        if message.text.startswith('/') or message.text == '📝 Оставить заявку':
            return
        
        user = message.from_user
        
        # Создаем заявку на любое сообщение
        application_id = save_application(user)
        
        response_text = """
🎉 Добро пожаловать в сеть ONIX!

Ваша заявка принята автоматически. 
Наш специалист свяжется с вами в ближайшее время.

Благодарим за выбор нашей сети!
        """
        
        bot.send_message(message.chat.id, response_text)
        
        # Уведомляем администратора
        notify_admin(user, application_id)
        
        logger.info(f"📨 Автоматическая заявка #{application_id} от {user.id} по сообщению")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_any_message: {e}")

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

# Уведомление администратора (без отправки в канал)
def notify_admin(user, application_id):
    try:
        admin_chat_id = os.environ.get('ADMIN_CHAT_ID')
        
        if not admin_chat_id:
            logger.warning("⚠️ ADMIN_CHAT_ID не установлен")
            return
        
        admin_message = f"""
🚀 НОВАЯ ЗАЯВКА В ONIX! #{application_id}

👤 Клиент: {user.first_name or ''} {user.last_name or ''}
📱 Username: @{user.username if user.username else 'не указан'}
🆔 User ID: {user.id}
📅 Время: {datetime.datetime.now().strftime('%H:%M %d.%m.%Y')}

Срочно связаться!
        """
        
        # Отправляем только администратору (не в канал)
        bot.send_message(admin_chat_id, admin_message)
        logger.info(f"📢 Админ уведомлен о заявке #{application_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка уведомления админа: {e}")

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
        
        # Уникальные пользователи за сегодня
        c.execute("SELECT COUNT(DISTINCT user_id) FROM applications WHERE date LIKE ?", (f'{today}%',))
        unique_users_today = c.fetchone()[0]
        
        conn.close()
        
        stats_text = f"""
📊 Статистика сети ONIX

📈 Всего заявок: {total_applications}
📅 Заявок сегодня: {today_applications}
👥 Уникальных пользователей сегодня: {unique_users_today}
⏰ Обновлено: {datetime.datetime.now().strftime('%H:%M %d.%m.%Y')}
        """
        
        bot.send_message(message.chat.id, stats_text)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в show_stats: {e}")

# Команда для получения ID чата
@bot.message_handler(commands=['id'])
def get_chat_id(message):
    chat_id = message.chat.id
    bot.send_message(message.chat.id, f"🆔 ID этого чата: {chat_id}")

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
    admin_id_set = bool(os.environ.get('ADMIN_CHAT_ID'))
    
    return f"""
🐛 ONIX Bot Debug:
✅ Server: Running
🤖 Bot Token: {'✅ SET' if bot_token_set else '❌ MISSING'}
👤 Admin ID: {'✅ SET' if admin_id_set else '❌ MISSING'}
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

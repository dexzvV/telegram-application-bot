import os
import telebot
from flask import Flask, request
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и Flask
bot = telebot.TeleBot(os.environ['BOT_TOKEN'])
app = Flask(__name__)

# Фиксированная ссылка на канал
CHANNEL_INVITE_LINK = "https://t.me/+87yO5xDdEUw2NWNi"

# Команда /start - отправляет ссылку
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        welcome_text = """
🎉 Добро пожаловать в сеть ONIX!

Нажмите на ссылку ниже чтобы подать заявку на вступление.
Бот автоматически примет вас в канал!
"""
        
        # Создаем кнопку со ссылкой
        markup = telebot.types.InlineKeyboardMarkup()
        channel_btn = telebot.types.InlineKeyboardButton(
            "📢 Подать заявку в ONIX", 
            url=CHANNEL_INVITE_LINK
        )
        markup.add(channel_btn)
        
        bot.send_message(
            message.chat.id, 
            welcome_text, 
            reply_markup=markup
        )
        
        logger.info(f"📨 Ссылка отправлена пользователю {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в send_welcome: {e}")

# Обработка любых сообщений - всегда отправляем ссылку
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_all_messages(message):
    try:
        # Пропускаем команды (чтобы /start не дублировался)
        if message.text and message.text.startswith('/'):
            return
            
        welcome_text = """
🎉 Добро пожаловать в сеть ONIX!

Нажмите на ссылку ниже чтобы подать заявку на вступление.
Бот автоматически примет вас в канал!
"""
        
        # Создаем кнопку со ссылкой
        markup = telebot.types.InlineKeyboardMarkup()
        channel_btn = telebot.types.InlineKeyboardButton(
            "📢 Подать заявку в ONIX", 
            url=CHANNEL_INVITE_LINK
        )
        markup.add(channel_btn)
        
        bot.send_message(
            message.chat.id, 
            welcome_text, 
            reply_markup=markup
        )
        
        logger.info(f"📨 Ссылка отправлена пользователю {message.from_user.id} по сообщению")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_all_messages: {e}")

# Обработчик заявок на вступление в канал
@bot.chat_join_request_handler()
def approve_join_request(chat_join_request):
    try:
        user = chat_join_request.from_user
        
        # Автоматически одобряем заявку
        bot.approve_chat_join_request(chat_join_request.chat.id, user.id)
        
        logger.info(f"✅ Заявка одобрена для пользователя {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка одобрения заявки: {e}")

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
    
    return f"""
🐛 ONIX Bot Debug:
✅ Server: Running
🤖 Bot Token: {'✅ SET' if bot_token_set else '❌ MISSING'}
📢 Channel Link: {CHANNEL_INVITE_LINK}
✅ Auto-approve: Enabled
🔄 Unlimited requests: Enabled
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
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 ONIX Bot starting on port {port}")
    app.run(host='0.0.0.0', port=port)

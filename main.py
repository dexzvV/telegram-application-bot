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
CHANNEL_INVITE_LINK = "https://t.me/+_58D1Ea_0WxjZTYy"

# Команда /start - показывает кнопку "Подать заявку"
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        welcome_text = """
🎉 Добро пожаловать в сеть ONIX!

Для подключения к нашему каналу нажмите кнопку "📝 Подать заявку" ниже.
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
        
        logger.info(f"👤 Пользователь {message.from_user.id} запустил бота")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в send_welcome: {e}")
        bot.send_message(message.chat.id, "🎉 Добро пожаловать в сеть ONIX!")

# Обработка кнопки "Подать заявку"
@bot.message_handler(func=lambda message: message.text == '📝 Подать заявку')
def handle_application(message):
    try:
        user = message.from_user
        
        success_text = """
✅ Заявка принята!

Добро пожаловать в сеть ONIX!
"""
        
        # Создаем кнопку с фиксированной ссылкой на канал
        markup = telebot.types.InlineKeyboardMarkup()
        channel_btn = telebot.types.InlineKeyboardButton(
            "📢 Перейти в канал ONIX", 
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
            "Нажмите на кнопку ниже чтобы присоединиться:",
            reply_markup=markup
        )
        
        logger.info(f"📨 Ссылка отправлена пользователю {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_application: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте позже.")

# Обработка других текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_other_messages(message):
    try:
        # Пропускаем команды
        if message.text.startswith('/'):
            return
        
        # Если пользователь пишет что-то кроме кнопки, показываем инструкцию
        instruction_text = """
ℹ️ Для подключения к каналу ONIX нажмите кнопку "📝 Подать заявку"

Если кнопка не видна, отправьте команду /start
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
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 ONIX Bot starting on port {port}")
    app.run(host='0.0.0.0', port=port)

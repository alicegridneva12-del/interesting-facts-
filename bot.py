import logging
import requests
import json
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackContext
)

#настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

CHOOSING, TYPING_REPLY = range(2)
CURRENT_CATEGORY = 'current_category'
USER_SETTINGS = 'user_settings'

class BotAPI:
    @staticmethod
    def get_random_fact():
        try:
            response = requests.get('https://uselessfacts.jsph.pl/random.json', timeout=5)
            if response.status_code == 200:
                return response.text
            #если вдруг не сработал первый API, вот второй
            response = requests.get('https://facts.bobthecow.org/random', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('text', 'Факт не найден')
                
        except:
            #е !вдруг! все API не работают, используем локальные факты
            facts = [
                "Медведи гризли могут бегать со скоростью до 50 км/ч",
                "Сердце кита бьется всего 9 раз в минуту",
                "Осьминоги имеют три сердца",
                "Страусы могут бегать быстрее лошадей",
                "Бабочки пробуют пищу ногами"
            ]
            return random.choice(facts)
    
    @staticmethod
    def get_weather(city):
        try:
            url = f'https://wttr.in/{city}?format=%C+%t'
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                weather_data = response.text.strip()
                return f"Погода в {city}: {weather_data}"
            else:
                #если !вдруг! API не работает, возвращаем тестовые данные 
                temperatures = ["+15°C солнечно", "+20°C облачно", "+10°C дождь", "+25°C ясно"]
                return f"Погода в {city}: {random.choice(temperatures)} (тестовые данные)"
                
        except Exception as e:
            logger.error(f"Ошибка погоды: {e}")
            # Всегда возвращаем какой-то ответ
            return f"Сейчас в {city} хорошая погода! (данные временно недоступны)"
    
    @staticmethod
    def get_exchange_rate():
        try:
            response = requests.get('https://api.exchangerate-api.com/v4/latest/RUB', timeout=5)
            if response.status_code == 200:
                data = response.json()
                usd = data['rates'].get('USD', 'Н/Д')
                eur = data['rates'].get('EUR', 'Н/Д')
                return f"Курс к рублю:\nUSD: {usd}\nEUR: {eur}"
            else:
                return "Курс валют:\nUSD: 90.5\nEUR: 98.2 (тестовые данные)"
                
        except:
            return "Курс валют временно недоступен. Попробуйте позже."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    keyboard = [
        ['Факт', 'Погода'],
        ['Курс', 'Настройки'],
        ['Помощь']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Привет, {user.first_name}!\nВыберите действие:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь"""
    help_text = (
        "Доступные команды:\n\n"
        "Факт - случайный интересный факт\n"
        "Погода <город> - узнать погоду\n"
        "Курс - курс валют\n"
        "Настройки - изменить настройки\n"
        "/cancel - отмена"
    )
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    text = update.message.text.lower()
    
    if 'факт' in text:
        fact = BotAPI.get_random_fact()
        await update.message.reply_text(f"📚 Факт:\n{fact}")
    
    elif 'погода' in text:
        if len(text.split()) == 1:
            await update.message.reply_text("Укажите город, например: Погода Москва")
        else:
            city = ' '.join(text.split()[1:]) 
            weather = BotAPI.get_weather(city)
            await update.message.reply_text(weather)
    
    elif 'курс' in text:
        rates = BotAPI.get_exchange_rate()
        await update.message.reply_text(rates)
    
    elif 'настройки' in text:
        keyboard = [['Имя', 'Город'], ['Готово']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Что изменить?",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif 'помощь' in text:
        await help_command(update, context)

async def settings_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор настройки"""
    text = update.message.text
    
    if text == 'Имя':
        context.user_data[CURRENT_CATEGORY] = 'Имя'
        await update.message.reply_text("Введите ваше имя:")
        return TYPING_REPLY
    elif text == 'Город':
        context.user_data[CURRENT_CATEGORY] = 'Город'
        await update.message.reply_text("Введите ваш город:")
        return TYPING_REPLY
    elif text == 'Готово':
        return await done(update, context)

async def save_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение настройки"""
    category = context.user_data.get(CURRENT_CATEGORY)
    value = update.message.text
    
    if USER_SETTINGS not in context.user_data:
        context.user_data[USER_SETTINGS] = {}
    
    context.user_data[USER_SETTINGS][category] = value
    
    keyboard = [['Имя', 'Город'], ['Готово']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Сохранено: {category} = {value}\nИзменить что-то еще?",
        reply_markup=reply_markup
    )
    return CHOOSING

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение настроек"""
    settings = context.user_data.get(USER_SETTINGS, {})
    
    if settings:
        text = "Настройки сохранены:\n"
        for key, value in settings.items():
            text += f"{key}: {value}\n"
    else:
        text = "Настройки не изменены"
    
    main_keyboard = [['Факт', 'Погода'], ['Курс', 'Настройки'], ['Помощь']]
    reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    
    await update.message.reply_text(text, reply_markup=reply_markup)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена"""
    main_keyboard = [['Факт', 'Погода'], ['Курс', 'Настройки'], ['Помощь']]
    reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    await update.message.reply_text("Отменено", reply_markup=reply_markup)
    return ConversationHandler.END

def main():
    TOKEN = "8275994353:AAF4hNv70ddHVkdcup0QHhJfpy7ry3Q2bOM"
    
    #создаем приложение!
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            CHOOSING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings_choice)
            ],
            TYPING_REPLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_setting)
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            MessageHandler(filters.Regex('^Готово$'), done)
        ]
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    application.add_handler(conv_handler)
    
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
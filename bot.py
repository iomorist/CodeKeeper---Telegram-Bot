import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Словарь для хранения кодов (в реальном приложении лучше использовать базу данных)
codes = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [InlineKeyboardButton("Добавить код", callback_data='add_code')],
        [InlineKeyboardButton("Просмотреть коды", callback_data='view_codes')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        'Привет! Я бот для хранения кодов лабораторных работ.\n'
        'Выберите действие:',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    if query.data == 'add_code':
        await query.message.reply_text(
            'Пожалуйста, отправьте код в следующем формате:\n'
            '/add <название_лабораторной> <код>'
        )
    elif query.data == 'view_codes':
        if not codes:
            await query.message.reply_text('У вас пока нет сохраненных кодов.')
        else:
            message = 'Сохраненные коды:\n\n'
            for lab_name, code in codes.items():
                message += f'📝 {lab_name}:\n```\n{code}\n```\n\n'
            await query.message.reply_text(message, parse_mode='Markdown')

async def add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /add"""
    try:
        # Разделяем сообщение на название и код
        _, lab_name, *code_parts = update.message.text.split(' ', 2)
        code = code_parts[0] if code_parts else ''
        
        if not code:
            await update.message.reply_text('Пожалуйста, укажите код после названия лабораторной работы.')
            return

        codes[lab_name] = code
        await update.message.reply_text(f'Код для лабораторной работы "{lab_name}" успешно сохранен!')
    except ValueError:
        await update.message.reply_text(
            'Неверный формат. Используйте:\n'
            '/add <название_лабораторной> <код>'
        )

def main():
    """Основная функция"""
    # Получаем токен из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logging.error("Не найден токен бота. Убедитесь, что он указан в файле .env")
        return

    # Создаем приложение
    application = Application.builder().token(token).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_code))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 
import os
import logging
import sqlite3
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Константы для пагинации
ITEMS_PER_PAGE = 5

# Состояния для ConversationHandler
SUBJECT, LAB_NUMBER, VARIANT, CODE = range(4)

# Временное хранилище данных
user_data = {}

def init_database():
    """Инициализация базы данных"""
    conn = sqlite3.connect('lab_codes.db')
    c = conn.cursor()
    # Создаем таблицу для хранения кодов, если она не существует
    c.execute('''
        CREATE TABLE IF NOT EXISTS codes
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         subject TEXT NOT NULL,
         lab_number TEXT NOT NULL,
         variant TEXT NOT NULL,
         code TEXT NOT NULL,
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    ''')
    conn.commit()
    conn.close()

def add_code_to_db(subject: str, lab_number: str, variant: str, code: str) -> bool:
    """Добавление кода в базу данных"""
    try:
        conn = sqlite3.connect('lab_codes.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO codes (subject, lab_number, variant, code) 
            VALUES (?, ?, ?, ?)
        ''', (subject, lab_number, variant, code))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Ошибка при добавлении кода в БД: {e}")
        return False

def get_codes_page(page: int) -> tuple:
    """Получение страницы кодов из базы данных"""
    try:
        conn = sqlite3.connect('lab_codes.db')
        c = conn.cursor()
        # Получаем общее количество записей
        c.execute('SELECT COUNT(*) FROM codes')
        total_count = c.fetchone()[0]
        
        # Получаем записи для текущей страницы
        offset = (page - 1) * ITEMS_PER_PAGE
        c.execute('SELECT id, subject, lab_number, variant, code FROM codes ORDER BY id LIMIT ? OFFSET ?', 
                 (ITEMS_PER_PAGE, offset))
        codes = c.fetchall()
        conn.close()
        
        total_pages = (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        return codes, total_pages
    except Exception as e:
        logging.error(f"Ошибка при получении кодов из БД: {e}")
        return [], 0

def get_all_codes_from_db() -> list:
    """Получение всех кодов из базы данных"""
    try:
        conn = sqlite3.connect('lab_codes.db')
        c = conn.cursor()
        c.execute('SELECT id, subject, lab_number, variant, code FROM codes ORDER BY id')
        codes = c.fetchall()
        conn.close()
        return codes
    except Exception as e:
        logging.error(f"Ошибка при получении кодов из БД: {e}")
        return []

def delete_code_from_db(lab_id: int) -> bool:
    """Удаление кода из базы данных по ID"""
    try:
        conn = sqlite3.connect('lab_codes.db')
        c = conn.cursor()
        c.execute('DELETE FROM codes WHERE id = ?', (lab_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Ошибка при удалении кода из БД: {e}")
        return False

def get_code_from_db(lab_id: int) -> tuple:
    """Получение кода по ID лабораторной"""
    try:
        conn = sqlite3.connect('lab_codes.db')
        c = conn.cursor()
        c.execute('''
            SELECT id, subject, lab_number, variant, code 
            FROM codes 
            WHERE id = ?
        ''', (lab_id,))
        result = c.fetchone()
        conn.close()
        return result
    except Exception as e:
        logging.error(f"Ошибка при получении кода из БД: {e}")
        return None

def update_code_in_db(lab_id: int, new_code: str) -> bool:
    """Обновление кода по ID лабораторной"""
    try:
        conn = sqlite3.connect('lab_codes.db')
        c = conn.cursor()
        c.execute('UPDATE codes SET code = ? WHERE id = ?', (new_code, lab_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Ошибка при обновлении кода в БД: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        'Привет! Я бот для хранения кодов лабораторных работ.\n\n'
        'Используйте команды:\n'
        '/add - Добавить новый код\n'
        '/list - Просмотреть все коды\n'
        '/edit <номер> <новый_код> - Редактировать код по номеру\n'
        '/delete <номер> - Удалить код по номеру\n'
        '/help - Показать справку'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "📚 Справка по использованию бота:\n\n"
        "/start - Начать работу с ботом\n"
        "/add - Добавить новый код (пошаговый ввод)\n"
        "/list - Просмотреть все сохраненные коды\n"
        "/edit <номер> <новый_код> - Редактировать код по номеру\n"
        "/delete <номер> - Удалить код по номеру\n"
        "/cancel - Отменить текущее действие\n"
        "/help - Показать эту справку\n\n"
        "При добавлении кода (/add) бот попросит ввести:\n"
        "1. Название предмета\n"
        "2. Номер лабораторной работы\n"
        "3. Вариант\n"
        "4. Сам код\n\n"
        "Примеры:\n"
        "/edit 1 print('New code')\n"
        "/delete 1"
    )
    await update.message.reply_text(help_text)

async def add_code_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса добавления кода"""
    await update.message.reply_text(
        'Пожалуйста, введите название предмета:'
    )
    return SUBJECT

async def add_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия предмета"""
    user_data[update.effective_user.id] = {'subject': update.message.text}
    await update.message.reply_text(
        'Теперь введите номер лабораторной работы:'
    )
    return LAB_NUMBER

async def add_lab_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка номера лабораторной"""
    user_data[update.effective_user.id]['lab_number'] = update.message.text
    await update.message.reply_text(
        'Введите вариант:'
    )
    return VARIANT

async def add_variant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка варианта"""
    user_data[update.effective_user.id]['variant'] = update.message.text
    await update.message.reply_text(
        'Теперь отправьте код лабораторной работы:'
    )
    return CODE

async def add_code_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Финальная обработка кода"""
    user_id = update.effective_user.id
    data = user_data.get(user_id, {})
    
    if not data:
        await update.message.reply_text(
            'Произошла ошибка. Пожалуйста, начните заново с команды /add'
        )
        return ConversationHandler.END
    
    code = update.message.text
    
    if add_code_to_db(data['subject'], data['lab_number'], data['variant'], code):
        await update.message.reply_text(
            f'✅ Код сохранен!\n'
            f'Предмет: {data["subject"]}\n'
            f'Лабораторная: {data["lab_number"]}\n'
            f'Вариант: {data["variant"]}'
        )
    else:
        await update.message.reply_text(
            '❌ Произошла ошибка при сохранении кода. Попробуйте позже.'
        )
    
    # Очищаем временные данные
    user_data.pop(user_id, None)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена процесса добавления кода"""
    user_id = update.effective_user.id
    user_data.pop(user_id, None)
    await update.message.reply_text(
        'Добавление кода отменено. Используйте /add для начала заново.'
    )
    return ConversationHandler.END

async def edit_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /edit"""
    try:
        _, lab_id, *code_parts = update.message.text.split(' ', 2)
        new_code = code_parts[0] if code_parts else ''
        
        if not new_code:
            await update.message.reply_text(
                'Пожалуйста, укажите новый код после номера лабораторной работы.\n'
                'Пример: /edit 1 print("New code")'
            )
            return

        # Проверяем, существует ли код
        lab_data = get_code_from_db(int(lab_id))
        if not lab_data:
            await update.message.reply_text(f'❌ Код с номером {lab_id} не найден.')
            return

        if update_code_in_db(int(lab_id), new_code):
            await update.message.reply_text(f'✅ Код для лабораторной работы "{lab_data[1]}" успешно обновлен!')
        else:
            await update.message.reply_text('❌ Произошла ошибка при обновлении кода. Попробуйте позже.')
    except (ValueError, IndexError):
        await update.message.reply_text(
            '❌ Неверный формат. Используйте:\n'
            '/edit <номер> <новый_код>'
        )

async def delete_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /delete"""
    try:
        _, lab_id = update.message.text.split(' ', 1)
        
        # Проверяем, существует ли код
        lab_data = get_code_from_db(int(lab_id))
        if not lab_data:
            await update.message.reply_text(f'❌ Код с номером {lab_id} не найден.')
            return

        if delete_code_from_db(int(lab_id)):
            await update.message.reply_text(f'✅ Код для лабораторной работы "{lab_data[1]}" успешно удален!')
        else:
            await update.message.reply_text('❌ Произошла ошибка при удалении кода. Попробуйте позже.')
    except (ValueError, IndexError):
        await update.message.reply_text(
            '❌ Неверный формат. Используйте:\n'
            '/delete <номер>'
        )

def create_pagination_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Создание клавиатуры для пагинации"""
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопки для каждой лабораторной работы
    codes, _ = get_codes_page(page)
    for lab_id, subject, lab_number, variant, _ in codes:
        keyboard.append([InlineKeyboardButton(f"📝 {subject} - Лаб. {lab_number} Вариант {variant}", callback_data=f"show_{lab_id}")])
    
    return InlineKeyboardMarkup(keyboard)

async def list_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /list"""
    subjects = get_subjects()
    if not subjects:
        await update.message.reply_text('📝 У вас пока нет сохраненных кодов.')
    else:
        message = '📚 Выберите предмет:'
        keyboard = create_subjects_keyboard()
        await update.message.reply_text(message, reply_markup=keyboard)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_subjects":
        message = '📚 Выберите предмет:'
        keyboard = create_subjects_keyboard()
        await query.message.edit_text(message, reply_markup=keyboard)
    
    elif query.data.startswith('subject_'):
        subject = query.data.split('_')[1]
        message = f'📚 Лабораторные работы по предмету "{subject}":'
        keyboard = create_labs_keyboard(subject)
        await query.message.edit_text(message, reply_markup=keyboard)
    
    elif query.data.startswith('show_'):
        lab_id = int(query.data.split('_')[1])
        lab_data = get_code_from_db(lab_id)
        
        if lab_data:
            message = (
                f'📝 Предмет: {lab_data[1]}\n'
                f'Лабораторная: {lab_data[2]}\n'
                f'Вариант: {lab_data[3]}\n'
                f'Код:\n```\n{lab_data[4]}\n```'
            )
            keyboard = [[InlineKeyboardButton("⬅️ Назад к лабораторным", callback_data=f"subject_{lab_data[1]}")]]
            await query.message.edit_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.message.edit_text('❌ Код не найден.')

def get_subjects() -> list:
    """Получение списка всех предметов"""
    try:
        conn = sqlite3.connect('lab_codes.db')
        c = conn.cursor()
        c.execute('SELECT DISTINCT subject FROM codes ORDER BY subject')
        subjects = [row[0] for row in c.fetchall()]
        conn.close()
        return subjects
    except Exception as e:
        logging.error(f"Ошибка при получении списка предметов: {e}")
        return []

def get_labs_by_subject(subject: str) -> list:
    """Получение списка лабораторных работ по предмету"""
    try:
        conn = sqlite3.connect('lab_codes.db')
        c = conn.cursor()
        c.execute('''
            SELECT id, lab_number, variant, code 
            FROM codes 
            WHERE subject = ? 
            ORDER BY lab_number, variant
        ''', (subject,))
        labs = c.fetchall()
        conn.close()
        return labs
    except Exception as e:
        logging.error(f"Ошибка при получении лабораторных работ: {e}")
        return []

def create_subjects_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры со списком предметов"""
    keyboard = []
    subjects = get_subjects()
    for subject in subjects:
        keyboard.append([InlineKeyboardButton(f"📚 {subject}", callback_data=f"subject_{subject}")])
    return InlineKeyboardMarkup(keyboard)

def create_labs_keyboard(subject: str) -> InlineKeyboardMarkup:
    """Создание клавиатуры со списком лабораторных работ"""
    keyboard = []
    labs = get_labs_by_subject(subject)
    for lab_id, lab_number, variant, _ in labs:
        keyboard.append([InlineKeyboardButton(
            f"📝 Лаб. {lab_number} Вариант {variant}", 
            callback_data=f"show_{lab_id}"
        )])
    keyboard.append([InlineKeyboardButton("⬅️ Назад к предметам", callback_data="back_to_subjects")])
    return InlineKeyboardMarkup(keyboard)

def main():
    """Основная функция"""
    # Инициализируем базу данных
    init_database()
    
    # Получаем токен из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logging.error("Не найден токен бота. Убедитесь, что он указан в файле .env")
        return

    # Создаем приложение
    application = Application.builder().token(token).build()

    # Создаем ConversationHandler для добавления кода
    add_code_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_code_start)],
        states={
            SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_subject)],
            LAB_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_lab_number)],
            VARIANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_variant)],
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_code_final)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(add_code_handler)
    application.add_handler(CommandHandler("edit", edit_code))
    application.add_handler(CommandHandler("delete", delete_code))
    application.add_handler(CommandHandler("list", list_codes))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Запускаем бота
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 
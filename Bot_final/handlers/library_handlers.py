from maxgram.keyboards import InlineKeyboard
from config import db, logger
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# Глобальные переменные для хранения состояния поиска книг
user_book_search = {}


def get_user_id(context):
    """Безопасное получение user_id для любого типа сообщений"""
    return context.message['recipient']['chat_id']



def start_book_search(context):
    """Начать поиск книги"""
    user_id = get_user_id(context)

    # Сохраняем состояние поиска
    user_book_search[user_id] = {'step': 'awaiting_search_query'}

    message = "🔍 Поиск книги\n\n"
    message += "Введи название или автора книги\n\n"
    message += "Пример: Преступление и наказание"

    # Используем правильный метод ответа в зависимости от типа контекста
    if hasattr(context, 'callback_query') and context.callback_query:
        context.reply_callback(message)
    else:
        context.reply(message)


def handle_book_search_query(context, text):
    """Обработка запроса на поиск книги"""
    user_id = get_user_id(context)

    if user_id not in user_book_search:
        start_book_search(context)
        return

    # Ищем книги в базе данных
    books = search_books(text)

    if not books:
        user_book_search[user_id] = {'step': 'awaiting_search_query'}

        keyboard = InlineKeyboard(
            [{"text": "🔍 Попробовать снова", "callback": "find_book"}],
            [{"text": "🏠 Главное меню", "callback": "back_to_menu"}]
        )

        message = "❌ Книга не найдена\n\n"
        message += "Попробуйте еще раз с другим названием или автором"

        # Используем правильный метод ответа
        if hasattr(context, 'callback_query') and context.callback_query:
            context.reply_callback(message, keyboard=keyboard)
        else:
            context.reply(message, keyboard=keyboard)
        return

    # Сохраняем результаты поиска
    user_book_search[user_id] = {
        'step': 'book_found',
        'search_results': books,
        'current_book_index': 0
    }

    # Показываем первую найденную книгу
    show_book_details(context, user_id, 0)


def show_book_details(context, user_id, book_index):
    """Показать детали книги"""
    if user_id not in user_book_search or 'search_results' not in user_book_search[user_id]:
        return

    books = user_book_search[user_id]['search_results']

    if book_index >= len(books):
        return

    book = books[book_index]
    user_book_search[user_id]['current_book_index'] = book_index

    message = f"📚 {book['title']}\n"
    message += f"✍️ Автор: {book['author']}\n"
    message += f"📖 Описание: {book['description'][:100]}...\n"
    message += f"📊 Доступно экземпляров: {book['available_copies']}/{book['total_copies']}\n"

    if book['is_digital'] and book['is_paper']:
        message += "💻 Доступна в электронном и бумажном виде\n"
    elif book['is_digital']:
        message += "💻 Доступна в электронном виде\n"
    else:
        message += "📗 Доступна только в бумажном виде\n"

    # Создаем клавиатуру
    keyboard_rows = []

    if book['is_digital']:
        keyboard_rows.append([{"text": "📱 Электронная версия", "callback": f"digital_book_{book['book_id']}"}])

    if book['is_paper']:
        keyboard_rows.append([{"text": "📖 Забронировать бумажную", "callback": f"reserve_book_{book['book_id']}"}])

    # Кнопки навигации если книг несколько
    if len(books) > 1:
        nav_buttons = []
        if book_index > 0:
            nav_buttons.append({"text": "⬅️ Предыдущая", "callback": f"prev_book_{book_index - 1}"})
        if book_index < len(books) - 1:
            nav_buttons.append({"text": "Следующая ➡️", "callback": f"next_book_{book_index + 1}"})
        if nav_buttons:
            keyboard_rows.append(nav_buttons)

    keyboard_rows.append([{"text": "🔍 Новый поиск", "callback": "find_book"}])
    keyboard_rows.append([{"text": "🏠 Главное меню", "callback": "back_to_menu"}])

    keyboard = InlineKeyboard(*keyboard_rows)

    # Используем правильный метод ответа
    if hasattr(context, 'callback_query') and context.callback_query:
        context.reply_callback(message, keyboard=keyboard)
    else:
        context.reply(message, keyboard=keyboard)


def handle_digital_book_request(context, book_id):
    """Обработка запроса электронной книги"""
    user_id = get_user_id(context)

    book = get_book_by_id(book_id)

    if not book or not book['is_digital']:
        context.reply_callback("❌ Электронная версия книги недоступна")
        return

    message = "✅ Отлично! Держи ссылку на прочтение:\n\n"
    message += f"🔗 {book['digital_link']}\n\n"
    message += "Приятного чтения! 📚"

    keyboard = InlineKeyboard(
        [{"text": "🔍 Найти другую книгу", "callback": "find_book"}],
        [{"text": "🏠 Главное меню", "callback": "back_to_menu"}]
    )

    context.reply_callback(message, keyboard=keyboard)


def handle_book_reservation(context, book_id):
    """Обработка бронирования бумажной книги"""
    user_id = get_user_id(context)

    book = get_book_by_id(book_id)

    if not book or book['available_copies'] <= 0:
        context.reply_callback("❌ К сожалению, эта книга сейчас недоступна для бронирования")
        return

    # Создаем бронирование
    reservation_id = create_book_reservation(book_id, user_id)

    if reservation_id:
        # Обновляем количество доступных книг
        update_book_availability(book_id, book['available_copies'] - 1)

        expiry_date = (datetime.now() + timedelta(days=7)).strftime("%d.%m.%Y")

        message = "✅ Книга забронирована за тобой!\n\n"
        message += f"📚 {book['title']}\n"
        message += f"✍️ {book['author']}\n"
        message += f"📅 Забрать в библиотеке до: {expiry_date}\n\n"
        message += "Не забудь взять с собой студенческий билет!"
    else:
        message = "❌ Произошла ошибка при бронировании. Попробуйте позже."

    keyboard = InlineKeyboard(
        [{"text": "🔍 Найти другую книгу", "callback": "find_book"}],
        [{"text": "🏠 Главное меню", "callback": "back_to_menu"}]
    )

    context.reply_callback(message, keyboard=keyboard)


def create_book_reservation(book_id, user_id):
    """Создать бронирование книги"""
    try:
        with db.conn.cursor() as cur:
            expiry_date = datetime.now() + timedelta(days=7)

            cur.execute("""
                INSERT INTO book_reservations (book_id, user_id, expiry_date) 
                VALUES (%s, %s, %s) 
                RETURNING reservation_id
            """, (book_id, user_id, expiry_date))

            reservation_id = cur.fetchone()[0]
            db.conn.commit()
            return reservation_id
    except Exception as e:
        logger.error(f"Ошибка создания бронирования: {e}")
        db.conn.rollback()
        return None


def update_book_availability(book_id, new_available):
    """Обновить количество доступных книг"""
    try:
        with db.conn.cursor() as cur:
            cur.execute("""
                UPDATE books 
                SET available_copies = %s 
                WHERE book_id = %s
            """, (new_available, book_id))
            db.conn.commit()
    except Exception as e:
        logger.error(f"Ошибка обновления доступности книги: {e}")
        db.conn.rollback()


def search_books(query):
    """Поиск книг по запросу"""
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            search_term = f"%{query}%"
            cur.execute("""
                SELECT * FROM books 
                WHERE title ILIKE %s OR author ILIKE %s 
                ORDER BY 
                    CASE 
                        WHEN title ILIKE %s THEN 1 
                        WHEN author ILIKE %s THEN 2 
                        ELSE 3 
                    END,
                    available_copies DESC
                LIMIT 10
            """, (search_term, search_term, search_term, search_term))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка поиска книг: {e}")
        return []


def get_book_by_id(book_id):
    """Получить книгу по ID"""
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
            return cur.fetchone()
    except Exception as e:
        logger.error(f"Ошибка получения книги: {e}")
        return None


def handle_navigation(context, book_index):
    """Обработка навигации по книгам"""
    user_id = get_user_id(context)
    show_book_details(context, user_id, book_index)
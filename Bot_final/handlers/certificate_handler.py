from config import db, logger
from psycopg2.extras import RealDictCursor
from maxgram.keyboards import InlineKeyboard
from handlers.notification_handler import create_notification
from handlers.authorization_handler import authenticated_users


def get_user_id(context):
    """Безопасное получение user_id для любого типа сообщений"""
    return context.message['recipient']['chat_id']



def get_db_user_id(chat_id):
    """Получает user_id из базы данных для авторизованного пользователя"""
    if chat_id in authenticated_users:
        user_data = authenticated_users[chat_id]
        if 'user_info' in user_data and 'user_id' in user_data['user_info']:
            return user_data['user_info']['user_id']
    return None



def handle_study_certificate_request(context):
    """Обработка запроса справки об обучении"""
    user_id = get_user_id(context)
    db_user_id = get_db_user_id(user_id)

    if not db_user_id:
        context.reply_callback("❌ Ошибка: пользователь не авторизован")
        return

    keyboard = InlineKeyboard(
        [{"text": "✅ Да, оформить", "callback": "select_certificate_delivery"}],
        [{"text": "❌ Отмена", "callback": "cancel_certificate"}]
    )

    message = "🎓 Справка об обучении\n\n"
    message += "Я могу оформить для тебя справку об обучении.\n\n"
    message += "Оформляем?"

    context.reply_callback(message, keyboard=keyboard)


def select_certificate_delivery(context):
    """Выбор способа получения справки"""
    user_id = get_user_id(context)
    db_user_id = get_db_user_id(user_id)

    if not db_user_id:
        context.reply_callback("❌ Ошибка: пользователь не авторизован")
        return

    keyboard = InlineKeyboard(
        [{"text": "💻 Электронная версия", "callback": "confirm_digital_certificate"}],
        [{"text": "🏢 Забрать в деканате", "callback": "confirm_office_certificate"}],
        [{"text": "❌ Отмена", "callback": "cancel_certificate"}]
    )

    message = "📋 Выбери способ получения справки:\n\n"
    message += "💻 Электронная версия - будет готова в течение 2 часов, пришлю ссылку для скачивания\n\n"
    message += "🏢 Забрать в деканате - будет готова через 1 рабочий день, пришлю уведомление когда можно забрать"

    context.reply_callback(message, keyboard=keyboard)


def confirm_digital_certificate(context):
    """Подтверждение оформления электронной справки"""
    user_id = get_user_id(context)
    db_user_id = get_db_user_id(user_id )

    if not db_user_id:
        context.reply_callback("❌ Ошибка: пользователь не авторизован")
        return

    # Создаем заявку в базе данных
    request_id = create_certificate_request(db_user_id, 'digital')

    if request_id:
        message = "✅ Справка оформлена в электронном виде.\n\n"
        message += "⏰ Ссылка для скачивания будет направлена в течение 2 часов.\n\n"
        message += "Справка будет с электронной подписью (ЭЦП)."

        # Имитируем обработку заявки
        process_digital_certificate_request(request_id, db_user_id )
    else:
        message = "❌ Произошла ошибка при оформлении справки. Попробуйте позже."

    keyboard = InlineKeyboard(
        [{"text": "🔍 Посмотреть статус", "callback": f"certificate_status_{request_id}"}],
        [{"text": "🏠 Главное меню", "callback": "back_to_menu"}]
    )

    context.reply_callback(message, keyboard=keyboard)


def confirm_office_certificate(context):
    """Подтверждение оформления справки для получения в деканате"""
    chat_id = get_user_id(context)
    db_user_id = get_db_user_id(chat_id)

    if not db_user_id:
        context.reply_callback("❌ Ошибка: пользователь не авторизован")
        return

    # Создаем заявку в базе данных
    request_id = create_certificate_request(db_user_id, 'office')

    if request_id:
        message = "✅ Справка оформлена для получения в деканате.\n\n"
        message += "⏰ Справка будет готова через 1 рабочий день.\n\n"
        message += "📍 Место получения: Деканат главного корпуса\n"
        message += "🕒 Часы работы: Пн-Пт с 9:00 до 17:00\n\n"
        message += "Я пришлю уведомление, когда справка будет готова к выдаче."

        # Имитируем обработку заявки
        process_office_certificate_request(request_id, db_user_id)
    else:
        message = "❌ Произошла ошибка при оформлении справки. Попробуйте позже."

    keyboard = InlineKeyboard(
        [{"text": "🔍 Посмотреть статус", "callback": f"certificate_status_{request_id}"}],
        [{"text": "🏠 Главное меню", "callback": "back_to_menu"}]
    )

    context.reply_callback(message, keyboard=keyboard)


def create_certificate_request(db_user_id, delivery_type, office_location="Деканат главного корпуса"):
    """Создать заявку на справку об обучении"""
    try:
        with db.conn.cursor() as cur:
            if delivery_type == 'digital':
                cur.execute("""
                    INSERT INTO study_certificate_requests (user_id, status, delivery_type) 
                    VALUES (%s, 'processing', 'digital') 
                    RETURNING request_id
                """, (db_user_id,))
            else:
                cur.execute("""
                    INSERT INTO study_certificate_requests (user_id, status, delivery_type, office_location) 
                    VALUES (%s, 'processing', 'office', %s) 
                    RETURNING request_id
                """, (db_user_id, office_location))

            request_id = cur.fetchone()[0]
            db.conn.commit()
            return request_id
    except Exception as e:
        logger.error(f"Ошибка создания заявки на справку: {e}")
        db.conn.rollback()
        return None


def process_digital_certificate_request(request_id, user_id):
    """Обработать заявку на электронную справку"""
    try:
        with db.conn.cursor() as cur:
            # Генерируем ссылку для скачивания
            download_link = f"https://example.com/certificates/{request_id}_signed.pdf"

            cur.execute("""
                UPDATE study_certificate_requests 
                SET status = 'completed', 
                    download_link = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE request_id = %s
            """, (download_link, request_id))
            db.conn.commit()

            # Создаем уведомление для пользователя
            notification_message = f"✅ Ваша справка об обучении готова!\n\nСкачать: {download_link}"
            create_notification(user_id, 'certificate_ready', '📄 Справка готова', notification_message, request_id)

    except Exception as e:
        logger.error(f"Ошибка обработки заявки на электронную справку: {e}")
        db.conn.rollback()


def process_office_certificate_request(request_id, user_id):
    """Обработать заявку на справку для получения в деканате"""
    try:
        with db.conn.cursor() as cur:
            cur.execute("""
                UPDATE study_certificate_requests 
                SET status = 'ready_for_pickup',
                    completed_at = CURRENT_TIMESTAMP
                WHERE request_id = %s
            """, (request_id,))
            db.conn.commit()

            # Создаем уведомление для пользователя
            notification_message = (
                "✅ Ваша справка об обучении готова к выдаче!\n\n"
                "📍 Место получения: Деканат главного корпуса\n"
                "🕒 Часы работы: Пн-Пт с 9:00 до 17:00\n\n"
                "Не забудьте взять с собой студенческий билет!"
            )
            create_notification(user_id, 'certificate_ready', '📄 Справка готова', notification_message, request_id)

    except Exception as e:
        logger.error(f"Ошибка обработки заявки на офисную справку: {e}")
        db.conn.rollback()


def show_certificate_status(context, request_id):
    """Показать статус справки"""
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM study_certificate_requests 
                WHERE request_id = %s
            """, (request_id,))
            request = cur.fetchone()

            if not request:
                context.reply_callback("❌ Заявка не найдена")
                return

            message = "📊 Статус справки об обучении\n\n"
            message += f"📋 Номер заявки: {request['request_id']}\n"
            message += f"📅 Дата подачи: {request['request_date'].strftime('%d.%m.%Y %H:%M')}\n"

            status_emoji = {
                'processing': '⏳',
                'completed': '✅',
                'ready_for_pickup': '📦',
                'pending': '⏳'
            }

            status_text = {
                'processing': 'В обработке',
                'completed': 'Готово',
                'ready_for_pickup': 'Готово к выдаче',
                'pending': 'Ожидает обработки'
            }

            message += f"📊 Статус: {status_emoji.get(request['status'], '📝')} {status_text.get(request['status'], request['status'])}\n"

            if request['delivery_type'] == 'digital':
                message += "💻 Способ получения: Электронная версия\n"
                if request['download_link']:
                    message += f"🔗 Ссылка для скачивания: {request['download_link']}\n"
            else:
                message += "🏢 Способ получения: Забрать в деканате\n"
                if request['office_location']:
                    message += f"📍 Место выдачи: {request['office_location']}\n"

            if request['completed_at']:
                message += f"✅ Готово: {request['completed_at'].strftime('%d.%m.%Y %H:%M')}\n"

            keyboard = InlineKeyboard(
                [{"text": "🔄 Обновить", "callback": f"certificate_status_{request_id}"}],
                [{"text": "🏠 Главное меню", "callback": "back_to_menu"}]
            )

            context.reply_callback(message, keyboard=keyboard)

    except Exception as e:
        logger.error(f"Ошибка получения статуса справки: {e}")
        context.reply_callback("❌ Произошла ошибка при получении статуса")


def cancel_certificate(context):
    """Отмена оформления справки"""
    message = "❌ Оформление справки отменено"

    keyboard = InlineKeyboard(
        [{"text": "🏠 Главное меню", "callback": "back_to_menu"}]
    )

    context.reply_callback(message, keyboard=keyboard)

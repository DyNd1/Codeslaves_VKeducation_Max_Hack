from applicant.open_days import (get_upcoming_open_days, format_open_days_message,
                                 is_user_registered, get_open_day_by_id)
from config import logger, db
from keyboards.menus import get_open_days_registration_keyboard, get_main_non_auth_keyboard,get_main_auth_keyboard
from maxgram.keyboards import InlineKeyboard
from psycopg2.extras import RealDictCursor

# Глобальный словарь для хранения временных данных регистрации
registration_data = {}


def show_open_days(context):
    """Показать дни открытых дверей"""
    open_days = get_upcoming_open_days(db.conn)

    if not open_days:
        context.reply_callback("📅 На данный момент нет запланированных дней открытых дверей.")
        return

    for i, event in enumerate(open_days, 1):
        mssg = format_open_days_message(open_days, i)
        open_days_keyboard = get_open_days_registration_keyboard(event['event_id'], i)
        context.reply_callback(mssg, keyboard=open_days_keyboard)


def start_open_day_registration(context, event_id, user_id):
    """Начать процесс регистрации на день открытых дверей"""
    try:
        # Проверяем, авторизован ли пользователь
        from handlers.authorization_handler import authenticated_users

        if user_id in authenticated_users:
            # Авторизованный пользователь - сразу регистрируем с данными из БД
            complete_registration_for_authenticated_user(context, event_id, user_id)
        else:
            # Неавторизованный пользователь - начинаем процесс ввода данных
            registration_data[user_id] = {
                'event_id': event_id,
                'step': 'fio',
                'data': {}
            }
            context.reply_callback("📝 Регистрация на день открытых дверей\n\n"
                                   "Шаг 1 из 3: Введите ваше ФИО (например: Иванов Иван Иванович)\n\n"
                                   "❌ Чтобы отменить регистрацию, нажмите /cancel")

    except Exception as e:
        logger.error(f"Ошибка при начале регистрации: {e}")
        context.reply_callback("❌ Произошла ошибка при начале регистрации. Попробуйте позже.")


def complete_registration_for_authenticated_user(context, event_id, user_id):
    """Завершение регистрации для авторизованного пользователя"""
    try:
        from handlers.authorization_handler import authenticated_users

        user_info = authenticated_users[user_id]['user_info']
        login = user_info['login']

        # Получаем полные данные пользователя из БД
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT first_name, last_name, phone_number, email, max_id 
                FROM users 
                WHERE login = %s
            """, (login,))
            db_user = cur.fetchone()

        if not db_user:
            context.reply("❌ Не удалось найти ваши данные в системе.")
            return

        first_name = db_user['first_name']
        last_name = db_user['last_name']
        phone = db_user['phone_number']
        email = db_user['email']
        fio = f"{last_name} {first_name}"
        max_id = db_user['max_id']
        # Проверяем, не зарегистрирован ли уже пользователь
        if is_user_registered(db.conn, event_id, max_id):
            context.reply("❌ Вы уже зарегистрированы на это событие!", keyboard = get_main_auth_keyboard())
            return

        # Проверяем, есть ли свободные места
        event = get_open_day_by_id(db.conn, event_id)
        if not event['can_register']:
            context.reply("❌ К сожалению, на это событие больше нет свободных мест.", keyboard = get_main_auth_keyboard())
            return

        # Регистрируем на событие
        try:
            with db.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO open_day_registrations (event_id, max_id)
                    VALUES (%s, %s)
                """, (event_id, max_id))
                db.conn.commit()
        except:
            db.conn.rollback()


        # Получаем информацию о событии для финального сообщения
        event_info = get_open_day_by_id(db.conn, event_id)

        success_message = (
            "✅ Регистрация завершена успешно!\n\n"
            f"🎓 Событие: {event_info['faculty_name']}\n"
            f"📅 Дата: {event_info['event_date']}\n"
            f"👤 Использованы данные из вашего профиля:\n"
            f"   • ФИО: {fio}\n"
            f"   • Телефон: {phone}\n"
            f"   • Email: {email}\n\n"
            "📋 Мы отправим вам напоминание за день до события!"
        )

        context.reply(success_message, keyboard=get_main_auth_keyboard())

    except Exception as e:
        logger.error(f"Ошибка завершения регистрации для авторизованного пользователя: {e}")
        db.conn.rollback()
        context.reply("❌ Произошла ошибка при регистрации. Попробуйте позже.")


def process_registration_step(context, user_id, text):
    """Обработка шагов регистрации для неавторизованных пользователей"""
    if user_id not in registration_data:
        return False

    current_data = registration_data[user_id]
    step = current_data['step']

    try:
        if step == 'fio':
            # Проверяем ФИО (должно быть минимум 2 слова)
            if len(text.split()) < 2:
                context.reply("❌ Пожалуйста, введите ФИО полностью (Фамилия Имя Отчество)")
                return True

            current_data['data']['fio'] = text
            current_data['step'] = 'phone'
            context.reply("Шаг 2 из 3: Введите ваш номер телефона (например: +79161234567)")

        elif step == 'phone':
            # Простая валидация номера телефона
            phone = text.strip()
            if not (phone.startswith('+7') or phone.startswith('8') or phone.replace('+', '').isdigit()):
                context.reply("❌ Пожалуйста, введите корректный номер телефона")
                return True

            current_data['data']['phone'] = phone
            current_data['step'] = 'email'
            context.reply("Шаг 3 из 3: Введите ваш email")

        elif step == 'email':
            # Простая валидация email
            email = text.strip()
            if '@' not in email or '.' not in email:
                context.reply("❌ Пожалуйста, введите корректный email")
                return True

            current_data['data']['email'] = email
            # Завершаем регистрацию
            complete_registration(context, user_id)
            # Удаляем временные данные
            del registration_data[user_id]

        return True

    except Exception as e:
        logger.error(f"Ошибка обработки шага регистрации: {e}")
        keyboard_rows = []
        keyboard_rows.append([{"text": "Назад", "callback": "back_to_menu"}])
        context.reply("❌ Произошла ошибка. Попробуйте начать регистрацию заново.",
                      keyboard=InlineKeyboard(*keyboard_rows))
        if user_id in registration_data:
            del registration_data[user_id]
        return False


def complete_registration(context, user_id):
    """Завершение регистрации и сохранение в БД для неавторизованных пользователей"""
    try:
        user_data = registration_data[user_id]
        event_id = user_data['event_id']
        fio = user_data['data']['fio']
        phone = user_data['data']['phone']
        email = user_data['data']['email']

        # Разделяем ФИО на составляющие
        fio_parts = fio.split()
        last_name = fio_parts[0] if len(fio_parts) > 0 else ""
        first_name = fio_parts[1] if len(fio_parts) > 1 else ""

        # Проверяем, не зарегистрирован ли уже пользователь
        if is_user_registered(db.conn, event_id, user_id):
            context.reply("❌ Вы уже зарегистрированы на это событие!", keyboard = get_main_non_auth_keyboard())
            return

        # Проверяем, есть ли свободные места
        event = get_open_day_by_id(db.conn, event_id)
        if not event['can_register']:
            context.reply("❌ К сожалению, на это событие больше нет свободных мест.", keyboard = get_main_non_auth_keyboard())
            return

        # Сохраняем пользователя в БД (если еще нет)

        # Регистрируем на событие
        with db.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO open_day_registrations (event_id, max_id, first_name, last_name)
                VALUES (%s, %s, %s, %s)
            """, (event_id, user_id, first_name, last_name))
            db.conn.commit()

        # Получаем информацию о событии для финального сообщения
        event_info = get_open_day_by_id(db.conn, event_id)

        success_message = (
            "✅ Регистрация завершена успешно!\n\n"
            f"🎓 Событие: {event_info['faculty_name']}\n"
            f"📅 Дата: {event_info['event_date']}\n"
            f"👤 Ваши данные:\n"
            f"   • ФИО: {fio}\n"
            f"   • Телефон: {phone}\n"
            f"   • Email: {email}\n\n"
            "📋 Мы отправим вам напоминание за день до события!"
        )

        context.reply(success_message, keyboard=get_main_non_auth_keyboard())

    except Exception as e:
        logger.error(f"Ошибка завершения регистрации: {e}")
        # Делаем rollback при ошибке
        db.conn.rollback()
        keyboard_rows = []
        keyboard_rows.append([{"text": "Назад", "callback": "back_to_menu"}])
        context.reply("❌ Произошла ошибка при завершении регистрации. Попробуйте позже.", keyboard=keyboard_rows)


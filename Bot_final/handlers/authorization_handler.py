from config import  logger, db
from maxgram.keyboards import InlineKeyboard
from psycopg2.extras import RealDictCursor
from handlers.open_days_handlers import registration_data
from handlers.ege_handler import user_selection_data
from keyboards.menus import get_app_keyboard, get_student_keyboard, get_teacher_keyboard, get_rector_keyboard

# Глобальные словари для хранения данных
auth_sessions = {}
authenticated_users = {}  # Новый словарь для хранения авторизованных пользователей


def start_authorization(context):
    """Начать процесс авторизации"""
    user_id = get_safe_user_id(context)

    # Сохраняем состояние авторизации
    auth_sessions[user_id] = {
        'step': 'login',
        'attempts': 0
    }

    context.reply_callback("🔐 Авторизация\n\nВведите ваш логин:")


def process_auth_step(context, user_id, text):
    """Обработка шагов авторизации"""
    if user_id not in auth_sessions:
        return False

    user_data = auth_sessions[user_id]
    step = user_data['step']

    try:
        if step == 'login':
            # Сохраняем логин и запрашиваем пароль
            user_data['login'] = text.strip()
            user_data['step'] = 'password'
            context.reply("Введите ваш пароль:")
            return True

        elif step == 'password':
            # Проверяем логин и пароль
            login = user_data['login']
            password = text.strip()

            user = authenticate_user(db.conn, login, password)

            if user:
                # Успешная авторизация - сохраняем пользователя
                authenticated_users[user_id] = {
                    'user_info': user,
                    'authenticated_at': context.message.get('created_at', 'unknown'),
                    'role': user['role']
                }

                user_data['authenticated'] = True
                user_data['user_info'] = user
                show_role_based_menu(context, user)

                # Удаляем сессию авторизации, но пользователь остается в authenticated_users
                del auth_sessions[user_id]
            else:
                # Неверные данные
                user_data['attempts'] += 1

                if user_data['attempts'] >= 3:
                    context.reply("❌ Превышено количество попыток. Авторизация отменена.")
                    del auth_sessions[user_id]
                else:
                    context.reply(
                        f"❌ Неверный логин или пароль. Попытка {user_data['attempts']} из 3. Попробуйте еще раз:\nВведите логин:")
                    user_data['step'] = 'login'

        return True

    except Exception as e:
        logger.error(f"Ошибка авторизации: {e}")
        context.reply("❌ Произошла ошибка при авторизации. Попробуйте позже.")
        if user_id in auth_sessions:
            del auth_sessions[user_id]
        return False


def is_user_authenticated(user_id):
    """Проверяет, авторизован ли пользователь"""
    return user_id in authenticated_users


def authenticate_user(conn, login, password):
    """Аутентификация пользователя"""
    try:
        # Проверяем соединение
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        except:
            conn.rollback()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Ищем пользователя по логину и паролю
            cur.execute("""
                SELECT user_id, login, max_id, role, first_name, surname, last_name, email, phone_number
                FROM users 
                WHERE login = %s AND password = %s
            """, (login, password))

            user = cur.fetchone()
            return user

    except Exception as e:
        logger.error(f"Ошибка аутентификации: {e}")
        try:
            conn.rollback()
        except:
            pass
        return None


def show_role_based_menu(context, user):
    """Показать меню в зависимости от роли пользователя"""
    role = user['role']
    first_name = user['first_name']
    surname = user['surname']

    if role == 'applicant':
        show_applicant_menu(context, first_name)
    elif role == 'student':
        show_student_menu(context, first_name)
    elif role == 'teacher':
        show_teacher_menu(context, first_name, surname)
    elif role == 'rector':
        show_rector_menu(context, first_name, surname)
    else:
        show_default_menu(context, first_name)


def show_applicant_menu(context, first_name):
    """Меню для абитуриента"""
    keyboard = get_app_keyboard()
    message = f"👋 Добро пожаловать, {first_name}!\n\n"
    message += "🎓 Вы вошли как **абитуриент**\n\n"
    message += "Доступные действия:"

    context.reply(message, keyboard=keyboard)


def show_student_menu(context, first_name):
    """Меню для студента"""
    keyboard = get_student_keyboard()

    message = f"👋 Привет, {first_name}!\n\n"
    message += "Чем могу помочь?\n\n"
    message += "Доступные действия:"

    context.reply(message, keyboard=keyboard)


def show_teacher_menu(context, first_name, surname):
    """Меню для преподавателя"""
    keyboard = get_teacher_keyboard()

    message = f"👋 Доброго дня, {first_name} {surname}!\n\n"
    message += "Чем могу помочь?\n\n"
    message += "Доступные действия:"

    context.reply(message, keyboard=keyboard)


def show_rector_menu(context, first_name,surname):
    """Меню для ректора"""
    keyboard = get_rector_keyboard()
    message = f"👋 Доброго дня, {first_name} {surname}!\n\n"
    message += "Чем могу помочь?\n\n"
    message += "Доступные действия:"

    context.reply(message, keyboard=keyboard)


def show_default_menu(context, first_name):
    """Меню по умолчанию"""
    keyboard = InlineKeyboard(
        [{"text": "🏠 Главное меню", "callback": "back_to_menu"}],
        [{"text": "🚪 Выйти", "callback": "logout"}]
    )

    message = f"👋 Добро пожаловать, {first_name}!\n\n"
    message += "Ваша роль не определена. Обратитесь к администратору."

    context.reply(message, keyboard=keyboard)


def handle_logout(context):
    """Обработка выхода из системы"""
    user_id = get_safe_user_id(context)

    # Удаляем все сессии пользователя
    if user_id in auth_sessions:
        del auth_sessions[user_id]
    if user_id in authenticated_users:
        del authenticated_users[user_id]
    if user_id in registration_data:
        del registration_data[user_id]
    if user_id in user_selection_data:
        del user_selection_data[user_id]

    from keyboards.menus import get_main_non_auth_keyboard
    context.reply_callback("✅ Вы вышли из системы.", keyboard=get_main_non_auth_keyboard())


def get_safe_user_id(context):
    """Безопасное получение user_id"""
    try:
        return context.message['recipient']['chat_id']
    except:
        return "unknown"


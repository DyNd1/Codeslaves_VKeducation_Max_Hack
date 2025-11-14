from config import bot, logger, db
from keyboards.menus import get_main_non_auth_keyboard, get_main_auth_keyboard
from handlers.open_days_handlers import registration_data, process_registration_step
from handlers.ege_handler import user_selection_data, process_score_input, show_subjects_keyboard
from handlers.authorization_handler import auth_sessions, process_auth_step, handle_logout, authenticated_users, show_role_based_menu
from handlers.business_trip_handler import (
    start_business_trip,
    cancel_business_trip,
    process_business_trip_message
)
from handlers.library_handlers import user_book_search, handle_book_search_query
from handlers.vacation_handler import (
    start_vacation,
    cancel_vacation,
    submit_vacation,
    process_vacation_message
)
from handlers.notification_handler import check_and_show_notifications
from handlers.schedule_handler import show_student_schedule, show_teacher_schedule
from handlers.project_handler import project_creation_sessions, process_project_creation

def get_safe_user_id(context):
    user_id = context.message['recipient']['chat_id']
    return user_id

def is_user_authenticated(user_id):
    """Проверяет, авторизован ли пользователь"""
    return user_id in authenticated_users

@bot.on("bot_started")
def on_start(context):
    logger.info("Бот запущен")

    # Если не авторизован, показываем обычное меню
    keyboard = get_main_non_auth_keyboard()
    welcome_message = (
        "Привет, ты в боте команды CodeSlaves! Здесь ты можешь ознакомиться с MVP-системой для вуза."
        " Нажми 'авторизация', если у тебя есть логин и пароль. В ином случае ты можешь "
        "ознакомиться с направлениями, которые могут быть тебе интересны, а так же узнать"
        " проходные баллы на них!"
    )
    context.reply(welcome_message, keyboard=keyboard)

@bot.hears("ping")
def ping_handler(context):
    logger.info("Получено сообщение 'ping'")
    context.reply("pong")

@bot.command("hello")
def hello_handler(context):
    logger.info("Вызвана команда /hello")
    context.reply("world")

@bot.on("message_created")
def handle_message(context):
    # Получаем user_id
    user_id = get_safe_user_id(context)

    # Извлекаем текст сообщения
    text = None
    if context.message and context.message.get("body") and "text" in context.message["body"]:
        text = context.message["body"]["text"]

    # Проверяем, находится ли пользователь в процессе авторизации
    if user_id in auth_sessions:
        if text:
            if text == "/cancel":
                if user_id in auth_sessions:
                    del auth_sessions[user_id]
                context.reply("❌ Авторизация отменена.")
                return

            # Сохраняем состояние до обработки авторизации
            was_in_auth_sessions = user_id in auth_sessions
            
            # Обрабатываем шаг авторизации
            process_auth_step(context, user_id, text)
            
            # Проверяем, завершилась ли авторизация успешно
            if was_in_auth_sessions and user_id not in auth_sessions and user_id in authenticated_users:
                # Показываем уведомления после успешной авторизации
                check_and_show_notifications(context)
                
        return

    # Проверяем, находится ли пользователь в процессе регистрации на день открытых дверей
    if user_id in registration_data:
        if text:
            if text == "/cancel":
                if user_id in registration_data:
                    del registration_data[user_id]
                context.reply("❌ Регистрация отменена")
                return

            process_registration_step(context, user_id, text)
            return

    # Проверяем, находится ли пользователь в процессе ввода баллов ЕГЭ
    if user_id in user_selection_data:
        user_data = user_selection_data[user_id]
        if user_data.get('current_step') == 'score_input':
            if text:
                if text == "/cancel":
                    user_data['current_step'] = 'subject_selection'
                    show_subjects_keyboard(context, user_id)
                    return
                if process_score_input(context, user_id, text):
                    return

    # Проверяем, находится ли пользователь в процессе создания проекта
    if user_id in project_creation_sessions:
        if text:
            if text == "/cancel":
                if user_id in project_creation_sessions:
                    del project_creation_sessions[user_id]
                context.reply("❌ Создание проекта отменено.")
                return

            if process_project_creation(context, text):
                return

    # Проверяем, находится ли пользователь в процессе оформления командировки
    if text and process_business_trip_message(context, text):
        return

    # Проверяем, находится ли пользователь в процессе оформления отпуска
    if text and process_vacation_message(context, text):
        return

    if user_id in user_book_search and user_book_search[user_id]['step'] == 'awaiting_search_query':
        handle_book_search_query(context, text)
        return True
        
    # Если не в каких-либо процессах, обрабатываем как обычное сообщение
    if text:
        context.reply("❌ Я вас не понял, воспользуйтесь командой из меню")
        pass

@bot.on("error")
def error_handler(context):
    logger.error(f"Ошибка бота: {context.error}")
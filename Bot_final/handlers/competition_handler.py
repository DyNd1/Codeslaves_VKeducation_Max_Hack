from config import db, logger
from psycopg2.extras import RealDictCursor
from maxgram.keyboards import InlineKeyboard
from datetime import date
from handlers.authorization_handler import authenticated_users


def get_user_id(context):
    """Безопасное получение user_id"""
    return context.message['recipient']['chat_id']


def get_db_user_id(chat_id):
    """Получает user_id из базы данных для авторизованного пользователя"""
    if chat_id in authenticated_users:
        user_data = authenticated_users[chat_id]
        if 'user_info' in user_data and 'user_id' in user_data['user_info']:
            return user_data['user_info']['user_id']
    return None


def show_teacher_contract_info(context):
    """Показать информацию о контракте преподавателя"""
    chat_id = get_user_id(context)
    db_user_id = get_db_user_id(chat_id)

    if not db_user_id:
        context.reply_callback("❌ Ошибка: пользователь не авторизован")
        return

    # Получаем информацию о контрактах преподавателя
    contracts = get_teacher_contracts(db_user_id)

    if not contracts:
        message = "📋 Информация о контрактах\n\n"
        message += "❌ У вас нет активных контрактов.\n\n"
        message += "Обратитесь в отдел кадров для уточнения информации."
    else:
        message = "📋 Ваши контракты\n\n"

        for i, contract in enumerate(contracts, 1):
            days_left = (contract['end_date'] - date.today()).days

            status_emoji = {
                'active': '✅',
                'expired': '❌',
                'terminated': '⏹️'
            }

            message += f"{i}. Контракт №{contract['contract_number']}\n"
            message += f"   🏢 Должность: {contract['position']}\n"
            message += f"   📚 Кафедра: {contract['department']}\n"
            message += f"   📅 Срок действия: {contract['start_date'].strftime('%d.%m.%Y')} - {contract['end_date'].strftime('%d.%m.%Y')}\n"
            message += f"   💰 Зарплата: {contract['salary']:.2f} руб.\n"
            message += f"   {status_emoji.get(contract['status'], '📝')} Статус: {contract['status']}\n"

            if contract['status'] == 'active' and days_left > 0:
                if days_left <= 30:
                    message += f"   ⚠️ До окончания: {days_left} дн.\n"
                else:
                    message += f"   📅 До окончания: {days_left} дн.\n"
            elif contract['status'] == 'active' and days_left <= 0:
                message += f"   ❗ Контракт истек!\n"

            message += "\n"

    keyboard = InlineKeyboard(
        [{"text": "🔙 Назад", "callback": "competition"}]
    )

    context.reply_callback(message, keyboard=keyboard)


def show_vacancy_competitions(context):
    """Показать информацию о конкурсах на замещение вакантных должностей"""
    # Получаем активные конкурсы
    competitions = get_active_competitions()

    if not competitions:
        message = "🏆 Конкурсы на замещение вакантных должностей\n\n"
        message += "📭 На данный момент нет активных конкурсов.\n\n"
        message += "Следите за обновлениями на сайте университета и в этом разделе."
    else:
        message = "🏆 Активные конкурсы\n\n"

        for i, competition in enumerate(competitions, 1):
            days_until_end = (competition['application_end_date'] - date.today()).days
            days_until_competition = (competition['competition_date'] - date.today()).days

            # Определяем статус срока подачи
            if days_until_end > 0:
                deadline_status = f"⏳ До окончания подачи: {days_until_end} дн."
            else:
                deadline_status = "❌ Прием заявок завершен"

            message += f"{i}. {competition['position']}\n"
            message += f"   🏢 Кафедра: {competition['department']}\n"
            message += f"   📊 Вакансий: {competition['vacancy_count']}\n"
            message += f"   💰 Зарплата: {competition['salary_range']}\n"
            message += f"   📅 Прием заявок: {competition['application_start_date'].strftime('%d.%m.%Y')} - {competition['application_end_date'].strftime('%d.%m.%Y')}\n"
            message += f"   🏁 Дата конкурса: {competition['competition_date'].strftime('%d.%m.%Y')}\n"
            message += f"   {deadline_status}\n"

            if days_until_competition > 0:
                message += f"   📋 До конкурса: {days_until_competition} дн.\n"

            message += "\n"

        message += "📝 Как принять участие:\n"
        message += "1. Подайте заявку в отделе кадров\n"
        message += "2. Подготовьте пакет документов\n"
        message += "3. Участвуйте в конкурсных мероприятиях"

    keyboard = InlineKeyboard(
        [{"text": "🔄 Обновить", "callback": "competition"}],
        [{"text": "🔙 Назад", "callback": "back_to_menu"}]
    )

    context.reply_callback(message, keyboard=keyboard)


def get_teacher_contracts(user_id):
    """Получить контракты преподавателя"""
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM teacher_contracts 
                WHERE user_id = %s 
                ORDER BY end_date DESC
            """, (user_id,))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении контрактов преподавателя: {e}")
        return []


def get_active_competitions():
    """Получить активные конкурсы"""
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM vacancy_competitions 
                WHERE status = 'active' 
                AND application_end_date >= CURRENT_DATE
                ORDER BY application_end_date ASC
            """)
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении конкурсов: {e}")
        return []


def handle_competition_menu(context):
    """Обработка меню конкурсов и контрактов"""
    chat_id = get_user_id(context)
    db_user_id = get_db_user_id(chat_id)

    if not db_user_id:
        context.reply_callback("❌ Ошибка: пользователь не авторизован")
        return

    # Проверяем роль пользователя
    user_role = authenticated_users[chat_id]['role']

    if user_role == 'teacher':
        # Для преподавателей показываем оба варианта
        keyboard = InlineKeyboard(
            [{"text": "📋 Мои контракты", "callback": "teacher_contracts"}],
            [{"text": "🏆 Конкурсы на замещение", "callback": "vacancy_competitions"}],
            [{"text": "🔙 Назад", "callback": "back_to_menu"}]
        )

        message = "📊 Кадровая информация\n\n"
        message += "Выберите раздел для просмотра информации:"
    else:
        # Для других ролей только конкурсы
        keyboard = InlineKeyboard(
            [{"text": "🏆 Конкурсы на замещение", "callback": "vacancy_competitions"}],
            [{"text": "🔙 Назад", "callback": "back_to_menu"}]
        )

        message = "🏆 Конкурсы на замещение вакантных должностей\n\n"
        message += "Просмотр активных конкурсов на замещение должностей в университете."

    context.reply_callback(message, keyboard=keyboard)

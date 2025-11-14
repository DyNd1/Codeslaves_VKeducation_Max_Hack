from config import bot, logger, db
from maxgram.keyboards import InlineKeyboard
from datetime import datetime, timedelta
from handlers.authorization_handler import authenticated_users
from psycopg2.extras import RealDictCursor

def get_safe_user_id(context):
    """Безопасное получение user_id"""
    try:
        return context.message['recipient']['chat_id']
    except:
        return "unknown"

def get_db_user_id(chat_id):
    """Получает user_id из базы данных для авторизованного пользователя"""
    if chat_id in authenticated_users:
        user_data = authenticated_users[chat_id]
        if 'user_info' in user_data and 'user_id' in user_data['user_info']:
            return user_data['user_info']['user_id']
    return None

def show_teacher_schedule(context):
    """Показ расписания преподавателя"""
    user_id = get_safe_user_id(context)
    
    # Проверяем, авторизован ли пользователь
    if user_id not in authenticated_users:
        context.reply("❌ Для просмотра расписания необходимо авторизоваться.")
        return
    
    db_user_id = get_db_user_id(user_id)
    if not db_user_id:
        context.reply("❌ Не удалось найти ваш профиль в системе.")
        return
    
    # Получаем текущую дату и вычисляем недели
    current_date = datetime.now()
    
    # Определяем, какая сейчас неделя (четная или нечетная)
    # Берем 1 сентября текущего учебного года как точку отсчета
    current_year = current_date.year
    september_first = datetime(current_year, 9, 1)
    
    # Если сейчас до 1 сентября, берем предыдущий учебный год
    if current_date < september_first:
        september_first = datetime(current_year - 1, 9, 1)
    
    # Вычисляем количество недель с 1 сентября
    weeks_since_september = (current_date - september_first).days // 7
    
    # Определяем тип текущей недели
    current_week_type = 'odd' if weeks_since_september % 2 == 0 else 'even'
    
    # Вычисляем даты для текущей недели (понедельник - воскресенье)
    current_week_dates = get_week_dates(current_date)
    
    # Вычисляем даты для следующей недели (противоположный тип)
    next_week_date = current_date + timedelta(days=7)
    next_week_dates = get_week_dates(next_week_date)
    next_week_type = 'even' if current_week_type == 'odd' else 'odd'
    
    # Получаем расписание для преподавателя
    schedule_current = get_teacher_schedule(db_user_id, current_week_type)
    schedule_next = get_teacher_schedule(db_user_id, next_week_type)
    
    # Формируем сообщения
    if schedule_current or schedule_next:
        # Сообщение для текущей недели
        message_current = format_schedule_message(
            schedule_current, 
            current_week_type, 
            current_week_dates,
            "📅 Расписание на текущую неделю"
        )
        
        # Сообщение для следующей недели
        message_next = format_schedule_message(
            schedule_next, 
            next_week_type, 
            next_week_dates,
            "📅 Расписание на следующую неделю"
        )
        
        # Отправляем оба сообщения
        context.reply_callback(message_current)
        context.reply_callback(message_next)
        
    else:
        context.reply_callback("📭 Расписание не найдено. Обратитесь в учебную часть.")
    
    # Добавляем кнопку назад
    keyboard = InlineKeyboard(
        [{"text": "🔙 Назад в меню", "callback": "back_to_menu"}]
    )
    context.reply_callback("Выберите действие:", keyboard=keyboard)

def get_week_dates(reference_date):
    """Возвращает даты недели (понедельник - воскресенье)"""
    # Находим понедельник недели
    monday = reference_date - timedelta(days=reference_date.weekday())
    
    week_dates = {}
    for i in range(7):
        day_date = monday + timedelta(days=i)
        week_dates[i + 1] = day_date.strftime('%d.%m.%Y')  # +1 потому что день_недели от 1 до 7
    
    return week_dates

def get_teacher_schedule(teacher_id, week_type):
    """Получает расписание преподавателя из БД"""
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT day_of_week, start_time, end_time, subject_name, classroom
                FROM teacher_schedule 
                WHERE teacher_id = %s AND week_type = %s
                ORDER BY day_of_week, start_time
            """, (teacher_id, week_type))
            
            return cur.fetchall()
            
    except Exception as e:
        logger.error(f"Ошибка при получении расписания: {e}")
        return []

def format_schedule_message(schedule, week_type, week_dates, title):
    """Форматирует сообщение с расписанием"""
    week_type_russian = "нечетную" if week_type == 'odd' else "четную"
    
    message = f"**{title} ({week_type_russian})**\n\n"
    
    if not schedule:
        message += "❌ Занятий нет\n\n"
        return message
    
    # Группируем занятия по дням недели
    days_schedule = {}
    for lesson in schedule:
        day = lesson['day_of_week']
        if day not in days_schedule:
            days_schedule[day] = []
        days_schedule[day].append(lesson)
    
    # Дни недели на русском
    days_names = {
        1: "Понедельник",
        2: "Вторник", 
        3: "Среда",
        4: "Четверг",
        5: "Пятница",
        6: "Суббота",
        7: "Воскресенье"
    }
    
    # Формируем расписание по дням
    for day_num in sorted(days_schedule.keys()):
        day_name = days_names.get(day_num, f"День {day_num}")
        day_date = week_dates.get(day_num, "")
        
        message += f"**{day_name} ({day_date})**\n"
        
        for lesson in days_schedule[day_num]:
            start_time = lesson['start_time'].strftime('%H:%M')
            end_time = lesson['end_time'].strftime('%H:%M')
            subject = lesson['subject_name']
            classroom = lesson['classroom'] or "ауд. не указана"
            
            message += f"🕒 {start_time}-{end_time}\n"
            message += f"   📚 {subject}\n"
            message += f"   🏫 {classroom}\n"
        
        message += "\n"
    
    return message
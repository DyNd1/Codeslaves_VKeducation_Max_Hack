from config import db, logger
from keyboards.menus import get_student_keyboard
from datetime import datetime
from handlers.authorization_handler import authenticated_users
from maxgram.keyboards import InlineKeyboard
from psycopg2.extras import RealDictCursor

# Хранилище состояний для процесса записи
digital_department_sessions = {}

def get_db_user_id(chat_id):
    """Получает user_id из базы данных для авторизованного пользователя"""
    if chat_id in authenticated_users:
        user_data = authenticated_users[chat_id]
        if 'user_info' in user_data and 'user_id' in user_data['user_info']:
            return user_data['user_info']['user_id']
    return None

def calculate_student_gpa(db_user_id):
    """Рассчитывает средний балл студента"""
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT AVG(grade) as gpa 
                FROM student_grades 
                WHERE user_id = %s
            """, (db_user_id,))
            result = cur.fetchone()
            return result['gpa'] if result and result['gpa'] else 0.0
    except Exception as e:
        logger.error(f"Ошибка при расчете GPA: {e}")
        return 0.0

def get_available_departments(db_user_id):
    """Получает доступные направления для студента"""
    gpa = calculate_student_gpa(db_user_id)
    
    # Добавляем отладочную информацию
    logger.info(f"DB User {db_user_id} GPA: {gpa}")
    
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT dd.* 
                FROM digital_departments dd
                WHERE dd.application_deadline >= CURRENT_DATE
                AND dd.min_gpa <= %s
                AND dd.available_places > (
                    SELECT COUNT(*) 
                    FROM digital_department_applications 
                    WHERE department_id = dd.department_id 
                    AND status = 'approved'
                )
                ORDER BY dd.department_name
            """, (gpa,))
            departments = cur.fetchall()
            
            # Логируем результаты запроса
            logger.info(f"Available departments for DB user {db_user_id}: {[dept['department_name'] for dept in departments]}")
            
            return departments
    except Exception as e:
        logger.error(f"Ошибка при получении направлений: {e}")
        return []

def start_digital_department_registration(context):
    """Начинает процесс записи на цифровую кафедру"""
    chat_id = context.message['recipient']['chat_id']
    db_user_id = get_db_user_id(chat_id)
    
    if not db_user_id:
        context.reply("❌ Вы не авторизованы.")
        return
    
    # Получаем доступные направления
    departments = get_available_departments(db_user_id)
    
    if not departments:
        context.reply("😔 В настоящее время нет доступных направлений для записи или ваш средний балл недостаточен.")
        return
    
    gpa = calculate_student_gpa(db_user_id)
    
    # Формируем сообщение с доступными направлениями
    message = f"🎯 Запись на цифровую кафедру\n\n"
    message += f"📊 Ваш средний балл: {gpa:.2f}\n"
    message += f"⏰ Запись открыта до: {departments[0]['application_deadline'].strftime('%d.%m.%Y')}\n\n"
    message += "Доступные направления:\n\n"
    

    keyboard_rows = []
    
    for i, dept in enumerate(departments, 1):
        message += f"{i}. {dept['department_name']}\n"
        message += f"   📍 {dept['description']}\n"
        message += f"   🎯 Мин. балл: {dept['min_gpa']} | 🪑 Мест: {dept['available_places']}\n\n"
        
        keyboard_rows.append([
            {"text": f"🎯 {dept['department_name'][:30]}...", 
             "callback": f"select_department_{dept['department_id']}"}
        ])
    
    keyboard_rows.append([{"text": "🔙 Назад", "callback": "back_to_menu"}])
    
    keyboard = InlineKeyboard(*keyboard_rows)
    
    # Сохраняем состояние
    digital_department_sessions[chat_id] = {
        'step': 'department_selection',
        'departments': departments,
        'db_user_id': db_user_id  # Сохраняем db_user_id в сессии
    }
    
    context.reply(message, keyboard=keyboard)

def handle_department_selection(context, department_id):
    """Обрабатывает выбор направления"""
    chat_id = context.message['recipient']['chat_id']
    
    if chat_id not in digital_department_sessions:
        context.reply_callback("❌ Сессия истекла. Начните заново.")
        return
    
    session_data = digital_department_sessions[chat_id]
    db_user_id = session_data['db_user_id']
    
    # Проверяем, не подана ли уже заявка
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM digital_department_applications 
                WHERE user_id = %s AND department_id = %s
            """, (db_user_id, department_id))
            existing = cur.fetchone()
    except Exception as e:
        logger.error(f"Ошибка при проверке существующей заявки: {e}")
        context.reply_callback("❌ Произошла ошибка. Попробуйте позже.")
        return
    
    if existing:
        context.reply_callback("❌ Вы уже подавали заявку на это направление.")
        return
    
    # Создаем заявку
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO digital_department_applications (user_id, department_id, status)
                VALUES (%s, %s, 'pending')
                RETURNING application_id
            """, (db_user_id, department_id))
            result = cur.fetchone()
            db.conn.commit()
            
            # Получаем информацию о направлении
            cur.execute("SELECT department_name FROM digital_departments WHERE department_id = %s", (department_id,))
            dept_result = cur.fetchone()
            
            # УВЕДОМЛЕНИЕ ТЕПЕРЬ СОЗДАЕТСЯ ТРИГГЕРОМ В БАЗЕ ДАННЫХ
            
            # Отправляем сообщение о успешной подаче
            message = f"✅ Заявка подана успешно!\n\n"
            message += f"🎯 Направление: {dept_result['department_name']}\n"
            message += f"📅 Дата подачи: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            message += f"⏳ Статус: На рассмотрении\n\n"
            message += "📢 Решение о зачислении будет опубликовано в этом чате"
            
            # Очищаем сессию
            del digital_department_sessions[chat_id]
            
            context.reply_callback(message, keyboard=get_student_keyboard())
            
    except Exception as e:
        logger.error(f"Ошибка при подаче заявки: {e}")
        db.conn.rollback()
        context.reply_callback("❌ Произошла ошибка при подаче заявки. Попробуйте позже.")

def get_department_applications(db_user_id):
    """Получает заявки пользователя на цифровую кафедру"""
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT dda.*, dd.department_name, dd.description
                FROM digital_department_applications dda
                JOIN digital_departments dd ON dda.department_id = dd.department_id
                WHERE dda.user_id = %s
                ORDER BY dda.application_date DESC
            """, (db_user_id,))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении заявок: {e}")
        return []

def show_digital_department_status(context):
    """Показывает статус заявок на цифровую кафедру"""
    chat_id = context.message['recipient']['chat_id']
    db_user_id = get_db_user_id(chat_id)
    
    if not db_user_id:
        context.reply("❌ Вы не авторизованы.")
        return
    
    applications = get_department_applications(db_user_id)
    
    if not applications:
        context.reply("📭 У вас нет активных заявок на цифровую кафедру.")
        return
    
    message = "📋 Ваши заявки на цифровую кафедру:\n\n"
    
    for app in applications:
        status_emoji = "⏳" if app['status'] == 'pending' else "✅" if app['status'] == 'approved' else "❌"
        message += f"{status_emoji} {app['department_name']}\n"
        message += f"   📅 Подана: {app['application_date'].strftime('%d.%m.%Y')}\n"
        message += f"   🎯 Статус: {app['status']}\n"
        
        if app['decision_date']:
            message += f"   📢 Решение: {app['decision_date'].strftime('%d.%m.%Y')}\n"
        
        message += "\n"
    
    context.reply(message)
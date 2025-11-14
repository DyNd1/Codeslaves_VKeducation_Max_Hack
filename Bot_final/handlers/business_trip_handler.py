from config import logger, db
from maxgram.keyboards import InlineKeyboard
from datetime import datetime, timedelta
import re
from handlers.authorization_handler import authenticated_users

# Глобальный словарь для хранения данных о командировках
business_trip_sessions = {}

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

def start_business_trip(context):
    """Начало оформления командировки"""
    user_id = get_safe_user_id(context)
    
    # Проверяем, авторизован ли пользователь
    if user_id not in authenticated_users:
        context.reply("❌ Для оформления командировки необходимо авторизоваться.")
        return
    
    db_user_id = get_db_user_id(user_id)
    if not db_user_id:
        context.reply("❌ Не удалось найти ваш профиль в системе. Обратитесь к администратору.")
        return
    
    # Инициализируем сессию для пользователя
    business_trip_sessions[user_id] = {
        'step': 'purpose',
        'purpose': '',
        'start_date': '',
        'end_date': '',
        'db_user_id': db_user_id
    }
    
    message = "🛫 Оформление заявки на командировку\n\n"
    message += "Заполним заявку. Цель командировки:\n\n"
    message += "✍️ Введите цель командировки:"
    
    keyboard = InlineKeyboard(
        [{"text": "❌ Отмена", "callback": "cancel_business_trip"}]
    )
    
    context.reply_callback(message, keyboard=keyboard)

def handle_business_trip_purpose(context, text):
    """Обработка ввода цели командировки"""
    user_id = get_safe_user_id(context)
    
    if user_id not in business_trip_sessions:
        context.reply("❌ Сессия устарела. Начните заново.")
        return
    
    # Сохраняем цель
    business_trip_sessions[user_id]['purpose'] = text.strip()
    business_trip_sessions[user_id]['step'] = 'start_date'
    
    message = "✅ Цель командировки сохранена.\n\n"
    message += "📅 Теперь введите дату начала командировки:\n\n"
    message += "Формат: ДД.ММ.ГГГГ (например, 15.12.2024)\n"
    message += "Или используйте специальные команды:\n"
    message += "• 'завтра' - для завтрашней даты\n"
    message += "• 'через 3 дня' - через указанное количество дней"
    
    keyboard = InlineKeyboard(
        [{"text": "❌ Отмена", "callback": "cancel_business_trip"}]
    )
    
    context.reply(message, keyboard=keyboard)

def handle_business_trip_start_date(context, text):
    """Обработка ввода даты начала"""
    user_id = get_safe_user_id(context)
    
    if user_id not in business_trip_sessions:
        context.reply("❌ Сессия устарела. Начните заново.")
        return
    
    # Парсим дату
    date_result = parse_date_input(text.strip())
    if not date_result:
        context.reply("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ или слова 'завтра', 'через N дней'")
        return
    
    business_trip_sessions[user_id]['start_date'] = date_result
    business_trip_sessions[user_id]['step'] = 'end_date'
    
    message = f"✅ Дата начала: {date_result.strftime('%d.%m.%Y')}\n\n"
    message += "📅 Теперь введите дату окончания командировки:\n\n"
    message += "Формат: ДД.ММ.ГГГГ (например, 20.12.2024)\n"
    message += "Или используйте специальные команды:\n"
    message += "• 'через 5 дней' - через указанное количество дней от начала"
    
    keyboard = InlineKeyboard(
        [{"text": "❌ Отмена", "callback": "cancel_business_trip"}]
    )
    
    context.reply(message, keyboard=keyboard)

def handle_business_trip_end_date(context, text):
    """Обработка ввода даты окончания"""
    user_id = get_safe_user_id(context)
    
    if user_id not in business_trip_sessions:
        context.reply("❌ Сессия устарела. Начните заново.")
        return
    
    start_date = business_trip_sessions[user_id]['start_date']
    
    # Парсим дату окончания
    end_date_result = parse_date_input(text.strip(), start_date)
    if not end_date_result:
        context.reply("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ или слова 'через N дней'")
        return
    
    # Проверяем, что дата окончания после даты начала
    if end_date_result <= start_date:
        context.reply("❌ Дата окончания должна быть позже даты начала!")
        return
    
    business_trip_sessions[user_id]['end_date'] = end_date_result
    
    # Сохраняем заявку в БД
    success = save_business_trip_to_db(user_id)
    
    if success:
        message = "✅ Заявка создана и отправлена на согласование декану!\n\n"
        message += f"📋 **Цель:** {business_trip_sessions[user_id]['purpose']}\n"
        message += f"📅 **Период:** {start_date.strftime('%d.%m.%Y')} - {end_date_result.strftime('%d.%m.%Y')}\n"
        message += f"⏳ **Статус:** Ожидание согласования\n\n"
        message += "Вы получите уведомление о смене статуса."
        
        # Очищаем сессию
        del business_trip_sessions[user_id]
    else:
        message = "❌ Ошибка при сохранении заявки. Попробуйте позже."
    
    keyboard = InlineKeyboard(
        [{"text": "🏠 Главное меню", "callback": "back_to_menu"}]
    )
    
    context.reply(message, keyboard=keyboard)

def cancel_business_trip(context):
    """Отмена оформления командировки"""
    user_id = get_safe_user_id(context)
    
    if user_id in business_trip_sessions:
        del business_trip_sessions[user_id]
    
    message = "❌ Оформление командировки отменено."
    keyboard = InlineKeyboard(
        [{"text": "🏠 Главное меню", "callback": "back_to_menu"}]
    )
    
    context.reply_callback(message, keyboard=keyboard)

def parse_date_input(text, reference_date=None):
    """Парсит ввод даты из текста"""
    if not reference_date:
        reference_date = datetime.now()
    
    text_lower = text.lower()
    
    # Обработка специальных команд
    if text_lower == 'завтра':
        return reference_date + timedelta(days=1)
    
    # Обработка "через N дней"
    days_match = re.search(r'через\s+(\d+)\s+дн', text_lower)
    if days_match:
        days = int(days_match.group(1))
        return reference_date + timedelta(days=days)
    
    # Обработка формата ДД.ММ.ГГГГ
    date_match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
    if date_match:
        day, month, year = map(int, date_match.groups())
        try:
            return datetime(year, month, day)
        except ValueError:
            return None
    
    return None

def save_business_trip_to_db(user_id):
    """Сохраняет заявку на командировку в БД"""
    try:
        if user_id not in business_trip_sessions:
            return False
        
        session_data = business_trip_sessions[user_id]
        
        # Используем user_id из базы данных
        db_user_id = session_data['db_user_id']
        
        # Получаем dean_id
        dean_id = get_random_dean_id()
        
        with db.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO business_trips 
                (user_id, purpose, start_date, end_date, dean_id, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
            """, (
                db_user_id,
                session_data['purpose'],
                session_data['start_date'],
                session_data['end_date'],
                dean_id
            ))
            
            db.conn.commit()
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении командировки в БД: {e}")
        db.conn.rollback()
        return False

def get_random_dean_id():
    """Получает ID случайного декана из БД"""
    try:
        with db.conn.cursor() as cur:
            cur.execute("""
                SELECT user_id FROM users 
                WHERE role = 'dean' 
                LIMIT 1
            """)
            result = cur.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Ошибка при получении декана: {e}")
        return None

def process_business_trip_message(context, text):
    """Обрабатывает текстовые сообщения для командировки"""
    user_id = get_safe_user_id(context)
    
    if user_id not in business_trip_sessions:
        return False
    
    session = business_trip_sessions[user_id]
    
    if session['step'] == 'purpose':
        handle_business_trip_purpose(context, text)
        return True
    elif session['step'] == 'start_date':
        handle_business_trip_start_date(context, text)
        return True
    elif session['step'] == 'end_date':
        handle_business_trip_end_date(context, text)
        return True
    
    return False
from config import logger, db
from maxgram.keyboards import InlineKeyboard
from datetime import datetime, timedelta
import re
from handlers.authorization_handler import authenticated_users

# Глобальный словарь для хранения данных об отпусках
vacation_sessions = {}

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

def start_vacation(context):
    """Начало оформления отпуска"""
    user_id = get_safe_user_id(context)
    
    # Проверяем, авторизован ли пользователь
    if user_id not in authenticated_users:
        context.reply("❌ Для оформления отпуска необходимо авторизоваться.")
        return
    
    db_user_id = get_db_user_id(user_id)
    if not db_user_id:
        context.reply("❌ Не удалось найти ваш профиль в системе. Обратитесь к администратору.")
        return
    
    # Инициализируем сессию для пользователя
    vacation_sessions[user_id] = {
        'step': 'dates',
        'start_date': '',
        'end_date': '',
        'days_count': 0,
        'db_user_id': db_user_id
    }
    
    message = "🏖️ Оформление заявки на отпуск\n\n"
    message += "У тебя доступно 28 дней основного отпуска.\n"
    message += "На какие даты планируешь?\n\n"
    message += "📅 Введите даты отпуска в формате:\n"
    message += "• ДД.ММ.ГГГГ-ДД.ММ.ГГГГ (например, 01.07.2024-15.07.2024)\n"
    message += "• Или введите даты по отдельности\n\n"
    message += "Сначала введите дату начала отпуска:"
    
    keyboard = InlineKeyboard(
        [{"text": "❌ Отмена", "callback": "cancel_vacation"}]
    )
    
    context.reply_callback(message, keyboard=keyboard)

def handle_vacation_dates(context, text):
    """Обработка ввода дат отпуска"""
    user_id = get_safe_user_id(context)
    
    if user_id not in vacation_sessions:
        context.reply("❌ Сессия устарела. Начните заново.")
        return
    
    # Пробуем распарсить диапазон дат (формат ДД.ММ.ГГГГ-ДД.ММ.ГГГГ)
    date_range_match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
    
    if date_range_match:
        # Обработка диапазона дат
        day1, month1, year1, day2, month2, year2 = map(int, date_range_match.groups())
        try:
            start_date = datetime(year1, month1, day1)
            end_date = datetime(year2, month2, day2)
            
            # Проверяем корректность дат
            if end_date <= start_date:
                context.reply("❌ Дата окончания должна быть позже даты начала!")
                return
            
            # Сохраняем даты
            vacation_sessions[user_id]['start_date'] = start_date
            vacation_sessions[user_id]['end_date'] = end_date
            vacation_sessions[user_id]['days_count'] = (end_date - start_date).days + 1
            
            # Переходим к подтверждению
            confirm_vacation(context, user_id)
            return
            
        except ValueError:
            context.reply("❌ Неверный формат дат. Попробуйте снова.")
            return
    
    # Если не диапазон, пробуем распарсить одну дату (начало отпуска)
    date_result = parse_date_input(text.strip())
    if date_result:
        if not vacation_sessions[user_id]['start_date']:
            # Это дата начала
            vacation_sessions[user_id]['start_date'] = date_result
            vacation_sessions[user_id]['step'] = 'end_date'
            
            message = f"✅ Дата начала: {date_result.strftime('%d.%m.%Y')}\n\n"
            message += "📅 Теперь введите дату окончания отпуска:\n\n"
            message += "Формат: ДД.ММ.ГГГГ (например, 15.07.2024)\n"
            message += "Или используйте специальные команды:\n"
            message += "• 'через 14 дней' - через указанное количество дней от начала"
            
            keyboard = InlineKeyboard(
                [{"text": "❌ Отмена", "callback": "cancel_vacation"}]
            )
            
            context.reply(message, keyboard=keyboard)
            return
        else:
            # Это дата окончания
            start_date = vacation_sessions[user_id]['start_date']
            
            # Проверяем, что дата окончания после даты начала
            if date_result <= start_date:
                context.reply("❌ Дата окончания должна быть позже даты начала!")
                return
            
            vacation_sessions[user_id]['end_date'] = date_result
            vacation_sessions[user_id]['days_count'] = (date_result - start_date).days + 1
            
            # Переходим к подтверждению
            confirm_vacation(context, user_id)
            return
    
    context.reply("❌ Неверный формат дат. Используйте ДД.ММ.ГГГГ-ДД.ММ.ГГГГ или вводите даты по отдельности")

def confirm_vacation(context, user_id):
    """Подтверждение данных отпуска"""
    session_data = vacation_sessions[user_id]
    start_date = session_data['start_date']
    end_date = session_data['end_date']
    days_count = session_data['days_count']
    
    # Проверяем, не превышает ли отпуск доступные дни
    available_days = 28
    if days_count > available_days:
        message = f"❌ Превышен лимит отпускных дней!\n\n"
        message += f"Доступно: {available_days} дней\n"
        message += f"Запрошено: {days_count} дней\n\n"
        message += "Пожалуйста, выберите более короткий период."
        
        # Сбрасываем даты
        vacation_sessions[user_id]['start_date'] = ''
        vacation_sessions[user_id]['end_date'] = ''
        vacation_sessions[user_id]['days_count'] = 0
        vacation_sessions[user_id]['step'] = 'dates'
        
        keyboard = InlineKeyboard(
            [{"text": "🔄 Ввести другие даты", "callback": "arrange_vacation"}],
            [{"text": "❌ Отмена", "callback": "cancel_vacation"}]
        )
        
        context.reply(message, keyboard=keyboard)
        return
    
    message = "✅ Проверьте данные отпуска:\n\n"
    message += f"📅 Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n"
    message += f"⏰ Количество дней: {days_count}\n"
    message += f"📋 Доступно дней: {available_days}\n\n"
    message += "Всё верно?"
    
    keyboard = InlineKeyboard(
        [{"text": "✅ Да, отправить на согласование", "callback": "submit_vacation"}],
        [{"text": "🔄 Ввести другие даты", "callback": "arrange_vacation"}],
        [{"text": "❌ Отмена", "callback": "cancel_vacation"}]
    )
    
    context.reply(message, keyboard=keyboard)

def submit_vacation(context):
    """Отправка заявки на отпуск"""
    user_id = get_safe_user_id(context)
    
    if user_id not in vacation_sessions:
        context.reply("❌ Сессия устарела. Начните заново.")
        return
    
    # Сохраняем заявку в БД
    success = save_vacation_to_db(user_id)
    
    if success:
        session_data = vacation_sessions[user_id]
        start_date = session_data['start_date']
        end_date = session_data['end_date']
        days_count = session_data['days_count']
        
        message = "✅ Заявление создано и отправлено на согласование руководителю!\n\n"
        message += f"📅 Период отпуска: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n"
        message += f"⏰ Количество дней: {days_count}\n"
        message += f"⏳ Статус: Ожидание согласования\n\n"
        message += "Вы получите уведомление о смене статуса."
        
        # Очищаем сессию
        del vacation_sessions[user_id]
    else:
        message = "❌ Ошибка при сохранении заявки. Попробуйте позже."
    
    keyboard = InlineKeyboard(
        [{"text": "🏠 Главное меню", "callback": "back_to_menu"}]
    )
    
    context.reply_callback(message, keyboard=keyboard)

def cancel_vacation(context):
    """Отмена оформления отпуска"""
    user_id = get_safe_user_id(context)
    
    if user_id in vacation_sessions:
        del vacation_sessions[user_id]
    
    message = "❌ Оформление отпуска отменено."
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

def save_vacation_to_db(user_id):
    """Сохраняет заявку на отпуск в БД"""
    try:
        if user_id not in vacation_sessions:
            return False
        
        session_data = vacation_sessions[user_id]
        
        # Используем user_id из базы данных
        db_user_id = session_data['db_user_id']
        
        # Получаем rector_id (ответственный - ректор)
        rector_id = get_random_rector_id()
        
        with db.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO vacations 
                (user_id, start_date, end_date, days_count, rector_id, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
            """, (
                db_user_id,
                session_data['start_date'],
                session_data['end_date'],
                session_data['days_count'],
                rector_id
            ))
            
            db.conn.commit()
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении отпуска в БД: {e}")
        db.conn.rollback()
        return False

def get_random_rector_id():
    """Получает ID случайного ректора из БД"""
    try:
        with db.conn.cursor() as cur:
            cur.execute("""
                SELECT user_id FROM users 
                WHERE role = 'rector' 
                LIMIT 1
            """)
            result = cur.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Ошибка при получении ректора: {e}")
        return None

def process_vacation_message(context, text):
    """Обрабатывает текстовые сообщения для отпуска"""
    user_id = get_safe_user_id(context)
    
    if user_id not in vacation_sessions:
        return False
    
    session = vacation_sessions[user_id]
    
    if session['step'] in ['dates', 'end_date']:
        handle_vacation_dates(context, text)
        return True
    
    return False
from config import logger, db
from maxgram.keyboards import InlineKeyboard
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

def check_and_show_notifications(context):
    """Проверяет и показывает непрочитанные уведомления"""
    user_id = get_safe_user_id(context)
    
    # Проверяем, авторизован ли пользователь
    if user_id not in authenticated_users:
        return
    
    db_user_id = get_db_user_id(user_id)
    if not db_user_id:
        return
    
    # Получаем непрочитанные уведомления
    notifications = get_unread_notifications(db_user_id)
    
    if notifications:
        # Показываем уведомления
        show_notifications(context, notifications)
        
        # Помечаем как прочитанные
        mark_notifications_as_read(notifications)
    else:
        # Если уведомлений нет, можно показать сообщение
        context.reply("📭 У вас нет новых уведомлений.")

def get_unread_notifications(user_id):
    """Получает непрочитанные уведомления для пользователя"""
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT notification_id, type, title, message, created_at
                FROM notifications 
                WHERE user_id = %s AND is_read = FALSE
                ORDER BY created_at DESC
                LIMIT 10
            """, (user_id,))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении уведомлений: {e}")
        return []

def mark_notifications_as_read(notifications):
    """Помечает уведомления как прочитанные"""
    if not notifications:
        return
    
    try:
        notification_ids = [str(n['notification_id']) for n in notifications]
        placeholders = ','.join(['%s'] * len(notification_ids))
        
        with db.conn.cursor() as cur:
            cur.execute(f"""
                UPDATE notifications 
                SET is_read = TRUE 
                WHERE notification_id IN ({placeholders})
            """, notification_ids)
            
            db.conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при обновлении уведомлений: {e}")
        db.conn.rollback()

def show_notifications(context, notifications):
    """Показывает уведомления пользователю"""
    message = "🔔 Ваши уведомления:\n\n"
    
    for i, notification in enumerate(notifications, 1):
        # Форматируем дату
        created_at = notification['created_at'].strftime('%d.%m.%Y %H:%M')
        
        message += f"{i}. {notification['title']}\n"
        message += f"   {notification['message']}\n"
        message += f"   📅 {created_at}\n\n"
    
    keyboard = InlineKeyboard(
        [{"text": "✅ Понятно", "callback": "back_to_menu"}]
    )
    
    context.reply(message, keyboard=keyboard)

def get_notifications_count(user_id):
    """Получает количество непрочитанных уведомлений"""
    try:
        with db.conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as count
                FROM notifications 
                WHERE user_id = %s AND is_read = FALSE
            """, (user_id,))
            result = cur.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Ошибка при получении количества уведомлений: {e}")
        return 0
# Добавить в конец notification_handler.py

def create_notification(user_id, notification_type, title, message, related_id=None):
    """Создает новое уведомление в базе данных"""
    try:
        with db.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO notifications (user_id, type, title, message, related_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, notification_type, title, message, related_id))
            db.conn.commit()
            logger.info(f"Создано уведомление для пользователя {user_id}: {title}")
            return True
    except Exception as e:
        logger.error(f"Ошибка при создании уведомления: {e}")
        db.conn.rollback()
        return False



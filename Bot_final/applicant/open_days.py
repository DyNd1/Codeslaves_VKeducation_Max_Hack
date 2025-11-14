from maxgram import Bot
from maxgram.keyboards import InlineKeyboard
from psycopg2.extras import RealDictCursor



def get_upcoming_open_days(conn):
    """Получить ближайшие дни открытых дверей"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    od.event_id,
                    f.faculty_name,
                    TO_CHAR(od.event_date, 'DD.MM.YYYY HH24:MI') as event_date,
                    od.description,
                    od.max_participants,
                    COUNT(odr.registration_id) as registered_count,
                    (od.max_participants - COUNT(odr.registration_id)) as available_places
                FROM open_days od
                JOIN faculties f ON od.faculty_id = f.faculty_id
                LEFT JOIN open_day_registrations odr ON od.event_id = odr.event_id
                WHERE od.event_date >= CURRENT_DATE
                GROUP BY od.event_id, f.faculty_name, od.event_date, od.description, od.max_participants
                ORDER BY od.event_date ASC
                LIMIT 5
            """)
            return cur.fetchall()
    except Exception as e:
        print(f"Ошибка получения дней открытых дверей: {e}")
        return []


def format_open_days_message(open_days, idx):
    """Форматирует список дней открытых дверей в читаемое сообщение"""
    if not open_days:
        return "📅 На данный момент нет запланированных дней открытых дверей."

    message = ""
    event = open_days[idx - 1]

    message += f"{idx}. 🏛 **{event['faculty_name']}**\n"
    message += f"   📅 Дата: {event['event_date']}\n"
    message += f"   📖 {event['description']}\n"
    message += f"   👥 Мест: {event['registered_count']}/{event['max_participants']} "

    if event['available_places'] > 0:
        message += f"(свободно: {event['available_places']})\n"
    else:
        message += "❌ ЗАПОЛНЕНО\n"

    message += f"   🆔 ID события: {event['event_id']}\n\n"

    message += "ℹ️ Для регистрации нажмите на соответствующую кнопку ниже."

    return message


def is_user_registered(conn, event_id, max_id):
    """Проверить, зарегистрирован ли пользователь на событие"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM open_day_registrations 
                WHERE event_id = %s AND max_id = %s
            """, (event_id, max_id))
            return cur.fetchone() is not None
    except Exception as e:
        print(f"Ошибка проверки регистрации: {e}")
        return False


def get_open_day_by_id(conn, event_id):
    """Получить событие дня открытых дверей по ID"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    od.event_id,
                    f.faculty_name,
                    TO_CHAR(od.event_date, 'DD.MM.YYYY HH24:MI') as event_date,
                    od.description,
                    od.max_participants,
                    COUNT(odr.registration_id) as registered_count,
                    (od.max_participants - COUNT(odr.registration_id)) as available_places,
                    CASE 
                        WHEN (od.max_participants - COUNT(odr.registration_id)) <= 0 THEN false
                        ELSE true
                    END as can_register
                FROM open_days od
                JOIN faculties f ON od.faculty_id = f.faculty_id
                LEFT JOIN open_day_registrations odr ON od.event_id = odr.event_id
                WHERE od.event_id = %s
                GROUP BY od.event_id, f.faculty_name, od.event_date, od.description, od.max_participants
            """, (event_id,))
            return cur.fetchone()
    except Exception as e:
        print(f"Ошибка получения события: {e}")
        return None



from config import db, logger
from datetime import datetime
from psycopg2.extras import RealDictCursor
from handlers.authorization_handler import authenticated_users
from maxgram.keyboards import InlineKeyboard

def get_db_user_id(chat_id):
    """Получает user_id из базы данных для авторизованного пользователя"""
    if chat_id in authenticated_users:
        user_data = authenticated_users[chat_id]
        if 'user_info' in user_data and 'user_id' in user_data['user_info']:
            return user_data['user_info']['user_id']
    return None

def get_rector_stats():
    """Собирает всю статистику для дашборда ректора"""
    stats = {}
    
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Средняя успеваемость студентов
            cur.execute("""
                SELECT ROUND(AVG(grade), 2) as avg_gpa 
                FROM student_grades
            """)
            stats['avg_gpa'] = cur.fetchone()['avg_gpa'] or 0.0
            
            # 2. Количество новостей
            cur.execute("SELECT COUNT(*) as count FROM news")
            stats['news_count'] = cur.fetchone()['count']
            
            # 3. Количество студентов
            cur.execute("SELECT COUNT(*) as count FROM users WHERE role = 'student'")
            stats['students_count'] = cur.fetchone()['count']
            
            # 4. Количество преподавателей
            cur.execute("SELECT COUNT(*) as count FROM users WHERE role = 'teacher'")
            stats['teachers_count'] = cur.fetchone()['count']
            
            # 5. Количество проектов
            cur.execute("SELECT COUNT(*) as count FROM projects")
            stats['projects_count'] = cur.fetchone()['count']
            
            # 6. Активные проекты
            cur.execute("SELECT COUNT(*) as count FROM projects WHERE status = 'active'")
            stats['active_projects_count'] = cur.fetchone()['count']
            
            # 7. Количество заявок на цифровую кафедру
            cur.execute("SELECT COUNT(*) as count FROM digital_department_applications")
            stats['digital_applications_count'] = cur.fetchone()['count']
            
            # 8. Заявки на цифровую кафедру по статусам
            cur.execute("""
                SELECT status, COUNT(*) as count 
                FROM digital_department_applications 
                GROUP BY status
            """)
            digital_statuses = cur.fetchall()
            stats['digital_pending'] = 0
            stats['digital_approved'] = 0
            stats['digital_rejected'] = 0
            for status in digital_statuses:
                if status['status'] == 'pending':
                    stats['digital_pending'] = status['count']
                elif status['status'] == 'approved':
                    stats['digital_approved'] = status['count']
                elif status['status'] == 'rejected':
                    stats['digital_rejected'] = status['count']
            
            # 9. Количество регистраций на открытые дни
            cur.execute("SELECT COUNT(*) as count FROM open_day_registrations")
            stats['open_day_registrations'] = cur.fetchone()['count']
            
            # 10. Популярность факультетов по регистрациям на открытые дни
            cur.execute("""
                SELECT f.faculty_name, COUNT(odr.registration_id) as registrations_count
                FROM faculties f
                LEFT JOIN open_days od ON f.faculty_id = od.faculty_id
                LEFT JOIN open_day_registrations odr ON od.event_id = odr.event_id
                GROUP BY f.faculty_id, f.faculty_name
                ORDER BY registrations_count DESC
                LIMIT 5
            """)
            stats['popular_faculties'] = cur.fetchall()
            
            # 11. Статистика по образовательным программам
            cur.execute("""
                SELECT COUNT(*) as total_programs,
                       SUM(budget_places) as total_budget_places,
                       AVG(last_year_pass_score) as avg_pass_score
                FROM educational_programs
            """)
            programs_stats = cur.fetchone()
            stats['total_programs'] = programs_stats['total_programs']
            stats['total_budget_places'] = programs_stats['total_budget_places'] or 0
            stats['avg_pass_score'] = round(programs_stats['avg_pass_score'] or 0)
            
            # 12. Количество абитуриентов
            cur.execute("SELECT COUNT(*) as count FROM users WHERE role = 'applicant'")
            stats['applicants_count'] = cur.fetchone()['count']
            
            # 13. Статистика заявок на проекты
            cur.execute("""
                SELECT COUNT(*) as total_applications,
                       SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_applications,
                       SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved_applications
                FROM project_applications
            """)
            project_apps = cur.fetchone()
            stats['project_applications_total'] = project_apps['total_applications']
            stats['project_applications_pending'] = project_apps['pending_applications']
            stats['project_applications_approved'] = project_apps['approved_applications']
            
            # 14. Статистика по командировкам и отпускам
            cur.execute("""
                SELECT status, COUNT(*) as count 
                FROM business_trips 
                GROUP BY status
            """)
            trips_stats = cur.fetchall()
            stats['trips_pending'] = 0
            stats['trips_approved'] = 0
            for trip in trips_stats:
                if trip['status'] == 'pending':
                    stats['trips_pending'] = trip['count']
                elif trip['status'] == 'approved':
                    stats['trips_approved'] = trip['count']
            
            cur.execute("""
                SELECT status, COUNT(*) as count 
                FROM vacations 
                GROUP BY status
            """)
            vacations_stats = cur.fetchall()
            stats['vacations_pending'] = 0
            stats['vacations_approved'] = 0
            for vacation in vacations_stats:
                if vacation['status'] == 'pending':
                    stats['vacations_pending'] = vacation['count']
                elif vacation['status'] == 'approved':
                    stats['vacations_approved'] = vacation['count']
            
            # 15. Активность библиотеки
            cur.execute("SELECT COUNT(*) as count FROM book_reservations")
            stats['book_reservations'] = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM books")
            stats['total_books'] = cur.fetchone()['count']
            
    except Exception as e:
        logger.error(f"Ошибка при сборе статистики для дашборда: {e}")
    
    return stats

def show_rector_dashboard(context):
    """Показывает дашборд ректора"""
    chat_id = context.message['recipient']['chat_id']
    db_user_id = get_db_user_id(chat_id)
    
    if not db_user_id:
        context.reply("❌ Вы не авторизованы.")
        return
    
    # Проверяем, что пользователь - ректор
    user_query = "SELECT role FROM users WHERE user_id = %s"
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(user_query, (db_user_id,))
            user_result = cur.fetchone()
            
            if not user_result or user_result['role'] != 'rector':
                context.reply("❌ Эта функция доступна только ректору.")
                return
    except Exception as e:
        logger.error(f"Ошибка при проверке роли пользователя: {e}")
        context.reply("❌ Произошла ошибка.")
        return
    
    # Собираем статистику
    stats = get_rector_stats()
    
    # Формируем сообщение с дашбордом
    message = "🎯 Дэшборд ректора \n\n"
    message += f"📊 Общая статистика университета\n"
    message += f"────────────────────\n\n"
    
    # Основные показатели
    message += f"👥 Студенты и преподаватели:\n"
    message += f"• 🎓 Студентов: {stats['students_count']}\n"
    message += f"• 👨‍🏫 Преподавателей: {stats['teachers_count']}\n"
    message += f"• 📝 Абитуриентов: {stats['applicants_count']}\n"
    message += f"• 📚 Средний GPA: {stats['avg_gpa']}\n\n"
    
    # Образовательные программы
    message += f"📚 Образовательные программы:\n"
    message += f"• 🏛️ Всего программ: {stats['total_programs']}\n"
    message += f"• 💰 Бюджетных мест: {stats['total_budget_places']}\n"
    message += f"• 🎯 Средний проходной балл: {stats['avg_pass_score']}\n\n"
    
    # Проектная деятельность
    message += f"🚀 Проектная деятельность:\n"
    message += f"• 📂 Всего проектов: {stats['projects_count']}\n"
    message += f"• 🔥 Активных проектов: {stats['active_projects_count']}\n"
    message += f"• 📋 Заявок на проекты: {stats['project_applications_total']}\n"
    message += f"  ├─ ⏳ Ожидают решения: {stats['project_applications_pending']}\n"
    message += f"  └─ ✅ Одобрено: {stats['project_applications_approved']}\n\n"
    
    # Цифровая кафедра
    message += f"💻 Цифровая кафедра:\n"
    message += f"• 📨 Всего заявок: {stats['digital_applications_count']}\n"
    message += f"  ├─ ⏳ На рассмотрении: {stats['digital_pending']}\n"
    message += f"  ├─ ✅ Одобрено: {stats['digital_approved']}\n"
    message += f"  └─ ❌ Отклонено: {stats['digital_rejected']}\n\n"
    
    # Мероприятия
    message += f"📅 Мероприятия:\n"
    message += f"• 🎪 Регистраций на дни открытых дверей: {stats['open_day_registrations']}\n"
    message += f"• 📰 Новостей в системе: {stats['news_count']}\n\n"
    
    # Административные заявки
    message += f"📋 Административные заявки:\n"
    message += f"• 🛫 Командировки:\n"
    message += f"  ├─ ⏳ Ожидают: {stats['trips_pending']}\n"
    message += f"  └─ ✅ Одобрено: {stats['trips_approved']}\n"
    message += f"• 🏖️ Отпуска:\n"
    message += f"  ├─ ⏳ Ожидают: {stats['vacations_pending']}\n"
    message += f"  └─ ✅ Одобрено: {stats['vacations_approved']}\n\n"
    
    # Библиотека
    message += f"📖 Библиотека:\n"
    message += f"• 📚 Всего книг: {stats['total_books']}\n"
    message += f"• 🔖 Бронирований: {stats['book_reservations']}\n\n"
    
    # Популярные факультеты
    if stats['popular_faculties']:
        message += f"🏆 Топ-5 факультетов по популярности:\n"
        for i, faculty in enumerate(stats['popular_faculties'][:5], 1):
            message += f"{i}. {faculty['faculty_name']} - {faculty['registrations_count']} регистраций\n"
    
    message += f"\n📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"

    keyboard = InlineKeyboard(
        [{"text": "🔄 Обновить статистику", "callback": "rector_stats"}],
        [{"text": "🔙 Назад", "callback": "back_to_menu"}]
    )
    
    context.reply(message, keyboard=keyboard)

def show_detailed_analytics(context):
    """Показывает расширенную аналитику"""
    # Здесь можно добавить более детальную аналитику
    # Например, графики, тренды, сравнения по периодам и т.д.
    
    message = "📈 Расширенная аналитика*\n\n"
    message += "Здесь будет детализированная аналитика с графиками и трендами:\n\n"
    message += "• 📊 Динамика успеваемости по семестрам\n"
    message += "• 📈 Рост количества проектов\n"
    message += "• 🎯 Эффективность цифровой кафедры\n"
    message += "• 👥 Распределение студентов по факультетам\n"
    message += "• 💰 Бюджетные vs платные места\n\n"
    message += "🛠 *Функция в разработке*"
    

    keyboard = InlineKeyboard(
        [{"text": "📊 Основной дашборд", "callback": "rector_stats"}],
        [{"text": "🔙 Назад", "callback": "back_to_menu"}]
    )
    
    context.reply(message, keyboard=keyboard)
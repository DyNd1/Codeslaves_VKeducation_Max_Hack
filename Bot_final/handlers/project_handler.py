from config import db, logger
from keyboards.menus import get_student_keyboard
from psycopg2.extras import RealDictCursor
from handlers.authorization_handler import authenticated_users
from maxgram.keyboards import InlineKeyboard

# Хранилище состояний для создания проекта
project_creation_sessions = {}

def get_db_user_id(chat_id):
    """Получает user_id из базы данных для авторизованного пользователя"""
    if chat_id in authenticated_users:
        user_data = authenticated_users[chat_id]
        if 'user_info' in user_data and 'user_id' in user_data['user_info']:
            return user_data['user_info']['user_id']
    return None

def start_project_creation(context):
    """Начинает процесс создания проекта"""
    chat_id = context.message['recipient']['chat_id']
    db_user_id = get_db_user_id(chat_id)
    
    if not db_user_id:
        context.reply("❌ Вы не авторизованы.")
        return
    
    # Инициализируем сессию создания проекта
    project_creation_sessions[chat_id] = {
        'db_user_id': db_user_id,
        'step': 'awaiting_title',
        'project_data': {}
    }
    
    message = "🚀 *Давай создадим твой проект!*\n\nОтветь на несколько вопросов.\n\n*Название проекта:*"
    context.reply(message)

def process_project_creation(context, text):
    """Обрабатывает шаги создания проекта"""
    chat_id = context.message['recipient']['chat_id']
    
    if chat_id not in project_creation_sessions:
        return False
    
    session = project_creation_sessions[chat_id]
    step = session['step']
    
    if text == "/cancel":
        del project_creation_sessions[chat_id]
        context.reply("❌ Создание проекта отменено.", keyboard=get_student_keyboard())
        return True
    
    if step == 'awaiting_title':
        if len(text) < 3:
            context.reply("❌ Название проекта должно содержать минимум 3 символа. Попробуйте еще раз:")
            return True
        
        session['project_data']['title'] = text
        session['step'] = 'awaiting_description'
        context.reply("📝 *Описание проекта:*")
        return True
    
    elif step == 'awaiting_description':
        if len(text) < 10:
            context.reply("❌ Описание должно содержать минимум 10 символов. Попробуйте еще раз:")
            return True
        
        session['project_data']['description'] = text
        session['step'] = 'awaiting_roles'
        context.reply("👥 *Какие роли нужны в команде?*\n(например: бэкенд-разработчик, дизайнер, фронтенд-разработчик)")
        return True
    
    elif step == 'awaiting_roles':
        if len(text) < 3:
            context.reply("❌ Укажите хотя бы одну роль. Попробуйте еще раз:")
            return True
        
        session['project_data']['required_roles'] = text
        
        # Создаем проект в базе данных
        try:
            with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO projects (creator_id, title, description, required_roles)
                    VALUES (%s, %s, %s, %s)
                    RETURNING project_id
                """, (
                    session['db_user_id'],
                    session['project_data']['title'],
                    session['project_data']['description'],
                    session['project_data']['required_roles']
                ))
                result = cur.fetchone()
                db.conn.commit()
                
                # Добавляем создателя как участника проекта
                cur.execute("""
                    INSERT INTO project_members (project_id, user_id, role)
                    VALUES (%s, %s, 'Создатель проекта')
                """, (result['project_id'], session['db_user_id']))
                db.conn.commit()
                
                # Отправляем сообщение об успехе
                message = f"🎉 *Проект \"{session['project_data']['title']}\" опубликован!*\n\n"
                message += f"📝 *Описание:* {session['project_data']['description']}\n"
                message += f"👥 *Нужные роли:* {session['project_data']['required_roles']}\n\n"
                message += "Теперь другие студенты смогут на него откликнуться!"
                
                # Очищаем сессию
                del project_creation_sessions[chat_id]
                
                context.reply(message, keyboard=get_student_keyboard())
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при создании проекта: {e}")
            db.conn.rollback()
            context.reply("❌ Произошла ошибка при создании проекта. Попробуйте позже.")
            del project_creation_sessions[chat_id]
            return True
    
    return False

def get_available_projects(user_id):
    """Получает доступные проекты для присоединения"""
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT p.*, 
                       u.first_name || ' ' || u.last_name as creator_name,
                       (SELECT COUNT(*) FROM project_members pm WHERE pm.project_id = p.project_id) as team_size
                FROM projects p
                JOIN users u ON p.creator_id = u.user_id
                WHERE p.status = 'active'
                AND p.creator_id != %s
                AND p.project_id NOT IN (
                    SELECT project_id FROM project_members WHERE user_id = %s
                )
                AND p.project_id NOT IN (
                    SELECT project_id FROM project_applications WHERE user_id = %s AND status = 'pending'
                )
                ORDER BY p.created_at DESC
            """, (user_id, user_id, user_id))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении проектов: {e}")
        return []

def show_available_projects(context):
    """Показывает доступные проекты для присоединения"""
    chat_id = context.message['recipient']['chat_id']
    db_user_id = get_db_user_id(chat_id)
    
    if not db_user_id:
        context.reply("❌ Вы не авторизованы.")
        return
    
    projects = get_available_projects(db_user_id)
    
    if not projects:
        context.reply("📭 В настоящее время нет доступных проектов для присоединения.")
        return


    
    message = "📋 *Доступные проекты:*\n\n"
    keyboard_rows = []
    
    for i, project in enumerate(projects, 1):
        message += f"{i}. *{project['title']}*\n"
        message += f"   👤 Создатель: {project['creator_name']}\n"
        message += f"   👥 Команда: {project['team_size']} человек\n"
        message += f"   📅 Создан: {project['created_at'].strftime('%d.%m.%Y')}\n\n"
        
        keyboard_rows.append([
            {"text": f"📁 {project['title'][:30]}...", 
             "callback": f"view_project_{project['project_id']}"}
        ])
    
    keyboard_rows.append([{"text": "🔙 Назад", "callback": "back_to_menu"}])
    keyboard = InlineKeyboard(*keyboard_rows)
    
    context.reply(message, keyboard=keyboard)

def show_project_details(context, project_id):
    """Показывает детали проекта"""
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT p.*, 
                       u.first_name || ' ' || u.last_name as creator_name,
                       (SELECT COUNT(*) FROM project_members pm WHERE pm.project_id = p.project_id) as team_size
                FROM projects p
                JOIN users u ON p.creator_id = u.user_id
                WHERE p.project_id = %s
            """, (project_id,))
            project = cur.fetchone()
            
            if not project:
                context.reply_callback("❌ Проект не найден.")
                return
            
            # Получаем участников проекта
            cur.execute("""
                SELECT pm.*, u.first_name, u.last_name
                FROM project_members pm
                JOIN users u ON pm.user_id = u.user_id
                WHERE pm.project_id = %s AND pm.status = 'active'
                ORDER BY pm.joined_at
            """, (project_id,))
            members = cur.fetchall()
            
            message = f"📁 {project['title']}\n\n"
            message += f"📝 Описание: {project['description']}\n\n"
            message += f"👥 Нужные роли: {project['required_roles']}\n\n"
            message += f"👤 Создатель: {project['creator_name']}\n"
            message += f"🕒 Создан: {project['created_at'].strftime('%d.%m.%Y')}\n\n"
            
            if members:
                message += "Команда:\n"
                for member in members:
                    message += f"• {member['first_name']} {member['last_name']} - {member['role']}\n"

            
            chat_id = context.message['recipient']['chat_id']
            db_user_id = get_db_user_id(chat_id)
            
            # Проверяем, не подал ли уже пользователь заявку
            cur.execute("""
                SELECT * FROM project_applications 
                WHERE project_id = %s AND user_id = %s AND status = 'pending'
            """, (project_id, db_user_id))
            existing_application = cur.fetchone()
            
            keyboard_rows = []
            
            if not existing_application:
                keyboard_rows.append([
                    {"text": "✅ Присоединиться", "callback": f"join_project_{project_id}"}
                ])
            
            keyboard_rows.append([{"text": "🔙 Назад к проектам", "callback": "Join_project"}])
            keyboard_rows.append([{"text": "🏠 Главное меню", "callback": "back_to_menu"}])
            
            keyboard = InlineKeyboard(*keyboard_rows)
            
            context.reply_callback(message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Ошибка при получении деталей проекта: {e}")
        context.reply_callback("❌ Произошла ошибка при загрузке проекта.")

def join_project(context, project_id):
    """Обрабатывает присоединение к проекту"""
    chat_id = context.message['recipient']['chat_id']
    db_user_id = get_db_user_id(chat_id)
    
    if not db_user_id:
        context.reply_callback("❌ Вы не авторизованы.")
        return
    
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Проверяем, не подал ли уже заявку
            cur.execute("""
                SELECT * FROM project_applications 
                WHERE project_id = %s AND user_id = %s AND status = 'pending'
            """, (project_id, db_user_id))
            existing = cur.fetchone()
            
            if existing:
                context.reply_callback("❌ Вы уже подали заявку на этот проект.")
                return
            
            # Получаем название проекта для уведомления
            cur.execute("SELECT title FROM projects WHERE project_id = %s", (project_id,))
            project = cur.fetchone()
            
            # Создаем заявку (роль будет определена создателем позже)
            cur.execute("""
                INSERT INTO project_applications (project_id, user_id, desired_role, message)
                VALUES (%s, %s, %s, %s)
            """, (project_id, db_user_id, "Участник", "Хочу присоединиться к проекту"))
            db.conn.commit()
            
            message = f"✅ Вы отправили заявку на присоединение к проекту \"{project['title']}\"!*\n\n"
            message += "Создатель проекта рассмотрит вашу заявку и уведомит о решении."
            
            context.reply_callback(message, keyboard=get_student_keyboard())
            
    except Exception as e:
        logger.error(f"Ошибка при подаче заявки на проект: {e}")
        db.conn.rollback()
        context.reply_callback("❌ Произошла ошибка при подаче заявки. Попробуйте позже.")

def show_my_projects(context):
    """Показывает проекты пользователя"""
    chat_id = context.message['recipient']['chat_id']
    db_user_id = get_db_user_id(chat_id)
    
    if not db_user_id:
        context.reply("❌ Вы не авторизованы.")
        return
    
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Проекты, созданные пользователем
            cur.execute("""
                SELECT p.*, 
                       (SELECT COUNT(*) FROM project_members pm WHERE pm.project_id = p.project_id) as team_size,
                       (SELECT COUNT(*) FROM project_applications pa WHERE pa.project_id = p.project_id AND pa.status = 'pending') as pending_applications
                FROM projects p
                WHERE p.creator_id = %s
                ORDER BY p.created_at DESC
            """, (db_user_id,))
            created_projects = cur.fetchall()
            
            # Проекты, в которых пользователь участвует
            cur.execute("""
                SELECT p.*, pm.role,
                       (SELECT COUNT(*) FROM project_members pm2 WHERE pm2.project_id = p.project_id) as team_size
                FROM projects p
                JOIN project_members pm ON p.project_id = pm.project_id
                WHERE pm.user_id = %s AND pm.status = 'active'
                ORDER BY pm.joined_at DESC
            """, (db_user_id,))
            participating_projects = cur.fetchall()
            
            message = "📂 Мои проекты\n\n"
            
            if created_projects:
                message += "🎯 Созданные мной проекты:\n"
                for project in created_projects:
                    applications_text = f" ({project['pending_applications']} заявок)" if project['pending_applications'] > 0 else ""
                    message += f"• *{project['title']}* ({project['team_size']} участников){applications_text}\n"
                message += "\n"
            
            if participating_projects:
                message += "👥 Проекты, в которых я участвую:\n"
                for project in participating_projects:
                    message += f"• *{project['title']}* - {project['role']} ({project['team_size']} участников)\n"
            
            if not created_projects and not participating_projects:
                message += "📭 У вас пока нет проектов.\n\nСоздайте свой первый проект или присоединитесь к существующему!"

            keyboard_rows = []
            
            if created_projects:
                for project in created_projects:
                    if project['pending_applications'] > 0:
                        keyboard_rows.append([
                            {"text": f"📋 Управлять {project['title'][:20]}...", 
                             "callback": f"manage_project_{project['project_id']}"}
                        ])
                    else:
                        keyboard_rows.append([
                            {"text": f"👀 Просмотреть {project['title'][:20]}...", 
                             "callback": f"view_my_project_{project['project_id']}"}
                        ])
            
            keyboard_rows.append([{"text": "🚀 Создать проект", "callback": "create_project"}])
            keyboard_rows.append([{"text": "👥 Присоединиться к проекту", "callback": "Join_project"}])
            keyboard_rows.append([{"text": "🔙 Назад", "callback": "back_to_menu"}])
            
            keyboard = InlineKeyboard(*keyboard_rows)
            
            context.reply(message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Ошибка при получении проектов пользователя: {e}")
        context.reply("❌ Произошла ошибка при загрузке ваших проектов.")

def show_my_project_details(context, project_id):
    """Показывает детали проекта создателя"""
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT p.*, 
                       (SELECT COUNT(*) FROM project_members pm WHERE pm.project_id = p.project_id) as team_size
                FROM projects p
                WHERE p.project_id = %s
            """, (project_id,))
            project = cur.fetchone()
            
            if not project:
                context.reply_callback("❌ Проект не найден.")
                return
            
            # Получаем участников проекта
            cur.execute("""
                SELECT pm.*, u.first_name, u.last_name
                FROM project_members pm
                JOIN users u ON pm.user_id = u.user_id
                WHERE pm.project_id = %s AND pm.status = 'active'
                ORDER BY pm.joined_at
            """, (project_id,))
            members = cur.fetchall()
            
            message = f"📁 {project['title']}\n\n"
            message += f"📝 Описание: {project['description']}\n\n"
            message += f"👥 Нужные роли: {project['required_roles']}\n\n"
            message += f"🕒 Создан: {project['created_at'].strftime('%d.%m.%Y')}\n\n"
            
            if members:
                message += "Команда:\n"
                for member in members:
                    message += f"• {member['first_name']} {member['last_name']} - {member['role']}\n"

            
            keyboard_rows = [
                [{"text": "📋 Управлять заявками", "callback": f"manage_project_{project_id}"}],
                [{"text": "🔙 Назад к моим проектам", "callback": "my_projects"}],
                [{"text": "🏠 Главное меню", "callback": "back_to_menu"}]
            ]
            
            keyboard = InlineKeyboard(*keyboard_rows)
            
            context.reply_callback(message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Ошибка при получении деталей проекта: {e}")
        context.reply_callback("❌ Произошла ошибка при загрузке проекта.")

def manage_project_applications(context, project_id):
    """Управление заявками на проект"""
    chat_id = context.message['recipient']['chat_id']
    db_user_id = get_db_user_id(chat_id)
    
    if not db_user_id:
        context.reply_callback("❌ Вы не авторизованы.")
        return
    
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Проверяем, является ли пользователь создателем проекта
            cur.execute("SELECT creator_id FROM projects WHERE project_id = %s", (project_id,))
            project = cur.fetchone()
            
            if not project or project['creator_id'] != db_user_id:
                context.reply_callback("❌ У вас нет прав для управления этим проектом.")
                return
            
            # Получаем заявки на проект
            cur.execute("""
                SELECT pa.*, u.first_name, u.last_name, u.user_id
                FROM project_applications pa
                JOIN users u ON pa.user_id = u.user_id
                WHERE pa.project_id = %s AND pa.status = 'pending'
                ORDER BY pa.applied_at
            """, (project_id,))
            applications = cur.fetchall()
            
            if not applications:
                context.reply_callback("📭 На ваш проект пока нет заявок.")
                return
            
            message = f"📋 *Заявки на проект*\n\n"
            
            for i, app in enumerate(applications, 1):
                message += f"{i}. *{app['first_name']} {app['last_name']}*\n"
                message += f"   🎯 Роль: {app['desired_role']}\n"
                if app['message']:
                    message += f"   💬 Сообщение: {app['message']}\n"
                message += f"   📅 Подана: {app['applied_at'].strftime('%d.%m.%Y %H:%M')}\n\n"

            
            keyboard_rows = []
            
            for app in applications:
                keyboard_rows.append([
                    {"text": f"✅ Принять {app['first_name']}", "callback": f"accept_application_{app['application_id']}"},
                    {"text": f"❌ Отклонить {app['first_name']}", "callback": f"reject_application_{app['application_id']}"}
                ])
            
            keyboard_rows.append([{"text": "🔙 Назад к проекту", "callback": f"view_my_project_{project_id}"}])
            keyboard_rows.append([{"text": "🏠 Главное меню", "callback": "back_to_menu"}])
            
            keyboard = InlineKeyboard(*keyboard_rows)
            
            context.reply_callback(message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Ошибка при управлении заявками: {e}")
        context.reply_callback("❌ Произошла ошибка при загрузке заявок.")

def accept_application(context, application_id):
    """Принимает заявку на присоединение к проекту"""
    chat_id = context.message['recipient']['chat_id']
    db_user_id = get_db_user_id(chat_id)
    
    if not db_user_id:
        context.reply_callback("❌ Вы не авторизованы.")
        return
    
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Получаем информацию о заявке
            cur.execute("""
                SELECT pa.*, p.creator_id, p.title as project_title
                FROM project_applications pa
                JOIN projects p ON pa.project_id = p.project_id
                WHERE pa.application_id = %s
            """, (application_id,))
            application = cur.fetchone()
            
            if not application:
                context.reply_callback("❌ Заявка не найдена.")
                return
            
            # Проверяем, является ли пользователь создателем проекта
            if application['creator_id'] != db_user_id:
                context.reply_callback("❌ У вас нет прав для принятия этой заявки.")
                return
            
            # Обновляем статус заявки
            cur.execute("""
                UPDATE project_applications 
                SET status = 'approved' 
                WHERE application_id = %s
            """, (application_id,))
            
            # Добавляем пользователя в участники проекта
            cur.execute("""
                INSERT INTO project_members (project_id, user_id, role)
                VALUES (%s, %s, %s)
            """, (application['project_id'], application['user_id'], application['desired_role']))
            
            db.conn.commit()
            
            # Создаем уведомление для заявителя
            from handlers.notification_handler import create_notification
            create_notification(
                user_id=application['user_id'],
                notification_type='project_application',
                title='✅ Заявка на проект принята',
                message=f'Ваша заявка на проект "{application["project_title"]}" была принята! Теперь вы участник проекта.',
                related_id=application_id
            )
            
            message = f"✅ *Заявка принята!*\n\nПользователь добавлен в команду проекта."
            
            context.reply_callback(message, keyboard=get_student_keyboard())
            
    except Exception as e:
        logger.error(f"Ошибка при принятии заявки: {e}")
        db.conn.rollback()
        context.reply_callback("❌ Произошла ошибка при принятии заявки. Попробуйте позже.")

def reject_application(context, application_id):
    """Отклоняет заявку на присоединение к проекту"""
    chat_id = context.message['recipient']['chat_id']
    db_user_id = get_db_user_id(chat_id)
    
    if not db_user_id:
        context.reply_callback("❌ Вы не авторизованы.")
        return
    
    try:
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Получаем информацию о заявке
            cur.execute("""
                SELECT pa.*, p.creator_id, p.title as project_title
                FROM project_applications pa
                JOIN projects p ON pa.project_id = p.project_id
                WHERE pa.application_id = %s
            """, (application_id,))
            application = cur.fetchone()
            
            if not application:
                context.reply_callback("❌ Заявка не найдена.")
                return
            
            # Проверяем, является ли пользователь создателем проекта
            if application['creator_id'] != db_user_id:
                context.reply_callback("❌ У вас нет прав для отклонения этой заявки.")
                return
            
            # Обновляем статус заявки
            cur.execute("""
                UPDATE project_applications 
                SET status = 'rejected' 
                WHERE application_id = %s
            """, (application_id,))
            
            db.conn.commit()
            
            # Создаем уведомление для заявителя
            from handlers.notification_handler import create_notification
            create_notification(
                user_id=application['user_id'],
                notification_type='project_application',
                title='❌ Заявка на проект отклонена',
                message=f'Ваша заявка на проект "{application["project_title"]}" была отклонена.',
                related_id=application_id
            )
            
            message = f"❌ *Заявка отклонена.*"
            
            context.reply_callback(message, keyboard=get_student_keyboard())
            
    except Exception as e:
        logger.error(f"Ошибка при отклонении заявки: {e}")
        db.conn.rollback()
        context.reply_callback("❌ Произошла ошибка при отклонении заявки. Попробуйте позже.")
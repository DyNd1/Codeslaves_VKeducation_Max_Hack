from config import bot, logger, db
import handlers.main_handlers
import handlers.faculty_handlers
from handlers.faculty_handlers import show_faculties, show_faculty_programs, show_program_details
from handlers.open_days_handlers import show_open_days, registration_data, start_open_day_registration
from keyboards.menus import (get_main_non_auth_keyboard, get_main_auth_keyboard,
                             get_app_keyboard, get_student_keyboard,
                             get_teacher_keyboard,get_rector_keyboard)
from handlers.ege_handler import (user_selection_data, start_program_selection,
                                  handle_subject_selection, reset_subjects_selection, show_available_programs_result)
from handlers.authorization_handler import auth_sessions, start_authorization, handle_logout, authenticated_users
from handlers.rector_news_handler import handle_rector_documents
from handlers.business_trip_handler import (
    start_business_trip,
    cancel_business_trip,
    process_business_trip_message
)
from handlers.vacation_handler import (
    start_vacation,
    cancel_vacation,
    submit_vacation,
    process_vacation_message
)
from keyboards.menus import get_auth_keyboard
from handlers.schedule_handler import show_student_schedule, show_teacher_schedule
from handlers.notification_handler import check_and_show_notifications
from handlers.library_handlers import (
    start_book_search,
    handle_book_search_query,
    handle_digital_book_request,
    handle_book_reservation,
    handle_navigation
)
from handlers.digital_department_handler import (
    start_digital_department_registration,
    handle_department_selection,
    show_digital_department_status
)
from handlers.project_handler import (
    start_project_creation,
    process_project_creation,
    show_available_projects,
    show_project_details,
    join_project,
    show_my_projects,
    show_my_project_details,
    manage_project_applications,
    accept_application,
    reject_application
)
from handlers.competition_handler import handle_competition_menu,show_teacher_contract_info,show_vacancy_competitions
from handlers.rector_dashboard_handler import show_rector_dashboard, show_detailed_analytics
# Добавляем импорт обработчиков справок
from handlers.certificate_handler import (
    handle_study_certificate_request,
    select_certificate_delivery,
    confirm_digital_certificate,
    confirm_office_certificate,
    show_certificate_status,
    cancel_certificate
)


# Извлечение user_id (chat_id)
def get_safe_user_id(context):
    user_id = context.message['recipient']['chat_id']
    return user_id


@bot.on("message_callback")
def handle_callback(context):
    user_id = get_safe_user_id(context)

    button = context.payload
    #Обработка inline-кнопок
    if user_id in auth_sessions:
        del auth_sessions[user_id]
    if button == "authorization":
        start_authorization(context)
    elif button == "programs":
        show_faculties(context)
    elif button == "can_program":
        start_program_selection(context)
    elif button == "open_days":
        show_open_days(context)
    elif button == "back_to_menu":
        # Отменяем все процессы
        if user_id in registration_data:
            del registration_data[user_id]
        if user_id in user_selection_data:
            del user_selection_data[user_id]
        if user_id in authenticated_users:
            if authenticated_users[user_id]['role'] == 'applicant':
                context.reply_callback("Вернемся к основному меню", keyboard=get_app_keyboard())
            elif authenticated_users[user_id]['role'] == 'teacher':
                check_and_show_notifications(context)
                context.reply_callback("Вернемся к основному меню", keyboard=get_teacher_keyboard())
            elif authenticated_users[user_id]['role'] == 'student':
                context.reply_callback("Вернемся к основному меню", keyboard=get_student_keyboard())
            elif authenticated_users[user_id]['role'] == 'rector':
                check_and_show_notifications(context)
                context.reply_callback("Вернемся к основному меню", keyboard=get_rector_keyboard())
        else:
            context.reply_callback("Вернемся к основному меню", keyboard=get_main_non_auth_keyboard())

    elif button.startswith("faculty_"):
        faculty_number = button.split("_")[1]
        show_faculty_programs(context, faculty_number)
    elif button.startswith("program_"):
        program_id = button.split("_")[1]
        show_program_details(context, program_id)
    elif button.startswith("register_"):
        event_id = button.split("register_open_day_")[1]
        start_open_day_registration(context, event_id, user_id)
    elif button == "cancel_registration":
        if user_id in registration_data:
            del registration_data[user_id]
        context.reply_callback("❌ Регистрация отменена")
    # Обработчики для выбора предметов
    elif button.startswith("select_subject_"):
        subject_id = button.split("select_subject_")[1]
        handle_subject_selection(context, subject_id)
    elif button == "reset_subjects":
        reset_subjects_selection(context, user_id)
    elif button == "show_available_programs":
        show_available_programs_result(context, user_id)
    # Обработчики для выхода
    elif button == "logout":
        handle_logout(context)
    elif user_id in authenticated_users:
        logger.info(f"User {user_id} pressed button: {button}")
        logger.info(f"Authenticated users: {list(authenticated_users.keys())}")
        if button == "rector_documents":
            handle_rector_documents(context)
        elif button == "business_trip":
            start_business_trip(context)
        elif button == "cancel_business_trip":
            cancel_business_trip(context)
        elif button == "arrange_vacation":
            start_vacation(context)
        elif button == "cancel_vacation":
            cancel_vacation(context)
        elif button == "submit_vacation":
            submit_vacation(context)

        elif button == "teacher_classes":
            show_teacher_schedule(context)
        elif button == "student_schedule":
            show_student_schedule(context)

        elif button == "show_notifications":
            check_and_show_notifications(context)
        elif button == "find_book":
            start_book_search(context)
        elif button.startswith("digital_book_"):
            book_id = int(button.replace("digital_book_", ""))
            handle_digital_book_request(context, book_id)
        elif button.startswith("reserve_book_"):
            book_id = int(button.replace("reserve_book_", ""))
            handle_book_reservation(context, book_id)
        elif button.startswith("prev_book_") or button.startswith("next_book_"):
            book_index = int(button.split("_")[-1])
            handle_navigation(context, book_index)
        elif button == "digital_department":
            start_digital_department_registration(context)
        elif button == "digital_department_status":
            show_digital_department_status(context)
        elif button.startswith("select_department_"):
            department_id = button.split("select_department_")[1]
            handle_department_selection(context, department_id)
        elif button == "digital_department":
            start_digital_department_registration(context)
        elif button == "digital_department_status":
            show_digital_department_status(context)
        elif button.startswith("select_department_"):
            department_id = button.split("select_department_")[1]
            handle_department_selection(context, department_id)
        elif button == "create_project":
            start_project_creation(context)
        elif button == "Join_project":
            show_available_projects(context)
        elif button == "my_projects":
            show_my_projects(context)
        elif button.startswith("view_project_"):
            project_id = button.split("view_project_")[1]
            show_project_details(context, project_id)
        elif button.startswith("join_project_"):
            project_id = button.split("join_project_")[1]
            join_project(context, project_id)
        elif button.startswith("view_my_project_"):
            project_id = button.split("view_my_project_")[1]
            show_my_project_details(context, project_id)
        elif button.startswith("manage_project_"):
            project_id = button.split("manage_project_")[1]
            manage_project_applications(context, project_id)
        elif button.startswith("accept_application_"):
            application_id = button.split("accept_application_")[1]
            accept_application(context, application_id)
        elif button.startswith("reject_application_"):
            application_id = button.split("reject_application_")[1]
            reject_application(context, application_id)
        elif button == "rector_stats":
            show_rector_dashboard(context)
        elif button == "detailed_analytics":
            show_detailed_analytics(context)
        # Добавляем обработчики для справок об обучении
        elif button == "study_certificate":
            handle_study_certificate_request(context)
        elif button == "select_certificate_delivery":
            select_certificate_delivery(context)
        elif button == "confirm_digital_certificate":
            confirm_digital_certificate(context)
        elif button == "confirm_office_certificate":
            confirm_office_certificate(context)
        elif button == "cancel_certificate":
            cancel_certificate(context)
        elif button.startswith("certificate_status_"):
            request_id = button.split("certificate_status_")[1]
            show_certificate_status(context, request_id)
        elif button == "competition":
            handle_competition_menu(context)
        elif button == "teacher_contracts":
            show_teacher_contract_info(context)
        elif button == "vacancy_competitions":
            show_vacancy_competitions(context)
    else:
        keyboard = get_auth_keyboard()
        context.reply_callback("Вы не авторизированы", keyboard = keyboard)



if __name__ == "__main__":
    logger.info("Запуск бота...")
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
        bot.stop()
        db.close()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

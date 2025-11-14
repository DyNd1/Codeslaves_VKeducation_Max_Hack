from config import logger, db
from keyboards.menus import get_faculties_keyboard, get_programs_keyboard, \
    get_program_detail_keyboard
from applicant.available_programs import get_all_faculties, get_programs_by_faculty, get_program_by_id, \
    get_program_subjects, get_faculty_by_id


def show_faculties(context):
    res = get_all_faculties(db.conn)
    faculty_name =  res[1]
    keys = res[2]
    faculty_keyboard = get_faculties_keyboard(faculty_name,keys)

    context.reply_callback(
        "Отлично в этом вузе есть такие факультеты:\n" + res[0] +
        "Программы какого факультета ты хочешь посмотреть?",
        keyboard=faculty_keyboard
    )


def show_faculty_programs(context, faculty_number):
    try:
        programs = get_programs_by_faculty(db.conn, faculty_number)

        if not programs:
            context.reply_callback(f"На факультете {faculty_number} пока нет программ")
            return

        programs_keyboard = get_programs_keyboard(programs)
        faculty_info = get_faculty_by_id(db.conn, faculty_number)

        message = f"🏛 Факультет: {faculty_info['faculty_name']}\n\n"
        message += f"📖 {faculty_info['description']}\n\n"
        message += "📋 Доступные образовательные программы:\n\n"

        for i, program in enumerate(programs, 1):
            message += f"{i}. {program['program_name']}\n"

        message += "\n🎯 Нажми на программу, чтобы узнать подробности"

        context.reply_callback(message, keyboard=programs_keyboard)

    except Exception as e:
        logger.error(f"Ошибка при получении программ факультета: {e}")
        context.reply_callback("Произошла ошибка при загрузке программ")


def show_program_details(context, program_id):
    try:
        program = get_program_by_id(db.conn, program_id)

        if not program:
            context.reply_callback("Программа не найдена")
            return

        message = f"🎓 {program['program_name']}\n\n"
        message += f"📝 Описание:\n{program['description']}\n\n"
        message += "📊 Информация о поступлении:\n"
        message += f"• 🎯 Проходной балл прошлого года: {program['last_year_pass_score']}\n"
        message += f"• 💺 Бюджетных мест: {program['budget_places']}\n"
        message += f"• 🏛 Факультет: {program['faculty_name']}\n"

        subjects = get_program_subjects(db.conn, program_id)
        if subjects:
            message += "\n📚 Предметы ЕГЭ:\n"
            for subject in subjects:
                required_icon = "✅" if subject['is_required'] else "📌"
                message += f"• {required_icon} {subject['subject_name']}\n"

        detail_keyboard = get_program_detail_keyboard(program['faculty_id'])
        context.reply_callback(message, keyboard=detail_keyboard)

    except Exception as e:
        logger.error(f"Ошибка при получении деталей программы: {e}")
        context.reply_callback("Произошла ошибка при загрузке информации о программе")
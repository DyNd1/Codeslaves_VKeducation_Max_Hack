from maxgram.keyboards import InlineKeyboard


def get_main_non_auth_keyboard():
    return InlineKeyboard(
        [{"text": "Авторизация", "callback": "authorization"}],
        [{"text": "Ознакомиться с программами ВУЗА", "callback": "programs"}],
        [{"text": "Куда я пройду по баллам ЕГЭ", "callback": "can_program"}],
        [{"text": "День открытых дверей", "callback": "open_days"}]
    )
def get_main_auth_keyboard():
    return InlineKeyboard(
        [{"text": "Ознакомиться с программами ВУЗА", "callback": "programs"}],
        [{"text": "Куда я пройду по баллам ЕГЭ", "callback": "can_program"}],
        [{"text": "День открытых дверей", "callback": "open_days"}]
    )


def get_faculties_keyboard(faculty_names,keys):
    keyboard_rows = []
    idx = 0
    for i in faculty_names:
        keyboard_rows.append([
            {"text": f"Факультет {i}", "callback": f"faculty_{keys[idx]}"}
        ])
        idx += 1
    keyboard_rows.append([{"text": "Назад", "callback": "back_to_menu"}])
    return InlineKeyboard(*keyboard_rows)


def get_programs_keyboard(programs):
    keyboard_rows = []
    for program in programs:
        program_name = program['program_name']
        if len(program_name) > 30:
            program_name = program_name[:27] + "..."
        keyboard_rows.append([
            {"text": f"📚 {program_name}", "callback": f"program_{program['program_id']}"}
        ])

    keyboard_rows.append([
        {"text": "🔙 Назад к факультетам", "callback": "programs"},
        {"text": "🏠 Главное меню", "callback": "back_to_menu"}
    ])
    return InlineKeyboard(*keyboard_rows)


def get_program_detail_keyboard(faculty_id):
    return InlineKeyboard(
        [
            {"text": "📋 Вернуться к программам", "callback": f"faculty_{faculty_id}"},
            {"text": "🎓 Все факультеты", "callback": "programs"}
        ],
        [
            {"text": "🏠 Главное меню", "callback": "back_to_menu"}
        ]
    )


def get_open_days_registration_keyboard(event_id, event_index=None):
    """Создает клавиатуру для регистрации на конкретное событие"""
    if event_index:
        button_text = f"📝 Записаться на событие {event_index}"
    else:
        button_text = "📝 Записаться"

    return InlineKeyboard(
        [
            {"text": button_text, "callback": f"register_open_day_{event_id}"}
        ],
        [
            {"text": "🔙 Назад", "callback": "back_to_menu"}
        ]
    )

def get_app_keyboard():
    keyboard = InlineKeyboard(
        [{"text": "📚 Ознакомиться с программами", "callback": "programs"}],
        [{"text": "🎯 Подбор программ по баллам", "callback": "can_program"}],
        [{"text": "📅 Дни открытых дверей", "callback": "open_days"}],
        [{"text": "🚪 Выйти", "callback": "logout"}]
    )
    return keyboard

def get_student_keyboard():
    keyboard = InlineKeyboard(
        [{"text": "📖 Мое расписание", "callback": "student_schedule"}],
        [{"text": "🔔 Уведомления", "callback": "show_notifications"}],
        [{"text": "📊 Записаться на цифровую кафедру", "callback": "digital_department"}],  
        [{"text": "📋 Мои заявки на цифровую кафедру", "callback": "digital_department_status"}], 
        [{"text": "🚀 Создать проект", "callback": "create_project"}],
        [{"text": "👥 Присоединиться к проекту", "callback": "Join_project"}],
        [{"text": "📂 Мои проекты", "callback": "my_projects"}],
        [{"text": "🎓 Оформить справку об обучении", "callback": "study_certificate"}],
        [{"text": "📖 Найти книгу", "callback": "find_book"}],
        [{"text": "🚪 Выйти", "callback": "logout"}]
    )
    return keyboard

def get_teacher_keyboard():
    keyboard = InlineKeyboard(
        [{"text": "👨‍🏫 Мои занятия", "callback": "teacher_classes"}],
        [{"text": "🔔 Уведомления", "callback": "show_notifications"}],
        [{"text": "📝 Оформить командировку", "callback": "business_trip"}],
        [{"text": "🏠Оформить отпуск", "callback": "arrange_vacation"}],
        [{"text": "📊 Конкурс на замещение вакантных должностей", "callback": "competition"}],
        [{"text": "🚪 Выйти", "callback": "logout"}]
    )
    return keyboard

def get_rector_keyboard():
    keyboard = InlineKeyboard(
        [{"text": "📊 Дашборд университета", "callback": "rector_stats"}],
        [{"text": "📑 Последние новости", "callback": "rector_documents"}],
        [{"text": "🚪 Выйти", "callback": "logout"}]
    )

    return keyboard

def get_auth_keyboard():
    keyboard = InlineKeyboard(
        [{"text": "Авторизация", "callback": "authorization"}],
    )
    return keyboard
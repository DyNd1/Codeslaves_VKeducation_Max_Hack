
from applicant.available_ege_program import (get_safe_user_id, get_all_subjects,
                                             get_available_programs, is_program_suitable, get_program_subjects,
                                             calculate_total_score, get_subject_min_score)
from config import bot, logger, db
from maxgram.keyboards import InlineKeyboard

# Глобальные переменные для хранения состояния
user_selection_data = {}


def start_program_selection(context):
    """Начать процесс выбора предметов ЕГЭ"""
    user_id = get_safe_user_id(context)

    # Получаем все уникальные предметы ЕГЭ из базы
    subjects = get_all_subjects(db.conn)

    if not subjects:
        context.reply_callback("❌ Не удалось загрузить список предметов ЕГЭ")
        return

    # Сохраняем состояние пользователя
    user_selection_data[user_id] = {
        'step': 'selecting_subjects',
        'subjects': subjects,
        'selected_subjects': [],  # список выбранных предметов с баллами
        'current_step': 'subject_selection'
    }

    # Показываем клавиатуру с предметами
    show_subjects_keyboard(context, user_id)


def show_subjects_keyboard(context, user_id):
    """Показать клавиатуру с предметами для выбора"""
    user_data = user_selection_data[user_id]
    subjects = user_data['subjects']

    # Создаем кнопки для каждого предмета
    keyboard_rows = []
    for subject in subjects:
        subject_id = subject['subject_id']
        subject_name = subject['subject_name']

        # Проверяем, выбран ли уже этот предмет
        is_selected = any(s['subject_id'] == subject_id for s in user_data['selected_subjects'])
        emoji = "✅" if is_selected else "📚"

        keyboard_rows.append([
            {"text": f"{emoji} {subject_name}", "callback": f"select_subject_{subject_id}"}
        ])

    # Добавляем кнопки управления
    if user_data['selected_subjects']:
        keyboard_rows.append([
            {"text": "🚀 Посмотреть подходящие программы", "callback": "show_available_programs"}
        ])

    keyboard_rows.append([
        {"text": "🔄 Сбросить выбор", "callback": "reset_subjects"},
        {"text": "🏠 Главное меню", "callback": "back_to_menu"}
    ])

    keyboard = InlineKeyboard(*keyboard_rows)

    # Формируем сообщение
    message = "🎯 Выберите предметы ЕГЭ, которые вы сдавали:\n\n"

    if user_data['selected_subjects']:
        message += "📋 Выбранные предметы:\n"
        for selected in user_data['selected_subjects']:
            message += f"• {selected['subject_name']}: {selected['score']} баллов\n"
        message += "\n"

    message += "ℹ️ Нажмите на предмет, чтобы добавить/изменить баллы\n"
    message += "✅ Выберите все предметы, которые вы сдавали"

    # Проверяем тип контекста и используем соответствующий метод
    if hasattr(context, 'callback_query') and context.callback_query:
        context.reply_callback(message, keyboard=keyboard)
    else:
        context.reply(message, keyboard=keyboard)


def handle_subject_selection(context, subject_id):
    """Обработка выбора предмета"""
    user_id = get_safe_user_id(context)

    if user_id not in user_selection_data:
        return

    user_data = user_selection_data[user_id]

    # Находим предмет по ID
    subject = next((s for s in user_data['subjects'] if s['subject_id'] == int(subject_id)), None)

    if not subject:
        context.reply_callback("❌ Предмет не найден")
        return

    # Получаем минимальный балл для предмета
    min_score = get_subject_min_score(db.conn, subject['subject_id'])

    # Сохраняем выбранный предмет для ввода баллов
    user_data['current_subject'] = subject
    user_data['current_min_score'] = min_score
    user_data['current_step'] = 'score_input'

    # Запрашиваем балл
    message = f"📝 Введите ваш балл по предмету:\n🎯 {subject['subject_name']}\n\n"
    if min_score > 0:
        message += f"⚠️ Минимальный балл для этого предмета: {min_score}\n\n"
    message += "Введите число от 0 до 100:\n"
    message += "• 0 - если не сдавали этот предмет\n"
    message += "• /cancel - для отмены"

    context.reply_callback(message)




def process_score_input(context, user_id, text):
    """Обработка введенного балла"""
    if user_id not in user_selection_data:
        return False

    user_data = user_selection_data[user_id]

    try:
        score = int(text.strip())

        if score < 0 or score > 100:
            context.reply("❌ Балл должен быть в диапазоне от 0 до 100")
            return True

        # Проверяем минимальный балл
        min_score = user_data.get('current_min_score', 0)
        if score > 0 and score < min_score:
            context.reply(f"❌ Балл должен быть не менее {min_score} для этого предмета")
            return True

        # Сохраняем предмет с баллом
        current_subject = user_data['current_subject']

        # Удаляем старую запись если предмет уже был выбран
        user_data['selected_subjects'] = [
            s for s in user_data['selected_subjects']
            if s['subject_id'] != current_subject['subject_id']
        ]

        # Добавляем новую запись если балл > 0
        if score > 0:
            user_data['selected_subjects'].append({
                'subject_id': current_subject['subject_id'],
                'subject_name': current_subject['subject_name'],
                'score': score
            })

        # Возвращаемся к выбору предметов
        user_data['current_step'] = 'subject_selection'
        show_subjects_keyboard(context, user_id)
        return True

    except Exception as e:
        print(e)
        context.reply("❌ Пожалуйста, введите число от 0 до 100")
        return True


def reset_subjects_selection(context, user_id):
    """Сбросить выбранные предметы"""
    if user_id in user_selection_data:
        user_selection_data[user_id]['selected_subjects'] = []
        show_subjects_keyboard(context, user_id)


def show_available_programs_result(context, user_id):
    """Показать доступные программы по выбранным предметам"""
    if user_id not in user_selection_data:
        return

    user_data = user_selection_data[user_id]
    selected_subjects = user_data['selected_subjects']

    if not selected_subjects:
        context.reply_callback("❌ Вы не выбрали ни одного предмета!")
        return

    # Преобразуем в формат для проверки
    scores = {s['subject_id']: s['score'] for s in selected_subjects}
    subject_ids = [s['subject_id'] for s in selected_subjects]

    # Получаем все программы
    all_programs = get_available_programs(db.conn)
    available_programs = []

    for program in all_programs:
        program_id = program['program_id']

        # Получаем предметы для этой программы
        program_subjects = get_program_subjects(db.conn, program_id)

        # Проверяем, подходит ли программа
        if is_program_suitable(program_subjects, scores, subject_ids, db.conn):
            available_programs.append(program)

    # Формируем сообщение с результатами
    message = format_programs_message(available_programs, scores, db.conn)

    # Отправляем сообщение
    context.reply_callback(message)

    # Показываем клавиатуру для продолжения
    keyboard = InlineKeyboard(
        [{"text": "🔄 Попробовать с другими предметами", "callback": "can_program"}],
        [{"text": "🏠 Главное меню", "callback": "back_to_menu"}]
    )
    context.reply_callback("Что хотите сделать дальше?", keyboard=keyboard)

    # Очищаем данные пользователя
    if user_id in user_selection_data:
        del user_selection_data[user_id]


def format_programs_message(available_programs, scores, conn):
    """Форматировать сообщение с программами"""
    if available_programs:
        message = "🎓 Вам подходят следующие программы:\n\n"

        for i, program in enumerate(available_programs, 1):
            total_score = calculate_total_score(program['program_id'], scores, conn)
            program_subjects = get_program_subjects(conn, program['program_id'])

            message += f"{i}. {program['program_name']}\n"
            message += f"   🏛 {program['faculty_name']}\n"
            message += f"   📝 {program['program_description'][:80]}...\n"
            message += f"   💺 Бюджетных мест: {program['budget_places']}\n"
            message += f"   🎯 Прошлогодний проходной: {program['last_year_pass_score']}\n"
            message += f"   📊 Ваш балл: {total_score}\n"

            # Показываем предметы программы
            required_subs = [sub for sub in program_subjects if sub['is_required']]
            optional_subs = [sub for sub in program_subjects if not sub['is_required']]

            if required_subs:
                message += "   ✅ Обязательные: " + ", ".join([sub['subject_name'] for sub in required_subs]) + "\n"
            if optional_subs:
                message += "   📌 На выбор: " + ", ".join([sub['subject_name'] for sub in optional_subs]) + "\n"

            message += "\n"

    else:
        message = "❌ К сожалению, по вашим баллам нет подходящих программ.\n\n"
        message += "💡 Рекомендации:\n"
        message += "• Попробуйте выбрать другие предметы\n"
        message += "• Рассмотрите программы с меньшими проходными баллами\n"
        message += "• Улучшите результаты ЕГЭ по ключевым предметам"

    return message





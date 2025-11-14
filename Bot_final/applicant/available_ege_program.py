from config import logger
from applicant.available_programs import get_program_subjects,get_available_programs
from psycopg2.extras import RealDictCursor

def get_all_subjects(conn):
    """Получить все предметы ЕГЭ из базы"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT subject_id, subject_name FROM subjects ORDER BY subject_name")
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка получения предметов: {e}")
        # Делаем rollback при ошибке
        conn.rollback()
        return []


def is_program_suitable(program_subjects, user_scores, user_selected_subjects, conn):
    """Проверить, подходит ли программа по предметам с учетом минимальных баллов"""
    required_subjects = [sub for sub in program_subjects if sub['is_required']]
    optional_subjects = [sub for sub in program_subjects if not sub['is_required']]

    # Проверяем обязательные предметы
    for req_sub in required_subjects:
        subject_id = req_sub['subject_id']
        user_score = user_scores.get(subject_id, 0)

        # Получаем минимальный балл для предмета
        min_score = get_subject_min_score(conn, subject_id)

        # Проверяем, что предмет выбран и балл >= минимального
        if subject_id not in user_selected_subjects or user_score < min_score:
            return False

    # Проверяем, что есть хотя бы один предмет из дополнительных (если они есть)
    if optional_subjects:
        has_optional = False
        for sub in optional_subjects:
            subject_id = sub['subject_id']
            user_score = user_scores.get(subject_id, 0)
            min_score = get_subject_min_score(conn, subject_id)

            if subject_id in user_selected_subjects and user_score >= min_score:
                has_optional = True
                break

        if not has_optional:
            return False

    return True


def calculate_total_score(program_id, user_scores, conn):
    """Рассчитать общий балл для программы"""
    program_subjects = get_program_subjects(conn, program_id)
    total = 0

    for subject in program_subjects:
        subject_id = subject['subject_id']
        if subject_id in user_scores and user_scores[subject_id] > 0:
            total += user_scores[subject_id]

    return total


def get_safe_user_id(context):
    """Безопасное получение user_id"""
    try:
        return context.message['recipient']['chat_id']
    except:
        return "unknown"

def get_subject_min_score(conn, subject_id):
    """Получить минимальный балл для предмета"""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT min_score FROM subjects WHERE subject_id = %s", (subject_id,))
            result = cur.fetchone()
            return result[0] if result and result[0] is not None else 0
    except Exception as e:
        logger.error(f"Ошибка получения минимального балла: {e}")
        return 0

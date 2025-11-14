from maxgram import Bot
from maxgram.keyboards import InlineKeyboard
from psycopg2.extras import RealDictCursor

def get_available_programs(conn):
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    f.faculty_id,
                    f.faculty_name,
                    f.description as faculty_description,
                    p.program_id,
                    p.program_name,
                    p.description as program_description,
                    p.budget_places,
                    p.last_year_pass_score
                FROM faculties f
                JOIN educational_programs p ON f.faculty_id = p.faculty_id
                ORDER BY f.faculty_name, p.program_name
            """)
            return cur.fetchall()
    except Exception as e:
        print(f"Ошибка получения программ: {e}")
        return []


def get_all_faculties(conn):
    """Получить все факультеты"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM faculties ORDER BY faculty_name")
            result = ""
            names=[]
            keys=[]
            idx=1
            for faculty_program in cur.fetchall():
                faculty_name = faculty_program['faculty_name']
                description = faculty_program['description']
                result+=str(idx)+". "+faculty_name+". "+description+"\n"
                idx+=1
                keys.append(faculty_program['faculty_id'])
                names.append(faculty_name)
            return result,names,keys
    except Exception as e:
        print(f"Ошибка получения факультетов: {e}")
        return []


def get_faculty_by_id(conn, faculty_id):
    """Получить информацию о факультете по ID"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM faculties WHERE faculty_id = %s", (faculty_id,))
            return cur.fetchone()
    except Exception as e:
        print(f"Ошибка получения факультета: {e}")
        return None

def get_programs_by_faculty(conn, faculty_id):
    """Получить программы конкретного факультета"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM educational_programs 
                WHERE faculty_id = %s 
                ORDER BY program_name
            """, (faculty_id,))
            return cur.fetchall()
    except Exception as e:
        print(f"Ошибка получения программ факультета: {e}")
        return []

def get_program_by_id(conn, program_id):
    """Получить информацию о программе по ID"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    p.*,
                    f.faculty_name
                FROM educational_programs p
                JOIN faculties f ON p.faculty_id = f.faculty_id
                WHERE p.program_id = %s
            """, (program_id,))
            return cur.fetchone()
    except Exception as e:
        print(f"Ошибка получения программы: {e}")
        return None

def get_program_subjects(conn, program_id):
    """Получить предметы ЕГЭ для программы"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    s.subject_id,
                    s.subject_name,
                    ps.is_required
                FROM program_subjects ps
                JOIN subjects s ON ps.subject_id = s.subject_id
                WHERE ps.program_id = %s
                ORDER BY ps.is_required DESC, s.subject_name
            """, (program_id,))
            return cur.fetchall()
    except Exception as e:
        print(f"Ошибка получения предметов программы: {e}")
        return []

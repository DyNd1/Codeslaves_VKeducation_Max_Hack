-- Создание базы данных (если не существует)
SELECT 'CREATE DATABASE education_system'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'education_system')\gexec
-- Подключение к созданной базе данных
\c education_system;

-- Создание ENUM типа для ролей
CREATE TYPE user_role AS ENUM ('applicant', 'student', 'teacher', 'staff', 'dean', 'rector');

-- Факультеты
DROP TABLE IF EXISTS faculties CASCADE;
CREATE TABLE faculties (
    faculty_id SERIAL PRIMARY KEY,
    faculty_name VARCHAR(200) NOT NULL,
    description TEXT
);

DROP TABLE IF EXISTS student_groups CASCADE;
CREATE TABLE IF NOT EXISTS student_groups (
    group_id SERIAL PRIMARY KEY,
    group_name VARCHAR(50) NOT NULL UNIQUE,
    faculty_id INTEGER REFERENCES faculties(faculty_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- 1. Таблица пользователей
DROP TABLE IF EXISTS users CASCADE;
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    login VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(50) NOT NULL,
    max_id VARCHAR(50) NOT NULL UNIQUE,
    role user_role NOT NULL,
    group_id INTEGER REFERENCES student_groups(group_id),
    first_name VARCHAR(100) NOT NULL,
    surname VARCHAR(100),
    last_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


DROP TABLE IF EXISTS educational_programs CASCADE;
-- 3. Образовательные программы
CREATE TABLE educational_programs (
    program_id SERIAL PRIMARY KEY,
    faculty_id INTEGER NOT NULL REFERENCES faculties(faculty_id),
    program_name VARCHAR(200) NOT NULL,
    description TEXT,
    budget_places INTEGER NOT NULL,
    last_year_pass_score INTEGER,
    price INTEGER NOT NULL
);

DROP TABLE IF EXISTS subjects CASCADE;
-- 4. Предметы ЕГЭ
CREATE TABLE subjects (
    subject_id SERIAL PRIMARY KEY,
    subject_name VARCHAR(100) NOT NULL UNIQUE,
    min_score INTEGER NOT NULL
);

DROP TABLE IF EXISTS program_subjects CASCADE;
-- 5. Связь программ и предметов
CREATE TABLE program_subjects (
    program_id INTEGER NOT NULL REFERENCES educational_programs(program_id),
    subject_id INTEGER NOT NULL REFERENCES subjects(subject_id),
    is_required BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (program_id, subject_id)
);

DROP TABLE IF EXISTS applicant_profiles CASCADE;
-- 6. Профили абитуриентов
CREATE TABLE applicant_profiles (
    profile_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES users(user_id),
    total_score INTEGER
);

DROP TABLE IF EXISTS applicant_scores CASCADE;
-- 7. Баллы абитуриентов по предметам
CREATE TABLE applicant_scores (
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    subject_id INTEGER NOT NULL REFERENCES subjects(subject_id),
    score INTEGER NOT NULL CHECK (score >= 0 AND score <= 100),
    PRIMARY KEY (user_id, subject_id)
);

DROP TABLE IF EXISTS open_days CASCADE;
-- 8. Дни открытых дверей
CREATE TABLE open_days (
    event_id SERIAL PRIMARY KEY,
    faculty_id INTEGER REFERENCES faculties(faculty_id),
    event_date TIMESTAMP NOT NULL,
    description TEXT,
    max_participants INTEGER
);

DROP TABLE IF EXISTS open_day_registrations CASCADE;
-- 9. Регистрации на дни открытых дверей
CREATE TABLE open_day_registrations (
    registration_id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES open_days(event_id),
    max_id BIGINT NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, max_id)
);

-- Создание таблиц для системы библиотеки

-- Таблица книг
DROP TABLE IF EXISTS books CASCADE;
CREATE TABLE IF NOT EXISTS books (
    book_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    isbn VARCHAR(20),
    description TEXT,
    total_copies INTEGER DEFAULT 1,
    available_copies INTEGER DEFAULT 1,
    is_digital BOOLEAN DEFAULT FALSE,
    is_paper BOOLEAN DEFAULT FALSE,
    digital_link TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица бронирований книг
DROP TABLE IF EXISTS book_reservations CASCADE;
CREATE TABLE IF NOT EXISTS book_reservations (
    reservation_id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(book_id),
    user_id VARCHAR(100) NOT NULL,
    reservation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiry_date TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active', -- active, completed, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS study_certificate_requests CASCADE;
-- Таблица заявок на справки об обучении
CREATE TABLE IF NOT EXISTS study_certificate_requests (
    request_id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed
    delivery_type VARCHAR(20) DEFAULT 'digital' CHECK (delivery_type IN ('digital', 'office')),
    office_location TEXT,
    download_link TEXT,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Таблица для уведомлений
DROP TABLE IF EXISTS notifications CASCADE;
CREATE TABLE IF NOT EXISTS notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    type VARCHAR(50) NOT NULL, -- 'schedule_change', 'vacation_status', 'business_trip_status'
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    related_id INTEGER, -- ID связанной сущности
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


DROP TABLE IF EXISTS digital_departments CASCADE;
CREATE TABLE digital_departments (
    department_id SERIAL PRIMARY KEY,
    department_name VARCHAR(200) NOT NULL,
    description TEXT,
    available_places INTEGER NOT NULL,
    application_deadline DATE NOT NULL,
    min_gpa DECIMAL(3,2) NOT NULL CHECK (min_gpa >= 0 AND min_gpa <= 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица заявок на цифровую кафедру
DROP TABLE IF EXISTS digital_department_applications CASCADE;
CREATE TABLE digital_department_applications (
    application_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    department_id INTEGER NOT NULL REFERENCES digital_departments(department_id),
    application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    decision_date TIMESTAMP,
    UNIQUE(user_id, department_id)
);

-- Таблица успеваемости студентов
DROP TABLE IF EXISTS student_grades CASCADE;
CREATE TABLE student_grades (
    grade_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    subject_name VARCHAR(200) NOT NULL,
    grade DECIMAL(3,1) CHECK (grade >= 0 AND grade <= 5),
    semester INTEGER NOT NULL,
    academic_year VARCHAR(10) NOT NULL
);


-- Таблица контрактов преподавателей
DROP TABLE IF EXISTS teacher_contracts CASCADE;
CREATE TABLE IF NOT EXISTS teacher_contracts (
    contract_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    contract_number VARCHAR(100) NOT NULL,
    position VARCHAR(200) NOT NULL, -- Должность
    department VARCHAR(200) NOT NULL, -- Кафедра
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    salary DECIMAL(10,2) NOT NULL,
    contract_type VARCHAR(50) DEFAULT 'fixed_term' CHECK (contract_type IN ('fixed_term', 'permanent', 'temporary')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'terminated')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица конкурсов на замещение вакантных должностей
DROP TABLE IF EXISTS vacancy_competitions CASCADE;
CREATE TABLE IF NOT EXISTS vacancy_competitions (
    competition_id SERIAL PRIMARY KEY,
    position VARCHAR(200) NOT NULL,
    department VARCHAR(200) NOT NULL,
    vacancy_count INTEGER DEFAULT 1,
    salary_range VARCHAR(100),
    requirements TEXT,
    responsibilities TEXT,
    application_start_date DATE NOT NULL,
    application_end_date DATE NOT NULL,
    competition_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


DROP TABLE IF EXISTS staff_responsibilities CASCADE;
-- Создаем таблицу для рабочих обязанностей staff (если еще не создана)
CREATE TABLE IF NOT EXISTS staff_responsibilities (
    responsibility_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    responsibility_area VARCHAR(100) NOT NULL,
    description TEXT,
    assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


DROP TABLE IF EXISTS business_trips CASCADE;
CREATE TABLE IF NOT EXISTS business_trips (
    trip_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    purpose TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected
    dean_id BIGINT REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Общая таблица расписания
DROP TABLE IF EXISTS schedule CASCADE;
CREATE TABLE IF NOT EXISTS schedule (
    schedule_id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES student_groups(group_id),
    teacher_id BIGINT REFERENCES users(user_id),
    subject_name VARCHAR(200) NOT NULL,
    week_type VARCHAR(10) NOT NULL CHECK (week_type IN ('even', 'odd')),
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    classroom VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для хранения новостей
DROP TABLE IF EXISTS news CASCADE;
CREATE TABLE IF NOT EXISTS news (
    news_id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    link TEXT NOT NULL UNIQUE,
    source VARCHAR(200),
    date_text VARCHAR(50),
    sentiment VARCHAR(20),
    sentiment_score DECIMAL(5,3),
    parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Таблица для заявок на отпуск
DROP TABLE IF EXISTS vacations CASCADE;
CREATE TABLE IF NOT EXISTS vacations (
    vacation_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days_count INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected
    rector_id BIGINT REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для улучшения производительности
CREATE INDEX idx_users_max_id ON users(max_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_educational_programs_faculty_id ON educational_programs(faculty_id);
CREATE INDEX idx_program_subjects_program_id ON program_subjects(program_id);
CREATE INDEX idx_program_subjects_subject_id ON program_subjects(subject_id);
CREATE INDEX idx_applicant_scores_user_id ON applicant_scores(user_id);
CREATE INDEX idx_applicant_scores_subject_id ON applicant_scores(subject_id);
CREATE INDEX idx_open_days_faculty_id ON open_days(faculty_id);
CREATE INDEX idx_open_day_registrations_event_id ON open_day_registrations(event_id);
CREATE INDEX idx_open_day_registrations_user_id ON open_day_registrations(max_id);
CREATE INDEX idx_educational_programs_price ON educational_programs(price);




-- Индекс для поиска по дате и тональности
CREATE INDEX IF NOT EXISTS idx_news_date_sentiment ON news(date_text, sentiment);
CREATE INDEX IF NOT EXISTS idx_news_sentiment_score ON news(sentiment_score);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_business_trips_user_id ON business_trips(user_id);
CREATE INDEX IF NOT EXISTS idx_business_trips_status ON business_trips(status);
CREATE INDEX IF NOT EXISTS idx_business_trips_dean_id ON business_trips(dean_id);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_vacations_user_id ON vacations(user_id);
CREATE INDEX IF NOT EXISTS idx_vacations_status ON vacations(status);
CREATE INDEX IF NOT EXISTS idx_vacations_rector_id ON vacations(rector_id);

-- Таблица расписания преподавателей
-- Таблица учебных групп

-- Добавляем поле group_id к пользователям (студентам)

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_schedule_group_id ON schedule(group_id);
CREATE INDEX IF NOT EXISTS idx_schedule_teacher_id ON schedule(teacher_id);
CREATE INDEX IF NOT EXISTS idx_schedule_week_type ON schedule(week_type);



-- Индексы для уведомлений
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);



-- Обновляем триггерную функцию для уведомлений об изменении расписания
CREATE OR REPLACE FUNCTION notify_schedule_change()
RETURNS TRIGGER AS $$
DECLARE
    user_ids BIGINT[];
    student_user_id BIGINT;
    group_name_val TEXT;  -- Изменяем имя переменной
    teacher_name_val TEXT; -- Изменяем имя переменной
    faculty_name_val TEXT;
BEGIN
    -- Если изменено расписание группы, уведомляем всех студентов группы
    IF NEW.group_id IS NOT NULL THEN
        -- Получаем название группы (используем псевдоним для избежания конфликта)
        SELECT sg.group_name INTO group_name_val
        FROM student_groups sg
        WHERE sg.group_id = NEW.group_id;

        -- Получаем название факультета для более информативного сообщения
        SELECT f.faculty_name INTO faculty_name_val
        FROM student_groups sg
        JOIN faculties f ON sg.faculty_id = f.faculty_id
        WHERE sg.group_id = NEW.group_id;

        -- Собираем всех студентов группы
        SELECT ARRAY(SELECT user_id FROM users WHERE group_id = NEW.group_id) INTO user_ids;

        -- Вставляем уведомления для каждого студента
        IF array_length(user_ids, 1) > 0 THEN
            FOREACH student_user_id IN ARRAY user_ids
            LOOP
                INSERT INTO notifications (user_id, type, title, message, related_id)
                VALUES (
                    student_user_id,
                    'schedule_change',
                    '📅 Изменение в расписании',
                    'В расписание вашей группы ' || group_name_val || ' (' || faculty_name_val || ') внесены изменения. Проверьте актуальное расписание.',
                    NEW.schedule_id
                );
            END LOOP;
        END IF;
    END IF;

    -- Если изменено расписание преподавателя, уведомляем преподавателя
    IF NEW.teacher_id IS NOT NULL THEN
        -- Получаем ФИО преподавателя
        SELECT
            u.last_name || ' ' || u.first_name ||
            CASE WHEN u.surname IS NOT NULL THEN ' ' || u.surname ELSE '' END
        INTO teacher_name_val
        FROM users u
        WHERE u.user_id = NEW.teacher_id;

        -- Получаем информацию о группе для преподавателя
        IF NEW.group_id IS NOT NULL THEN
            SELECT sg.group_name INTO group_name_val
            FROM student_groups sg
            WHERE sg.group_id = NEW.group_id;

            INSERT INTO notifications (user_id, type, title, message, related_id)
            VALUES (
                NEW.teacher_id,
                'schedule_change',
                '📅 Изменение в вашем расписании',
                'В ваше расписание для группы ' || group_name_val || ' внесены изменения.',
                NEW.schedule_id
            );
        ELSE
            INSERT INTO notifications (user_id, type, title, message, related_id)
            VALUES (
                NEW.teacher_id,
                'schedule_change',
                '📅 Изменение в вашем расписании',
                'В ваше расписание внесены изменения. Проверьте актуальное расписание.',
                NEW.schedule_id
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Удаляем старый триггер и создаем новый
DROP TRIGGER IF EXISTS schedule_change_trigger ON schedule;
CREATE TRIGGER schedule_change_trigger
    AFTER INSERT OR UPDATE ON schedule
    FOR EACH ROW EXECUTE FUNCTION notify_schedule_change();


-- Триггерная функция для уведомлений об изменении статуса отпуска
CREATE OR REPLACE FUNCTION notify_vacation_status_change()
RETURNS TRIGGER AS $$
DECLARE
    status_text TEXT;
BEGIN
    -- Если статус изменился
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        -- Определяем текст статуса
        status_text := CASE
            WHEN NEW.status = 'approved' THEN '✅ Одобрен'
            WHEN NEW.status = 'rejected' THEN '❌ Отклонен'
            ELSE NEW.status
        END;

        -- Создаем уведомление
        INSERT INTO notifications (user_id, type, title, message, related_id)
        VALUES (
            NEW.user_id,
            'vacation_status',
            '🏖️ Статус отпуска изменен',
            'Статус вашего заявления на отпуск изменен на: ' || status_text,
            NEW.vacation_id
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для отпусков
DROP TRIGGER IF EXISTS vacation_status_trigger ON vacations;
CREATE TRIGGER vacation_status_trigger
    AFTER UPDATE ON vacations
    FOR EACH ROW EXECUTE FUNCTION notify_vacation_status_change();

-- Триггерная функция для уведомлений об изменении статуса командировки
CREATE OR REPLACE FUNCTION notify_business_trip_status_change()
RETURNS TRIGGER AS $$
DECLARE
    status_text TEXT;
BEGIN
    -- Если статус изменился
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        -- Определяем текст статуса
        status_text := CASE
            WHEN NEW.status = 'approved' THEN '✅ Одобрена'
            WHEN NEW.status = 'rejected' THEN '❌ Отклонена'
            ELSE NEW.status
        END;

        -- Создаем уведомление
        INSERT INTO notifications (user_id, type, title, message, related_id)
        VALUES (
            NEW.user_id,
            'business_trip_status',
            '🛫 Статус командировки изменен',
            'Статус вашей заявки на командировку изменен на: ' || status_text,
            NEW.trip_id
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для командировок
DROP TRIGGER IF EXISTS business_trip_status_trigger ON business_trips;
CREATE TRIGGER business_trip_status_trigger
    AFTER UPDATE ON business_trips
    FOR EACH ROW EXECUTE FUNCTION notify_business_trip_status_change();




-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_digital_departments_deadline ON digital_departments(application_deadline);
CREATE INDEX IF NOT EXISTS idx_digital_applications_user_id ON digital_department_applications(user_id);
CREATE INDEX IF NOT EXISTS idx_digital_applications_status ON digital_department_applications(status);
CREATE INDEX IF NOT EXISTS idx_student_grades_user_id ON student_grades(user_id);


-- Триггерная функция для уведомлений об изменении статуса заявки на цифровую кафедру
CREATE OR REPLACE FUNCTION notify_digital_department_status_change()
RETURNS TRIGGER AS $$
DECLARE
    dept_name TEXT;
    status_text TEXT;
    emoji TEXT;
    user_chat_id BIGINT;
BEGIN
    -- Если статус изменился
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        -- Получаем название направления
        SELECT department_name INTO dept_name
        FROM digital_departments
        WHERE department_id = NEW.department_id;

        -- Определяем текст и эмодзи для статуса
        status_text := CASE
            WHEN NEW.status = 'approved' THEN 'одобрена'
            WHEN NEW.status = 'rejected' THEN 'отклонена'
            ELSE NEW.status
        END;

        emoji := CASE
            WHEN NEW.status = 'approved' THEN '✅'
            WHEN NEW.status = 'rejected' THEN '❌'
            ELSE '📝'
        END;

        -- Получаем chat_id пользователя из таблицы users
        SELECT u.user_id INTO user_chat_id
        FROM users u
        WHERE u.user_id = NEW.user_id;

        -- Создаем уведомление
        INSERT INTO notifications (user_id, type, title, message, related_id)
        VALUES (
            user_chat_id,
            'digital_department_status',
            emoji || ' Статус заявки на цифровую кафедру',
            'Ваша заявка на направление "' || dept_name || '" ' || status_text || '.',
            NEW.application_id
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для заявок на цифровую кафедру
DROP TRIGGER IF EXISTS digital_department_status_trigger ON digital_department_applications;
CREATE TRIGGER digital_department_status_trigger
    AFTER UPDATE ON digital_department_applications
    FOR EACH ROW EXECUTE FUNCTION notify_digital_department_status_change();

-- Триггерная функция для уведомлений о новой заявке на цифровую кафедру
CREATE OR REPLACE FUNCTION notify_digital_department_application_created()
RETURNS TRIGGER AS $$
DECLARE
    dept_name TEXT;
    user_chat_id BIGINT;
BEGIN
    -- Получаем название направления
    SELECT department_name INTO dept_name
    FROM digital_departments
    WHERE department_id = NEW.department_id;

    -- Получаем chat_id пользователя из таблицы users
    SELECT u.user_id INTO user_chat_id
    FROM users u
    WHERE u.user_id = NEW.user_id;

    -- Создаем уведомление
    INSERT INTO notifications (user_id, type, title, message, related_id)
    VALUES (
        user_chat_id,
        'digital_department_application',
        '📝 Заявка на цифровую кафедру подана',
        'Ваша заявка на направление "' || dept_name || '" принята на рассмотрение.\n\nРешение о зачислении будет опубликовано в этом чате.',
        NEW.application_id
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для новых заявок на цифровую кафедру
DROP TRIGGER IF EXISTS digital_department_application_trigger ON digital_department_applications;
CREATE TRIGGER digital_department_application_trigger
    AFTER INSERT ON digital_department_applications
    FOR EACH ROW EXECUTE FUNCTION notify_digital_department_application_created();

-- Таблица проектов
DROP TABLE IF EXISTS projects CASCADE;
CREATE TABLE projects (
    project_id SERIAL PRIMARY KEY,
    creator_id BIGINT NOT NULL REFERENCES users(user_id),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    required_roles TEXT NOT NULL, -- JSON или текстовое поле с ролями
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица участников проектов
DROP TABLE IF EXISTS project_members CASCADE;
CREATE TABLE project_members (
    member_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(project_id),
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    role VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'left', 'removed')),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);

-- Таблица заявок на присоединение к проектам
DROP TABLE IF EXISTS project_applications CASCADE;
CREATE TABLE project_applications (
    application_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(project_id),
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    desired_role VARCHAR(100) NOT NULL,
    message TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_projects_creator_id ON projects(creator_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_project_members_project_id ON project_members(project_id);
CREATE INDEX IF NOT EXISTS idx_project_members_user_id ON project_members(user_id);
CREATE INDEX IF NOT EXISTS idx_project_applications_project_id ON project_applications(project_id);
CREATE INDEX IF NOT EXISTS idx_project_applications_user_id ON project_applications(user_id);
CREATE INDEX IF NOT EXISTS idx_project_applications_status ON project_applications(status);

-- Триггеры для уведомлений о проектах

-- Уведомление о новой заявке на проект
CREATE OR REPLACE FUNCTION notify_project_application_created()
RETURNS TRIGGER AS $$
DECLARE
    project_title TEXT;
    applicant_name TEXT;
BEGIN
    -- Получаем название проекта и имя заявителя
    SELECT p.title, u.first_name || ' ' || u.last_name
    INTO project_title, applicant_name
    FROM projects p
    JOIN users u ON u.user_id = NEW.user_id
    WHERE p.project_id = NEW.project_id;

    -- Создаем уведомление для создателя проекта
    INSERT INTO notifications (user_id, type, title, message, related_id)
    VALUES (
        (SELECT creator_id FROM projects WHERE project_id = NEW.project_id),
        'project_application',
        '📋 Новая заявка на проект',
        'Пользователь ' || applicant_name || ' подал заявку на присоединение к вашему проекту "' || project_title || '" на роль: ' || NEW.desired_role,
        NEW.application_id
    );

    RETURN NEW;
END;

$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS project_application_trigger ON project_applications;
CREATE TRIGGER project_application_trigger
    AFTER INSERT ON project_applications
    FOR EACH ROW EXECUTE FUNCTION notify_project_application_created();

-- Уведомление о изменении статуса заявки
CREATE OR REPLACE FUNCTION notify_project_application_status_change()
RETURNS TRIGGER AS $$
DECLARE
    project_title TEXT;
    status_text TEXT;
    emoji TEXT;
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        -- Получаем название проекта
        SELECT title INTO project_title
        FROM projects
        WHERE project_id = NEW.project_id;

        -- Определяем текст статуса
        status_text := CASE
            WHEN NEW.status = 'approved' THEN 'одобрена'
            WHEN NEW.status = 'rejected' THEN 'отклонена'
            ELSE NEW.status
        END;

        emoji := CASE
            WHEN NEW.status = 'approved' THEN '✅'
            WHEN NEW.status = 'rejected' THEN '❌'
            ELSE '📝'
        END;

        -- Создаем уведомление для заявителя
        INSERT INTO notifications (user_id, type, title, message, related_id)
        VALUES (
            NEW.user_id,
            'project_application_status',
            emoji || ' Статус заявки на проект',
            'Ваша заявка на проект "' || project_title || '" ' || status_text || '.',
            NEW.application_id
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS project_application_status_trigger ON project_applications;
CREATE TRIGGER project_application_status_trigger
    AFTER UPDATE ON project_applications
    FOR EACH ROW EXECUTE FUNCTION notify_project_application_status_change();

    -- Добавить в schema.sql после существующих таблиц

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_teacher_contracts_user_id ON teacher_contracts(user_id);
CREATE INDEX IF NOT EXISTS idx_teacher_contracts_end_date ON teacher_contracts(end_date);
CREATE INDEX IF NOT EXISTS idx_teacher_contracts_status ON teacher_contracts(status);
CREATE INDEX IF NOT EXISTS idx_vacancy_competitions_dates ON vacancy_competitions(application_start_date, application_end_date);
CREATE INDEX IF NOT EXISTS idx_vacancy_competitions_status ON vacancy_competitions(status);

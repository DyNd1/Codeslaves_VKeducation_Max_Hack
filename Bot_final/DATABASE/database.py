import psycopg2
import os
import time
import sys


class EducationDB:
    def __init__(self, max_retries=10, retry_delay=5):  # Увеличиваем таймауты для Docker
        self.conn = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Получаем параметры подключения из переменных окружения
        self.db_config = {
            "host": os.getenv("DATABASE_HOST", "localhost"),
            "database": os.getenv("DATABASE_NAME", "education_system"),
            "user": os.getenv("DATABASE_USER", "postgres"),
            "password": os.getenv("DATABASE_PASSWORD", "12345"),
            "port": os.getenv("DATABASE_PORT", "5432")
        }

        self.connect_with_retry()
        self.create_tables()

    def connect(self):
        """Подключение к базе данных"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.conn.autocommit = False
            print(f"Успешное подключение к базе данных: {self.db_config['host']}:{self.db_config['port']}")
            return True
        except psycopg2.OperationalError as e:
            print(f"Ошибка подключения к {self.db_config['host']}:{self.db_config['port']}: {e}")
            return False
    def ensure_database_exists(self):
        """Создание базы данных, если она не существует"""
        try:
            # Подключаемся к системной базе данных для создания целевой БД
            temp_conn = psycopg2.connect(
                host="localhost",
                database="postgres",  # Системная БД
                user="postgres",
                password="12345",
                port="5432"
            )
            temp_conn.autocommit = True  # Необходимо для создания БД

            with temp_conn.cursor() as cur:
                # Проверяем существование базы данных
                cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'education_system'")
                exists = cur.fetchone()

                if not exists:
                    print("Создание базы данных 'education_system'...")
                    cur.execute("CREATE DATABASE education_system")
                    print("База данных успешно создана")
                else:
                    print("База данных 'education_system' уже существует")

            temp_conn.close()

        except Exception as e:
            print(f"Ошибка при создании базы данных: {e}")
            sys.exit(1)

    def connect_with_retry(self):
        """Попытка подключения с повторными попытками"""
        print("Проверка существования базы данных...")
        self.ensure_database_exists()

        for attempt in range(self.max_retries):
            print(f"Попытка подключения {attempt + 1}/{self.max_retries}...")

            if self.connect():
                return True

            if attempt < self.max_retries - 1:
                print(f"Повторная попытка через {self.retry_delay} секунд...")
                time.sleep(self.retry_delay)

        print("Не удалось подключиться к базе данных после всех попыток")
        sys.exit(1)

    def get_schema_path(self, filename):
        """Получение полного пути к файлам схемы"""
        # Определяем базовую директорию
        base_dir = os.path.dirname(os.path.abspath(__file__))
        schema_dir = os.path.join(base_dir, '.')

        # Создаем директорию, если она не существует
        if not os.path.exists(schema_dir):
            os.makedirs(schema_dir)
            print(f"Создана директория: {schema_dir}")

        return os.path.join(schema_dir, filename)

    def execute_sql_file(self, filename, required=True):
        """Выполнение SQL файла"""
        filepath = self.get_schema_path(filename)

        if not os.path.exists(filepath):
            if required:
                print(f"Файл {filename} не найден по пути: {filepath}")
                return False
            else:
                print(f"Файл {filename} не найден, пропускаем...")
                return True

        try:
            with self.conn.cursor() as cur:
                with open(filepath, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                    if sql_content.strip():
                        cur.execute(sql_content)
                        print(f"Файл {filename} успешно выполнен")
                    else:
                        print(f"Файл {filename} пуст")
            return True
        except Exception as e:
            print(f"Ошибка выполнения файла {filename}: {e}")
            return False

    def create_tables(self):
        """Создание таблиц (если не существуют)"""
        try:
            # Список файлов для выполнения в правильном порядке
            sql_files = [
                'schema.sql',  # Создание структуры
                'insert_users.sql',  # Начальные данные пользователей
                'insert_grades.sql',  # Начальные данные оценок
                'insert_data.sql'  # Другие начальные данные
            ]

            success = True
            for sql_file in sql_files:
                if not self.execute_sql_file(sql_file, required=(sql_file == 'schema.sql')):
                    success = False
                    if sql_file == 'schema.sql':  # schema.sql обязателен
                        break

            if success:
                self.conn.commit()
                print("Все таблицы успешно созданы и заполнены")
            else:
                self.conn.rollback()
                print("Произошли ошибки при создании таблиц")

        except Exception as e:
            print(f"Общая ошибка создания таблиц: {e}")
            self.conn.rollback()


    def close(self):
        """Закрытие соединения"""
        if self.conn:
            self.conn.close()
            print("Соединение с базой данных закрыто")

    def reconnect(self):
        """Переподключение к базе данных"""
        print("Переподключение к базе данных...")
        self.close()
        self.connect_with_retry()

    def __enter__(self):
        """Поддержка контекстного менеджера"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие соединения при выходе из контекста"""
        self.close()



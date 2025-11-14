import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import re
import math
from collections import Counter
import pymorphy3  

class SentimentAnalyzer:
    def __init__(self):
        self.morph = pymorphy3.MorphAnalyzer()
        
        # Расширенные словари с весами
        self.positive_words = {
            'успех': 1.5, 'победа': 2.0, 'развитие': 1.2, 'инновация': 1.8, 'достижение': 1.5,
            'награда': 1.7, 'лидер': 1.3, 'рост': 1.2, 'прорыв': 2.0, 'улучшение': 1.3,
            'эффективный': 1.2, 'перспективный': 1.4, 'качество': 1.1, 'прогресс': 1.3,
            'стабильность': 1.1, 'приз': 1.5, 'отличный': 1.6, 'премия': 1.4, 'инвестиция': 1.3,
            'снижение': 1.0, 'доступный': 1.1, 'рекорд': 1.8, 'успешный': 1.5, 'развивать': 1.2,
            'поддержка': 1.1, 'сотрудничество': 1.0, 'партнерство': 1.0, 'новый': 0.8,
            'первый': 0.9, 'лучший': 1.7, 'высокий': 1.2, 'большой': 0.8, 'хороший': 1.3
        }
        
        self.negative_words = {
            'проблема': -1.5, 'кризис': -2.0, 'сложный': -1.3, 'падение': -1.8, 'убыток': -2.0,
            'поражение': -1.7, 'авария': -2.2, 'смерть': -2.5, 'трагедия': -2.3, 'конфликт': -1.8,
            'спор': -1.4, 'забастовка': -1.9, 'увольнение': -1.7, 'сокращение': -1.8,
            'банкротство': -2.2, 'долг': -1.6, 'задолженность': -1.7, 'штраф': -1.5,
            'нарушение': -1.6, 'пожар': -2.1, 'наводнение': -2.0, 'землетрясение': -2.2,
            'теракт': -2.5, 'преступление': -2.0, 'обман': -1.8, 'коррупция': -2.1,
            'скандал': -1.9, 'расследование': -1.2, 'суд': -1.3, 'плохой': -1.4,
            'низкий': -1.1, 'маленький': -0.8, 'старый': -0.7, 'сложность': -1.3
        }
        
        # Слова-усилители и ослабители
        self.intensifiers = {
            'очень': 1.5, 'сильно': 1.4, 'крайне': 1.6, 'абсолютно': 1.5, 'совершенно': 1.4,
            'чрезвычайно': 1.7, 'исключительно': 1.6
        }
        
        self.diminishers = {
            'слегка': 0.7, 'немного': 0.8, 'чуть': 0.7, 'почти': 0.9, 'отчасти': 0.8
        }

    def normalize_word(self, word):
        """Приводит слово к нормальной форме"""
        parsed = self.morph.parse(word)[0]
        return parsed.normal_form

    def tokenize_text(self, text):
        """Разбивает текст на токены (слова)"""
        # Удаляем знаки препинания и разбиваем на слова
        words = re.findall(r'\b[а-яё]+\b', text.lower())
        return [self.normalize_word(word) for word in words]

    def calculate_sentiment_score(self, text):
        """Вычисляет математическую оценку тональности текста"""
        if not text:
            return 0.0
            
        tokens = self.tokenize_text(text)
        if not tokens:
            return 0.0
            
        total_score = 0.0
        word_count = len(tokens)
        
        for i, token in enumerate(tokens):
            # Проверяем основной тон слова
            if token in self.positive_words:
                score = self.positive_words[token]
            elif token in self.negative_words:
                score = self.negative_words[token]
            else:
                continue
                
            # Проверяем усилители/ослабители перед текущим словом
            if i > 0:
                prev_token = tokens[i-1]
                if prev_token in self.intensifiers:
                    score *= self.intensifiers[prev_token]
                elif prev_token in self.diminishers:
                    score *= self.diminishers[prev_token]
                    
            total_score += score
        
        # Нормализуем оценку по количеству слов
        if word_count > 0:
            normalized_score = total_score / math.sqrt(word_count)
        else:
            normalized_score = 0.0
            
        return normalized_score

    def classify_sentiment(self, score):
        """Классифицирует тональность на основе числовой оценки"""
        if score > 0.3:
            return "Положительный"
        elif score < -0.3:
            return "Негативный"
        else:
            return "Нейтральный"

    def analyze_sentiment(self, text):
        """Основная функция анализа тональности"""
        score = self.calculate_sentiment_score(text)
        sentiment = self.classify_sentiment(score)
        return sentiment, score

def search_google_news_alternative(query):
    """Альтернативный метод поиска новостей с улучшенной эмоциональной оценкой"""
    try:
        # Параметры запроса
        params = {
            'q': query,
            'tbm': 'nws',
            'hl': 'ru',
            'gl': 'ru',
            'ceid': 'RU:ru',
            'tbs': 'qdr:w'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        url = "https://www.google.com/search"
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            news_results = []
            
            selectors = [
                'div.SoaBEf', 'div.MjjYud', 'div.g', 'div.VwiC3b', 'a.WlydOe',
            ]
            
            # Инициализируем анализатор
            analyzer = SentimentAnalyzer()
            
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    title_elem = element.select_one('h3, .n0jPhd, .ynAwRc, .mCBkyc, .JtKRv')
                    link_elem = element.select_one('a')
                    source_elem = element.select_one('.MgUUmf, .NUnG9d, .OSrXXb, .CEMjEf')
                    date_elem = element.select_one('.OSrXXb, .r0jCaf, .hFTDmf')
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text().strip()
                        link = link_elem.get('href')
                        source = source_elem.get_text().strip() if source_elem else "Неизвестный источник"
                        date_text = date_elem.get_text().strip() if date_elem else ""
                        
                        if link and '/url?q=' in link:
                            link = link.split('/url?q=')[1].split('&')[0]
                        
                        # Анализируем эмоциональную окраску с помощью математического метода
                        sentiment, score = analyzer.analyze_sentiment(title)
                        
                        formatted_date = format_date(date_text)
                        
                        if title and link and 'http' in link:
                            news_results.append({
                                'title': title,
                                'link': link,
                                'source': source,
                                'date_text': formatted_date,
                                'sentiment': sentiment,
                                'sentiment_score': round(score, 3)
                            })
            
            return news_results
        else:
            print(f"Ошибка запроса: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"Ошибка при поиске новостей: {e}")
        return []

def format_date(date_text):
    """Преобразует дату в стандартный формат дд.мм.гггг"""
    if not date_text:
        return ""
    
    current_date = datetime.now()
    date_text_lower = date_text.lower()
    
    months = {
        'янв': '01', 'января': '01', 'фев': '02', 'февраля': '02',
        'мар': '03', 'марта': '03', 'апр': '04', 'апреля': '04',
        'май': '05', 'мая': '05', 'июн': '06', 'июня': '06',
        'июл': '07', 'июля': '07', 'авг': '08', 'августа': '08',
        'сен': '09', 'сентября': '09', 'окт': '10', 'октября': '10',
        'ноя': '11', 'ноября': '11', 'дек': '12', 'декабря': '12'
    }
    
    if 'час' in date_text_lower or 'минут' in date_text_lower:
        return current_date.strftime("%d.%m.%Y")
    
    if 'вчера' in date_text_lower:
        yesterday = current_date - timedelta(days=1)
        return yesterday.strftime("%d.%m.%Y")
    
    if 'день' in date_text_lower or 'дня' in date_text_lower:
        days_match = re.search(r'(\d+)', date_text)
        if days_match:
            days_ago = int(days_match.group(1))
            target_date = current_date - timedelta(days=days_ago)
            return target_date.strftime("%d.%m.%Y")
    
    cleaned_date = re.sub(r'г\.|\.', '', date_text).strip()
    date_parts = cleaned_date.split()
    
    if len(date_parts) >= 3:
        day = date_parts[0].zfill(2)
        month_str = date_parts[1].lower()
        month = months.get(month_str, '')
        year = date_parts[2]
        
        if day and month and year:
            return f"{day}.{month}.{year}"
    
    return date_text

def save_to_csv(news_list, filename='news_ngtu_with_sentiment.csv'):
    """Сохраняет список новостей в CSV файл с эмоциональной оценкой"""
    if not news_list:
        print("Нет данных для сохранения")
        return
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['title', 'link', 'date', 'sentiment', 'sentiment_score']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        
        writer.writeheader()
        for news in news_list:
            row = {
                'title': news['title'],
                'link': news['link'],
                'date': news['date_text'],
                'sentiment': news['sentiment'],
                'sentiment_score': news['sentiment_score']
            }
            writer.writerow(row)
    
    print(f"Данные сохранены в файл: {filename}")
    print(f"Сохранено записей: {len(news_list)}")
    
    # Статистика по эмоциям
    sentiment_counts = Counter([news['sentiment'] for news in news_list])
    print(f"\nСтатистика эмоциональной окраски:")
    for sentiment in ["Положительный", "Нейтральный", "Негативный"]:
        count = sentiment_counts.get(sentiment, 0)
        print(f"  {sentiment}: {count} новостей")
    
    # Средняя оценка тональности
    if news_list:
        avg_score = sum(news['sentiment_score'] for news in news_list) / len(news_list)
        print(f"  Средняя оценка тональности: {avg_score:.3f}")

def parse_score_write():
    query = "НГТУ новости"
    
    print("Поиск новостей с математическим анализом тональности...")
    results = search_google_news_alternative(query)
    
    if not results:
        print("Новости не найдены")
        return
    
    print(f"Найдено {len(results)} новостей")
    
    # Сохраняем в CSV
    if results:
        save_to_csv(results)
        
        # Показываем примеры с детальным анализом
        print(f"\nПримеры новостей с анализом тональности:")
        for i, news in enumerate(results[:5], 1):
            sentiment = news['sentiment']
            score = news['sentiment_score']
            print(f"{i}. [{sentiment}] (оценка: {score}) {news['title']}")
            print(f"   Ссылка: {news['link']}")
            print(f"   Дата: {news['date_text']}\n")
    else:
        print("Нет новостей за последнюю неделю")



def save_news_to_db(news_list):
    """Сохраняет список новостей в базу данных"""
    if not news_list:
        print("Нет данных для сохранения в БД")
        return False
    
    try:
        # Импортируем db из config здесь, чтобы избежать циклического импорта
        from config import db
        conn = db.conn
        with conn.cursor() as cur:
            # Подготавливаем запрос для вставки
            insert_query = """
            INSERT INTO news (title, link, source, date_text, sentiment, sentiment_score)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (link) DO NOTHING
            """
            
            # Вставляем каждую новость
            for news in news_list:
                cur.execute(insert_query, (
                    news['title'],
                    news['link'],
                    news['source'],
                    news['date_text'],
                    news['sentiment'],
                    news['sentiment_score']
                ))
            
            conn.commit()
        
        print(f"Успешно сохранено новостей в БД: {len(news_list)}")
        return True
        
    except Exception as e:
        print(f"Ошибка при сохранении в БД: {e}")
        conn.rollback()
        return False

def parse_and_save_news():
    """Парсит новости и сохраняет в базу данных"""
    query = "НГТУ новости"
    
    print("Запуск парсера новостей...")
    results = search_google_news_alternative(query)
    
    if not results:
        print("Новости не найдены")
        return False
    
    print(f"Найдено {len(results)} новостей")
    
    # Сохраняем в базу данных
    success = save_news_to_db(results)
    
    if success:
        # Статистика
        sentiment_counts = Counter([news['sentiment'] for news in results])
        print(f"\nСтатистика эмоциональной окраски:")
        for sentiment in ["Положительный", "Нейтральный", "Негативный"]:
            count = sentiment_counts.get(sentiment, 0)
            print(f"  {sentiment}: {count} новостей")
        
        avg_score = sum(news['sentiment_score'] for news in results) / len(results)
        print(f"  Средняя оценка тональности: {avg_score:.3f}")
    
    return success

def parse_and_save_news_with_stats():
    
    query = "НГТУ новости"
    
    print("Запуск парсера новостей...")
    results = search_google_news_alternative(query)
    
    if not results:
        print("Новости не найдены")
        return []
    
    print(f"Найдено {len(results)} новостей")
    
    # Сохраняем в базу данных
    save_news_to_db(results)
    
    # Выводим статистику в консоль (как было раньше)
    sentiment_counts = Counter([news['sentiment'] for news in results])
    print(f"\nСтатистика эмоциональной окраски:")
    for sentiment in ["Положительный", "Нейтральный", "Негативный"]:
        count = sentiment_counts.get(sentiment, 0)
        print(f"  {sentiment}: {count} новостей")
    
    avg_score = sum(news['sentiment_score'] for news in results) / len(results)
    print(f"  Средняя оценка тональности: {avg_score:.3f}")
    
    # Возвращаем результаты для использования в боте
    return results



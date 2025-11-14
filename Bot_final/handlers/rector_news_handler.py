from config import bot, logger, db
from maxgram.keyboards import InlineKeyboard
from collections import Counter
from urllib.parse import urlparse

def get_safe_user_id(context):
    """Безопасное получение user_id"""
    try:
        return context.message['recipient']['chat_id']
    except:
        return "unknown"

def handle_rector_documents(context):
    """Обработчик для кнопки '📑 Последние новости' - загружает новости и показывает последние 10"""
    user_id = get_safe_user_id(context)
    
    # Запускаем парсер
    context.reply_callback("🔄 Запускаю парсер новостей... Это может занять несколько секунд.")
    
    try:
        # Запускаем парсер и получаем результаты со статистикой
        news_results, stats_message = run_parser_with_stats()
        
        if not news_results:
            message = "❌ Новости не найдены или произошла ошибка."
            keyboard = InlineKeyboard(
                [{"text": "🔙 Назад в меню", "callback": "back_to_menu"}]
            )
        else:
            # Получаем последние 10 новостей из БД
            news_list = get_recent_news_from_db(limit=10)
            
            if news_list:
                # Формируем сообщение со статистикой и списком новостей
                message = "✅ Новости успешно загружены!\n\n"
                message += stats_message
                message += "\n\n📰 Последние 10 новостей НГТУ:\n\n"
                
                for i, news in enumerate(news_list, 1):
                    sentiment_emoji = {
                        "Положительный": "📈",
                        "Нейтральный": "😐", 
                        "Негативный": "📉"
                    }.get(news['sentiment'], '📄')
                    
                    # Обрезаем длинный заголовок
                    title = news['title']
                    if len(title) > 80:
                        title = title[:77] + "..."
                    
                    # Очищаем источник от URL и обрезаем
                    source = clean_source(news['source'])
                    if len(source) > 25:
                        source = source[:22] + "..."
                    
                    message += f"{i}. {sentiment_emoji} [{news['sentiment']}] {title}\n"
                    message += f"   📅 {news['date_text']} | 📰 {source}\n\n"
                
                # Создаем клавиатуру с кнопками-ссылками на каждую новость
                keyboard_rows = []
                for i, news in enumerate(news_list, 1):
                    # Очищаем ссылку от параметров Google
                    clean_link = get_clean_news_link(news['link'])
                    
                    # Создаем кнопку с полной ссылкой
                    keyboard_rows.append([
                        {"text": f"🔗 Ссылка на новость {i}", "url": clean_link}
                    ])
                
                # Добавляем кнопку "Назад"
                keyboard_rows.append([
                    {"text": "🔙 Назад в меню", "callback": "back_to_menu"}
                ])
                
                keyboard = InlineKeyboard(*keyboard_rows)
            else:
                message = "📭 В базе данных нет новостей.\n\n" + stats_message
                keyboard = InlineKeyboard(
                    [{"text": "🔙 Назад в меню", "callback": "back_to_menu"}]
                )
                
    except Exception as e:
        logger.error(f"Ошибка при работе с новостями: {e}")
        message = "❌ Произошла ошибка при загрузке новостей."
        keyboard = InlineKeyboard(
            [{"text": "🔙 Назад в меню", "callback": "back_to_menu"}]
        )
    
    # Отправляем сообщение с новостями и кнопками-ссылками
    context.reply_callback(message, keyboard=keyboard)

def run_parser_with_stats():
    """Запускает парсер и возвращает результаты со статистикой"""
    # Импортируем здесь чтобы избежать циклических импортов
    from rector.parser import search_google_news_alternative, save_news_to_db
    
    query = "НГТУ новости"
    
    print("Запуск парсера новостей...")
    results = search_google_news_alternative(query)
    
    if not results:
        print("Новости не найдены")
        return [], ""
    
    print(f"Найдено {len(results)} новостей")
    
    # Сохраняем в базу данных
    save_news_to_db(results)
    
    # Считаем статистику
    sentiment_counts = Counter([news['sentiment'] for news in results])
    avg_score = sum(news['sentiment_score'] for news in results) / len(results)
    
    # Формируем сообщение со статистикой
    stats_message = "Статистика эмоциональной окраски:\n"
    for sentiment in ["Положительный", "Нейтральный", "Негативный"]:
        count = sentiment_counts.get(sentiment, 0)
        stats_message += f"  {sentiment}: {count} новостей\n"
    stats_message += f"  Средняя оценка тональности: {avg_score:.3f}"
    
    # Выводим статистику в консоль (как было раньше)
    print(f"\n{stats_message}")
    
    return results, stats_message

def get_recent_news_from_db(limit=10):
    """Получает последние новости из базы данных"""
    try:
        with db.conn.cursor() as cur:
            cur.execute("""
                SELECT title, link, source, date_text, sentiment, sentiment_score
                FROM news 
                ORDER BY parsed_at DESC 
                LIMIT %s
            """, (limit,))
            
            news_list = []
            for row in cur.fetchall():
                news_list.append({
                    'title': row[0],
                    'link': row[1],
                    'source': row[2],
                    'date_text': row[3],
                    'sentiment': row[4],
                    'sentiment_score': float(row[5]) if row[5] else 0.0
                })
            
            return news_list
            
    except Exception as e:
        print(f"Ошибка при получении новостей из БД: {e}")
        return []

def get_clean_news_link(url):
    """Очищает ссылку на новость от параметров Google"""
    try:
        # Очищаем URL от параметров Google
        if '/url?q=' in url:
            url = url.split('/url?q=')[1].split('&')[0]
        
        # Декодируем URL-encoded символы
        from urllib.parse import unquote
        url = unquote(url)
        
        return url
            
    except:
        return url

def clean_source(source):
    """Очищает источник от URL и оставляет только название"""
    if not source:
        return "Неизвестный источник"
    
    # Если источник начинается с http, извлекаем домен
    if source.startswith('http'):
        return get_domain_from_url(source)
    
    # Убираем лишние части из названия источника
    source = source.replace('http://', '').replace('https://', '')
    
    # Убираем параметры RSS и другие технические части
    if '?option=' in source:
        source = source.split('?')[0]
    
    # Если после очистки это все еще выглядит как URL, извлекаем домен
    if '.' in source and ('/' in source or source.count('.') >= 2):
        try:
            parsed = urlparse('http://' + source if not source.startswith('http') else source)
            domain = parsed.netloc if parsed.netloc else parsed.path.split('/')[0]
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            pass
    
    return source

def get_domain_from_url(url):
    """Извлекает домен из URL для отображения источника"""
    try:
        # Очищаем URL от параметров Google
        if '/url?q=' in url:
            url = url.split('/url?q=')[1].split('&')[0]
        
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Убираем www. если есть
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    except:
        return "ссылка"
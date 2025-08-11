import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os
from functools import wraps

KEYWORDS = ['дизайн', 'фото', 'web', 'python']
URL = 'https://habr.com/ru/articles/'
LOG_FILE = 'habr_parser.log'

def logger(path):
    def __logger(old_function):
        @wraps(old_function)
        def new_function(*args, **kwargs):
            call_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            function_name = old_function.__name__
            
            try:
                result = old_function(*args, **kwargs)
                log_entry = (
                    f"{call_time} - Функция: {function_name}\n"
                    f"Аргументы: args={args}, kwargs={kwargs}\n"
                    f"Успешно выполнена\n"
                    f"Результат: {str(result)[:100] + '...' if len(str(result)) > 100 else result}\n\n"
                )
                status = 'SUCCESS'
                return result
            except Exception as e:
                log_entry = (
                    f"{call_time} - Функция: {function_name}\n"
                    f"Аргументы: args={args}, kwargs={kwargs}\n"
                    f"Ошибка: {type(e).__name__}: {str(e)}\n\n"
                )
                status = 'ERROR'
                raise
            finally:
                with open(path, 'a', encoding='utf-8') as log_file:
                    log_file.write(log_entry)
                if status == 'ERROR':
                    with open(path, 'a', encoding='utf-8') as log_file:
                        log_file.write(f"!!! Функция завершилась с ошибкой !!!\n\n")
        
        return new_function
    return __logger

@logger(LOG_FILE)
def check_article_content(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()   
    soup = BeautifulSoup(response.text, 'html.parser')
    article_content = soup.find('div', class_='article-formatted-body')
    
    if article_content:
        content_text = article_content.text.lower()
        found_keywords = [kw for kw in KEYWORDS if kw.lower() in content_text]
        return len(found_keywords) > 0, found_keywords
    return False, []

@logger(LOG_FILE)
def scrape_habr():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    
    response = requests.get(URL, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('article')
    results = []
    
    for article in articles:
        try:
            title = article.find('h2').find('a').text
            time_tag = article.find('time')
            date_str = time_tag['datetime']
            date_str_fixed = re.sub(r'\.\d+Z$', '+0000', date_str)
            date = datetime.strptime(date_str_fixed, '%Y-%m-%dT%H:%M:%S%z').strftime('%d.%m.%Y')
            link = article.find('h2').find('a')['href']
            
            if not link.startswith('http'):
                link = 'https://habr.com' + link
            
            preview_text = ' '.join([p.text for p in article.find_all('p')])
            preview_match = any(keyword.lower() in title.lower() or 
                              keyword.lower() in preview_text.lower() 
                              for keyword in KEYWORDS)
            
            if not preview_match:
                content_match, found_kw = check_article_content(link)
                if content_match:
                    result = f"{date} – {title} – {link} (найдены ключевые слова: {', '.join(found_kw)})"
                    print(result)
                    results.append(result)
            else:
                found_kw = [kw for kw in KEYWORDS if kw.lower() in title.lower() or kw.lower() in preview_text.lower()]
                result = f"{date} – {title} – {link} (найдены ключевые слова: {', '.join(found_kw)})"
                print(result)
                results.append(result)
                
        except Exception as e:
            with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                log_file.write(f"Ошибка при обработке статьи: {str(e)}\n")
            continue
    
    return results

if __name__ == '__main__':
    scrape_habr()
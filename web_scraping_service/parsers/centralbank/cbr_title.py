import requests
from bs4 import BeautifulSoup
import time
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CBRAnalyticsParser:
    def __init__(self):
        self.base_url = "https://cbr.ru"
        self.feed_id = 84521  
        self.load_more_url = f"{self.base_url}/Crosscut/CrosscutFeed/LoadFeedContent/{self.feed_id}"

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'text/html, */*; q=0.01',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'X-Requested-With': 'XMLHttpRequest',  
            'Referer': f'{self.base_url}/analytics/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }

    def get_first_page(self):
        """Получаем первую страницу с первыми 10 элементами"""
        response = requests.get(f"{self.base_url}/analytics/", headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        items = self.parse_items(soup)
        return items

    def load_more(self, index=10, ordinal=10):
        """
        Подгружаем следующую порцию элементов через AJAX

        Args:
            index: номер следующего элемента для загрузки (10, 20, 30...)
            ordinal: порядковый номер (обычно равен index)
        """
        params = {
            'Index': index,
            'Ordinal': ordinal,
        }

        try:
            response = requests.get(
                self.load_more_url, 
                params=params, 
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                return self.parse_items(soup)
            else:
                logger.error(f"Ошибка: HTTP {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            return []

    def parse_items(self, soup):
        """Парсим элементы из HTML"""
        items = []
        result_divs = soup.find_all('div', class_='cross-result')
        
        if not result_divs:
            result_divs = soup.select('.cross-results > div')
        
        if not result_divs:
            result_divs = soup.find_all('div', recursive=False)

        for div in result_divs:
            title_div = div.select_one('div.title-source > div.title')
            if not title_div:
                title_div = div.select_one('div.title')
            
            main_link = None
            
            if title_div:
                main_link = title_div.find('a')
            
            if not main_link:
                for link in div.find_all('a', attrs={'data-zoom-referer': True}):
                    if link.find_parent('div', class_='versions'):
                        continue
                    main_link = link
                    break
            
            title = ""
            if title_div:
                title_text = title_div.get_text(strip=True)
                if title_div.find('a'):
                    title = title_div.find('a').get_text(strip=True)
                else:
                    title = title_text
            elif main_link:
                title = main_link.get_text(strip=True)
            
            source_elem = div.select_one('div.source > a')
            source = source_elem.get_text(strip=True) if source_elem else ""
            
            if main_link:
                href = main_link.get('href', '')
                if href and not href.startswith('http'):
                    href = self.base_url + href
                
                referer = main_link.get('data-zoom-referer', '')
                referer_title = main_link.get('data-zoom-referer-title', '')
                
                if title and href:
                    items.append({
                        'title': title,
                        'url': href,
                        'source': source,
                        'data_zoom_referer': referer,
                        'data_zoom_referer_title': referer_title,
                    })
            else:
                versions_div = div.find('div', class_='versions')
                if versions_div and title:
                    version_links = versions_div.find_all('a', class_='versions_item')[:1]
                    
                    for version_link in version_links:
                        href = version_link.get('href', '')
                        if href and not href.startswith('http'):
                            href = self.base_url + href
                        
                        version_title = version_link.get_text(strip=True)
                        referer = version_link.get('data-zoom-referer', '')
                        referer_title = version_link.get('data-zoom-referer-title', '')
                        
                        if href:
                            items.append({
                                'title': f"{title} - {version_title}",
                                'url': href,
                                'source': source,
                                'data_zoom_referer': referer,
                                'data_zoom_referer_title': referer_title,
                            })

        return items

    def parse_all(self, max_items=None, delay=1):
        """
        Парсим все элементы

        Args:
            max_items: максимальное количество элементов (None = все)
            delay: задержка между запросами в секундах
        """
        all_items = []

        logger.info("Загружаем первую страницу...")
        items = self.get_first_page()
        all_items.extend(items)
        logger.info(f"Загружено {len(all_items)} элементов")

        index = 10  
        empty_responses = 0  

        while True:
            if max_items and len(all_items) >= max_items:
                logger.info(f"Достигнут лимит: {max_items} элементов")
                break

            time.sleep(delay)

            logger.info(f"Загружаем элементы с {index}...")
            items = self.load_more(index=index, ordinal=index)

            if not items:
                empty_responses += 1
                logger.warning(f"Пустой ответ (попытка {empty_responses}/3)")

                if empty_responses >= 3:
                    logger.info("Достигнут конец списка")
                    break
            else:
                empty_responses = 0  
                all_items.extend(items)
                logger.info(f"Загружено {len(all_items)} элементов")

            index += 10

        return all_items

    def save_to_json(self, items, filename='cbr_analytics.json'):
        """Сохраняем результаты в JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        logger.info(f"Данные сохранены в {filename}")

    def save_to_csv(self, items, filename='cbr_analytics.csv'):
        """Сохраняем результаты в CSV"""
        import csv

        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            if items:
                writer = csv.DictWriter(f, fieldnames=items[0].keys())
                writer.writeheader()
                writer.writerows(items)
        logger.info(f"Данные сохранены в {filename}")
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re


class PravoGovRuParser:
    """
    Парсер для извлечения ссылок и номеров из раздела published-tabs на pravo.gov.ru
    """

    def __init__(self):
        self.base_url = "http://pravo.gov.ru/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def fetch_page(self) -> Optional[str]:
        """
        Получает HTML-контент главной страницы
        """
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException:
            return None
    
    def parse_all_data(self, html_content: str) -> Dict[str, any]:
        """
        Парсит все данные: ссылки из блока #daily и номера из #daily
        """
        if not html_content:
            return {'published_tabs': [], 'daily_numbers': []}
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        data = {
            'published_tabs': [],
            'daily_numbers': []
        }
        
        seen_urls = set()
        
        daily_block = soup.select_one('#daily')
        if daily_block:
            text_elements = daily_block.select('div.td.text')
            
            for text_elem in text_elements:
                link = text_elem.find('a', href=True)
                if not link:
                    continue
                
                url = link['href']
                text = link.get_text(strip=True)
                full_url = self._make_absolute_url(url) if url else None
                
                number = None
                parent_row = text_elem.find_parent('div', class_='tr')
                if not parent_row:
                    parent_row = text_elem.find_parent('div')
                
                if parent_row:
                    numb_elem = parent_row.find('div', class_='numb')
                    if numb_elem:
                        number_text = numb_elem.get_text(strip=True)
                        number = number_text if number_text else None
                
                if full_url and full_url not in seen_urls:
                    item = {
                        'number': number,
                        'text': text,
                        'url': url,
                        'full_url': full_url
                    }
                    data['published_tabs'].append(item)
                    seen_urls.add(full_url)
            
            numb_elements = daily_block.select('div.td.numb')
            seen_numbers = set()
            for elem in numb_elements:
                number = elem.get_text(strip=True)
                if number and number not in seen_numbers:
                    data['daily_numbers'].append(number)
                    seen_numbers.add(number)
        
        return data
    
    def _make_absolute_url(self, url: str) -> str:
        """
        Преобразует относительные URL в абсолютные
        """
        if url.startswith('http'):
            return url
        elif url.startswith('/'):
            return f"http://pravo.gov.ru{url}"
        else:
            return f"http://pravo.gov.ru/{url}"
    
    def run(self) -> List[str]:
        """
        Запускает процесс парсинга и возвращает список URL элементов с номерами
        из разрешенных категорий (только daily ссылки)
        """

        allowed_categories = {
            "Правительство",
            "Федеральные органы исполнительной власти РФ",
            "Президент",
            "Органы государственной власти субъектов РФ",
            "Государственная Дума",
            "Совет Федерации",
            "Конституционный суд"
        }
        
        html = self.fetch_page()
        
        if not html:
            return []
        
        data = self.parse_all_data(html)
        
        urls = []
        for item in data['published_tabs']:
            if not item.get('full_url'):
                continue
            
            number = item.get('number')
            if not number or number == '' or number is None:
                continue
            
            text = item.get('text')
            if not text:
                continue
            
            text_clean = re.sub(r'\s+', ' ', text.strip())
            
            found = False
            for cat in allowed_categories:
                cat_clean = re.sub(r'\s+', ' ', cat.strip())
                if text_clean == cat_clean:
                    found = True
                    break
            
            if not found:
                continue
            
            urls.append(item['full_url'])
        
        return urls


if __name__ == "__main__":
    parser = PravoGovRuParser()
    urls = parser.run()
    for url in urls:
        print(url)

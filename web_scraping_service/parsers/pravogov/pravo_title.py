import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


class PravoReviewParser:
    """
    Парсер для извлечения титульников и ссылок документов с pravo.gov.ru
    """
    
    def __init__(self, base_url: str = "http://publication.pravo.gov.ru"):
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def _make_absolute_url(self, url: str) -> str:
        """
        Преобразует относительные URL в абсолютные
        """
        if url.startswith('http'):
            return url
        elif url.startswith('/'):
            return f"{self.base_url}{url}"
        else:
            return f"{self.base_url}/{url}"
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Получает HTML-контент страницы
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException:
            return None
    
    def _get_next_url(self, url: str) -> Optional[str]:
        """
        Формирует URL следующей страницы, увеличивая index на 1
        
        Args:
            url: Текущий URL
            
        Returns:
            URL следующей страницы
        """
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        current_index = int(params.get('index', ['1'])[0])
        next_index = current_index + 1
        
        params['index'] = [str(next_index)]
        
        new_query = urlencode(params, doseq=True)
        new_parsed = parsed._replace(query=new_query)
        
        return urlunparse(new_parsed)
    
    def _parse_documents_from_page(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Парсит документы с текущей страницы
        
        Args:
            soup: BeautifulSoup объект страницы
            
        Returns:
            Список словарей с ключами 'title' и 'url'
        """
        documents = []
        
        document_list_div = soup.select_one('#documentListDiv')
        if not document_list_div:
            return documents
        
        documents_container = document_list_div.select_one('div.documents-container')
        if not documents_container:
            return documents
        
        rows = documents_container.select('div.documents-table-row')
        
        for row in rows:
            title_link = row.select_one('a.documents-item-name')
            if not title_link:
                continue
            
            title = title_link.get_text(strip=True)
            href = title_link.get('href', '')
            
            if not title or not href:
                continue
            
            full_url = self._make_absolute_url(href)
            
            documents.append({
                'title': title,
                'url': full_url
            })
        
        return documents
    
    def parse_documents_from_url(self, url: str) -> List[Dict[str, str]]:
        """
        Парсит все документы со страницы и всех последующих страниц
        
        Args:
            url: URL страницы для парсинга
            
        Returns:
            Список словарей с ключами 'title' и 'url'
        """
        documents = []
        current_url = url
        
        while current_url:
            html = self._fetch_page(current_url)
            if not html:
                break
            
            soup = BeautifulSoup(html, 'html.parser')
            
            page_documents = self._parse_documents_from_page(soup)
            
            if not page_documents:
                break
            
            documents.extend(page_documents)
            
            current_url = self._get_next_url(current_url)
        
        return documents
    
    def run(self, url: str) -> List[Dict[str, str]]:
        """
        Запускает парсинг документов
        
        Args:
            url: URL страницы для парсинга
            
        Returns:
            Список словарей с ключами 'title' и 'url'
        """
        return self.parse_documents_from_url(url)


if __name__ == "__main__":
    count = 0
    parser = PravoReviewParser()
    url = "http://publication.pravo.gov.ru/documents/daily?block=subjects"
    documents = parser.run(url)

    
    for doc in documents:
        count += 1
        print(f"{count}. Title: {doc['title']}")
        print(f"URL: {doc['url']}")
        print("---")

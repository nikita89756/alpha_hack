import logging
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NalogPageParser:
    """Парсер контента со страниц nalog.gov.ru"""
    
    def __init__(self):
        """Инициализация парсера"""
        logger.info("Инициализирован парсер страниц nalog.gov.ru")
    
    def parse_page(self, url: str) -> str:
        """
        Парсит контент страницы
        
        Args:
            url: URL страницы для парсинга
            
        Returns:
            Текстовый контент страницы
        """
        try:
            logger.info(f"Парсим страницу: {url}")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                page.goto(url, wait_until='networkidle', timeout=60000)
                logger.info("Страница загружена")
                
                time.sleep(2)
                
                html = page.content()
                browser.close()
                
                soup = BeautifulSoup(html, 'html.parser')
                
                content_div = soup.select_one('#MainForm > div.wrap-all > div.wrap-content > div.wrapper.wrapper_blue-light > div.content')
                
                if not content_div:
                    logger.warning("Контент не найден по селектору")
                    return ""
                
                text = self._extract_text(content_div)
                
                logger.info(f"Извлечено {len(text)} символов")
                return text
                
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _extract_text(self, element) -> str:
        """
        Извлекает текст из HTML элемента с сохранением структуры
        Парсит элементы последовательно как они идут в HTML
        
        Args:
            element: BeautifulSoup элемент
            
        Returns:
            Форматированный текст
        """
        lines = []
        
        for child in element.descendants:
            if isinstance(child, str) or not hasattr(child, 'name'):
                continue
            
            if child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                text = child.get_text(strip=True)
                if text and not self._is_inside_processed(child):
                    lines.append(f"\n\n{text.upper()}")
            
            elif child.name == 'p':
                temp_element = child.__copy__()
                for button in temp_element.find_all(['button', 'a']):
                    button.decompose()
                
                text = temp_element.get_text(strip=True)
                has_emphasis = child.find(['em', 'strong'])
                min_length = 3 if has_emphasis else 10
                
                if text and len(text) >= min_length and not self._is_inside_processed(child):
                    lines.append(f"\n{text}")
            
            elif child.name == 'div':
                if child.find(['div', 'p', 'ul', 'ol', 'table'], recursive=False):
                    continue
                
                temp_element = child.__copy__()
                for button in temp_element.find_all(['button', 'a']):
                    button.decompose()
                
                text = temp_element.get_text(strip=True)
                if text and len(text) > 10 and not self._is_inside_processed(child):
                    lines.append(f"\n{text}")
            
            elif child.name in ['ul', 'ol']:
                if not self._is_inside_processed(child):
                    for li in child.find_all('li', recursive=False):
                        text = li.get_text(strip=True)
                        if text:
                            lines.append(f"  • {text}")
            
            elif child.name == 'table':
                if not self._is_inside_processed(child):
                    lines.append("\n" + "="*80)
                    lines.append("ТАБЛИЦА:")
                    lines.append("="*80)
                    
                    for row in child.find_all('tr'):
                        cells = []
                        for cell in row.find_all(['td', 'th']):
                            cell_text = cell.get_text(strip=True)
                            if cell_text:
                                cells.append(cell_text)
                        
                        if cells:
                            lines.append(" | ".join(cells))
        
        return '\n'.join(lines)
    
    def _is_inside_processed(self, element) -> bool:
        """
        Проверяет находится ли элемент внутри уже обработанного
        
        Args:
            element: Проверяемый элемент
            
        Returns:
            True если элемент внутри списка/таблицы
        """
        parent = element.parent
        while parent:
            if parent.name in ['ul', 'ol', 'table']:
                return True
            parent = parent.parent
        return False
    
    def save_to_file(self, text: str, filename: str = 'nalog_page.txt'):
        """
        Сохраняет текст в файл
        
        Args:
            text: Текст для сохранения
            filename: Имя файла
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(text)
            logger.info(f"Текст сохранён в {filename}")
        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")



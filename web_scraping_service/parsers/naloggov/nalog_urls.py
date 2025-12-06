import logging
from playwright.sync_api import sync_playwright
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NalogGovParser:
    """Парсер ссылок с nalog.gov.ru"""
    
    def __init__(self):
        """Инициализация парсера"""
        self.base_url = "https://www.nalog.gov.ru/new2025/"
        self.urls = set() 
        logger.info("Инициализирован парсер nalog.gov.ru")
    
    def parse_all(self) -> set:
        """
        Парсит все ссылки для ИП и ЮЛ
        
        Returns:
            Множество уникальных URL
        """
        try:
            with sync_playwright() as p:
                logger.info("Запускаем браузер...")
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                logger.info(f"Загружаем страницу: {self.base_url}")
                page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                logger.info("Страница загружена")
                
                time.sleep(2)
                
                logger.info("Парсим ссылки для ИП...")
                self._parse_tab(page, "tab-IP", "ИП")
                
                logger.info("Парсим ссылки для ЮЛ...")
                self._parse_tab(page, "tab-UL", "ЮЛ")
                
                browser.close()
                
                logger.info(f"Всего найдено уникальных ссылок: {len(self.urls)}")
                return self.urls
                
        except Exception as e:
            logger.error(f"Ошибка при парсинге: {e}")
            import traceback
            traceback.print_exc()
            return self.urls
    
    def _parse_tab(self, page, button_id: str, tab_name: str):
        """
        Парсит ссылки на вкладке
        
        Args:
            page: Playwright page объект
            button_id: ID кнопки таба
            tab_name: Название таба для логов
        """
        try:
            logger.info(f"Кликаем на кнопку '{tab_name}'...")
            button = page.locator(f"#{button_id}")
            button.click()
            
            time.sleep(2)
            
            links = page.locator("a[href]").all()
            
            initial_count = len(self.urls)
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href:
                        if href.startswith('http'):
                            full_url = href
                        elif href.startswith('/'):
                            full_url = f"https://www.nalog.gov.ru{href}"
                        else:
                            continue
                        
                        if (full_url.startswith('https://www.nalog.gov.ru/rn77') and 
                            not full_url.startswith('https://www.nalog.gov.ru/rn77/about_fts/el_usl/')):
                            self.urls.add(full_url)
                except Exception as e:
                    continue
            
            new_count = len(self.urls) - initial_count
            logger.info(f"Найдено новых ссылок для '{tab_name}': {new_count}")
            logger.info(f"Всего уникальных ссылок: {len(self.urls)}")
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге таба '{tab_name}': {e}")




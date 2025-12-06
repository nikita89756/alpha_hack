from playwright.sync_api import sync_playwright
import time
import logging
import os
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

stock_urls = [
    "https://alfabank.ru/sme/start/", 
    "https://alfabank.ru/sme/raschetnyj-schet/", 
    "https://alfabank.ru/sme/profits-new/", 
    "https://alfabank.ru/sme/payservice/", 
    "https://alfabank.ru/sme/cards/", 
    "https://alfabank.ru/sme/deposits/online/", 
    "https://alfabank.ru/sme/ved/", 
    "https://alfabank.ru/sme/loyalty/"
    ]

class AlfaBankSMEParser:
    def __init__(self) -> None:
        self.url = "https://alfabank.ru/sme/"
        self.is_docker = os.getenv('AIRFLOW_HOME') is not None or os.getenv('DISPLAY') is None
    
    def parse_cards(self) -> List[str]:
        """Парсинг карточек с ссылками со страницы SME. Возвращает список URL."""
        urls = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.is_docker,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            
            try:
                page.goto(self.url, wait_until='networkidle', timeout=60000)
                time.sleep(5)
                
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(2)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                
                link_selectors = [
                    "#alfa > div > div:nth-child(1) > div > div.aSfUAb.sSfUAb.aQWkTE.kQWkTE.jQWkTE.iQWkTE.avQWkTE > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(1) > div > a",
                    "#alfa > div > div:nth-child(1) > div > div.aSfUAb.sSfUAb.aQWkTE.kQWkTE.jQWkTE.iQWkTE.avQWkTE > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(2) > div > a",
                    "#alfa > div > div:nth-child(1) > div > div.aSfUAb.sSfUAb.aQWkTE.kQWkTE.jQWkTE.iQWkTE.avQWkTE > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(3) > div > a",
                    "#alfa > div > div:nth-child(1) > div > div.aSfUAb.sSfUAb.aQWkTE.kQWkTE.jQWkTE.iQWkTE.avQWkTE > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(4) > div > a",
                    "#alfa > div > div:nth-child(1) > div > div.aSfUAb.sSfUAb.aQWkTE.kQWkTE.jQWkTE.iQWkTE.avQWkTE > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(1) > div > div.aUl5hC.fUl5hC.uQWkTE > div:nth-child(1) > div > a",
                    "#alfa > div > div:nth-child(1) > div > div.aSfUAb.sSfUAb.aQWkTE.kQWkTE.jQWkTE.iQWkTE.avQWkTE > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(1) > div > div.aUl5hC.fUl5hC.uQWkTE > div:nth-child(2) > div > a",
                    "#alfa > div > div:nth-child(1) > div > div.aSfUAb.sSfUAb.aQWkTE.kQWkTE.jQWkTE.iQWkTE.avQWkTE > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(1) > div > div.aUl5hC.fUl5hC.uQWkTE > div:nth-child(3) > div > a",
                    "#alfa > div > div:nth-child(1) > div > div.aSfUAb.sSfUAb.aQWkTE.kQWkTE.jQWkTE.iQWkTE.avQWkTE > div:nth-child(1) > div > div:nth-child(2) > div:nth-child(1) > div > div.aUl5hC.fUl5hC.uQWkTE > div:nth-child(4) > div > a"
                ]
                
                for selector in link_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            href = element.get_attribute('href')
                            if href:
                                if href.startswith('/'):
                                    href = f"https://alfabank.ru{href}"
                                urls.append(href)
                    except:
                        pass
                
                all_links = page.query_selector_all('a.aR7Oy1.dR7Oy1.uR7Oy1.RR7Oy1.qR7Oy1.pQWkTE.RQWkTE')
                
                for link in all_links:
                    try:
                        href = link.get_attribute('href')
                        if href:
                            if href.startswith('/'):
                                href = f"https://alfabank.ru{href}"
                            if href not in urls:
                                urls.append(href)
                    except:
                        pass
                
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                
            finally:
                browser.close()
        
        return urls

def check_urls() -> bool:
    parser = AlfaBankSMEParser()
    urls = parser.parse_cards()
    parsed_set = set(urls)
    stock_set = set(stock_urls)
    return parsed_set == stock_set

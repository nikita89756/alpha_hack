from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
from typing import List
from pathlib import Path
from datetime import datetime
import os


class AlfaBankParser:
    
    def __init__(self) -> None:
        self.base_url = "https://alfabank.ru"
        self.is_docker = os.getenv('AIRFLOW_HOME') is not None or os.getenv('DISPLAY') is None
        if self.is_docker:
            self.debug_dir = Path("/opt/airflow/logs/parser_debug")
        else:
            self.debug_dir = Path(__file__).parent.parent.parent / "logs" / "parser_debug"
        self.debug_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_page_1_start(self) -> str:
        """Парсинг /sme/start/ - возвращает список текстовых блоков для RAG"""
        
        url = f"{self.base_url}/sme/start/"
        content_blocks = []
        
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
            
            page.goto(url, wait_until='networkidle', timeout=60000)
            time.sleep(5)
            
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            content_blocks.append(f"Источник: {url}")
            content_blocks.append("")
            
            h1 = soup.find('h1')
            if h1:
                content_blocks.append(f"УСЛУГА: {h1.get_text().strip()}")
                content_blocks.append("")
            
            offer_cards = soup.find_all('div', class_=lambda x: x and 'bcphvj' in str(x))[:2]
            
            for card in offer_cards:
                h3 = card.find('h3')
                paragraphs = card.find_all('p', class_=lambda x: x and 'aR7Oy1' in str(x))
                
                if h3:
                    content_blocks.append(f"Предложение: {h3.get_text().strip()}")
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text:
                            content_blocks.append(f"  - {text}")
                    content_blocks.append("")
            
            benefit_cards = soup.find_all('div', style=lambda x: x and '364px' in str(x) and '266px' in str(x))[:3]
            
            if benefit_cards:
                content_blocks.append("Преимущества:")
                for card in benefit_cards:
                    h3 = card.find('h3') or card.find('p', class_=lambda x: x and 'AR7Oy1' in str(x))
                    desc = card.find('p', class_=lambda x: x and 'VR7Oy1' in str(x))
                    
                    if h3:
                        title = h3.get_text().strip()
                        description = desc.get_text().strip() if desc else ""
                        content_blocks.append(f"  • {title}: {description}")
                content_blocks.append("")
            
            accordions = soup.find_all('div', attrs={'data-test-id': lambda x: x and 'accordion-item' in str(x)})
            
            if accordions:
                content_blocks.append("Часто задаваемые вопросы:")
                content_blocks.append("")
                
                for accordion in accordions[:10]:
                    question_elem = accordion.find('h3')
                    answer_panel = accordion.find_next_sibling('div', class_=lambda x: x and 'AyJgKm' in str(x))
                    if not answer_panel:
                        answer_panel = accordion.find('div', attrs={'data-test-id': lambda x: x and 'accordion-panel' in str(x)})
                    
                    if question_elem:
                        question = question_elem.get_text().strip()
                        answer = ""
                        
                        if answer_panel:
                            answer_texts = answer_panel.find_all('p', class_=lambda x: x and 'aR7Oy1' in str(x))
                            answer = ' '.join([p.get_text().strip() for p in answer_texts])
                        
                        if question and len(question) > 3:
                            content_blocks.append(f"Вопрос: {question}")
                            content_blocks.append(f"Ответ: {answer}")
                            content_blocks.append("")
            
            browser.close()
            
            result = "\n".join(content_blocks)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = self.debug_dir / f"alfabank_page1_start_{timestamp}.txt"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"[DEBUG] Сохранён результат парсинга page 1: {debug_file}")
            
            return result

    def parse_page_2_raschetnyj_schet(self) -> str:
        """Парсинг /sme/raschetnyj-schet/ - возвращает список текстовых блоков для RAG"""
        
        url = f"{self.base_url}/sme/raschetnyj-schet/"
        content_blocks = []
        
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
            
            page.goto(url, wait_until='networkidle', timeout=60000)
            time.sleep(5)
            
            for i in range(4):
                page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/4})")
            time.sleep(2)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            content_blocks.append(f"Источник: {url}")
            content_blocks.append("")
            
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text().strip()
                content_blocks.append(f"УСЛУГА: {title}")
                
                subtitle_p = h1.find_next('p')
                if subtitle_p:
                    content_blocks.append(f"Подзаголовок: {subtitle_p.get_text().strip()}")
                content_blocks.append("")
            
            h1_section = soup.find('h1')
            if h1_section:
                parent = h1_section.find_parent('div')
                if parent:
                    offer_cards = parent.find_all('div', class_=lambda x: x and 'bcphvj' in str(x))[:2]
                    for card in offer_cards:
                        h2 = card.find('h2')
                        if h2:
                            content_blocks.append(f"Предложение: {h2.get_text().strip()}")
                            features = card.find_all('p', class_=lambda x: x and 'VR7Oy1' in str(x))
                            for f in features:
                                text = f.get_text().strip()
                                if text:
                                    content_blocks.append(f"- {text}")
                            content_blocks.append("")
            
            all_divs = soup.find_all('div', style=lambda x: x and 'blur(12px)' in str(x) and '178px' in str(x))
            
            if all_divs:
                content_blocks.append("Преимущества:")
                for card in all_divs[:4]:
                    title = card.find('p', class_=lambda x: x and 'yR7Oy1' in str(x) and 'MR7Oy1' in str(x))
                if title:
                        title_text = title.get_text().strip()
                        desc_text = ""
                        
                        desc_p = card.find('p', class_=lambda x: x and 'xR7Oy1' in str(x))
                        if desc_p:
                            desc_text = desc_p.get_text().strip()
                        
                        if not desc_text:
                            tooltip_div = card.find('div', class_=lambda x: x and 'xR7Oy1' in str(x))
                            if tooltip_div:
                                span = tooltip_div.find('span', class_=lambda x: x and 'aXYDeT' in str(x))
                                if span:
                                    desc_text = span.get_text().strip()
                        
                        content_blocks.append(f"• {title_text}: {desc_text}")
                content_blocks.append("")
            
            content_blocks.append("Тарифы на расчётный счёт:")
            content_blocks.append("")
            
            tariff_map = [
                ('Нулевой', 'nullforservice'),
                ('Простой', 'simple'),
                ('Быстрый рост', 'fastgrowth'),
                ('Активные операции', 'activetransactions')
            ]
            
            for name, url_part in tariff_map:
                link = soup.find('a', href=lambda x: x and url_part in str(x))
                if link:
                    card = link.find('div', class_=lambda x: x and 'bcphvj' in str(x))
                    if card:
                        h3 = card.find('h3')
                        desc = card.find('p', class_=lambda x: x and 'VR7Oy1' in str(x))
                        price = card.find('p', class_=lambda x: x and ('DR7Oy1' in str(x) or 'cR7Oy1' in str(x)))
                        
                        tariff_name = h3.get_text().strip() if h3 else name
                        tariff_desc = desc.get_text().strip() if desc else ""
                        tariff_price = price.get_text().strip() if price else ""
                        
                        content_blocks.append(f"Тариф: {tariff_name}")
                        content_blocks.append(f"Описание: {tariff_desc}")
                        content_blocks.append(f"Стоимость: {tariff_price}")
                        content_blocks.append("")
            
            eight_options_section = soup.find('h2', string=lambda x: x and '8' in str(x) and 'бесплатн' in str(x).lower())
            if eight_options_section:
                content_blocks.append(eight_options_section.get_text().strip())
                ul = eight_options_section.find_next('ul')
                if ul:
                    items = ul.find_all('li')
                    for li in items:
                        content_blocks.append(f"• {li.get_text().strip()}")
                content_blocks.append("")
            
            content_blocks.append("Подробные условия по тарифам:")
            content_blocks.append("")
            
            more_section = soup.find('div', id='more')
            if more_section:
                tariff_names = []
                tabs = more_section.find_all('div', role='tab')
                for tab in tabs:
                    text_elem = tab.find('text')
                    if text_elem:
                        tariff_names.append(text_elem.get_text().strip())
                
                all_tables = more_section.find_all('table', class_=lambda x: x and 'aHLYAJ' in str(x))
                
                for idx, table in enumerate(all_tables[:4], 1):
                    tariff_name = tariff_names[idx-1] if idx-1 < len(tariff_names) else f"Тариф {idx}"
                    content_blocks.append(f"Тариф '{tariff_name}':")
                    
                    rows = table.find_all('tr', class_=lambda x: x and 'fHL9Sw' in str(x))
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            param = cells[0].get_text().strip()
                            
                            value_parts = []
                            for p in cells[1].find_all('p', recursive=True):
                                p_text = p.get_text().strip()
                                if p_text:
                                    value_parts.append(p_text)
                            
                            value = ' / '.join(value_parts) if value_parts else cells[1].get_text().strip()
                            
                            if param and value:
                                content_blocks.append(f"• {param}: {value}")
                    
                    content_blocks.append("")
            
            all_h3 = soup.find_all('h3')
            step_keywords = ['заявк', 'документ', 'готов', 'открыт', 'подпиш']
            steps = []
            
            for h3 in all_h3:
                text = h3.get_text().strip()
                if text and any(kw in text.lower() for kw in step_keywords):
                    if len(steps) < 3 and text not in steps:
                        steps.append(text)
            
            if steps:
                content_blocks.append("Как открыть счёт:")
                for idx, step in enumerate(steps, 1):
                    content_blocks.append(f"{idx}. {step}")
                content_blocks.append("")
            
            why_section = soup.find('h2', string=lambda x: x and 'Почему' in str(x) and 'Альфа' in str(x))
            if why_section:
                content_blocks.append(why_section.get_text().strip())
                cards = why_section.find_next('div').find_all('div', class_=lambda x: x and 'bcphvj' in str(x))[:3]
                for card in cards:
                    h3 = card.find('h3')
                    desc = card.find('p', class_=lambda x: x and 'VR7Oy1' in str(x))
                    if h3:
                        title = h3.get_text().strip()
                        description = desc.get_text().strip() if desc else ""
                        content_blocks.append(f"• {title}: {description}")
                content_blocks.append("")
            
            bonus_cards = soup.find_all('div', class_=lambda x: x and 'lcphvj' in str(x))
            bonuses_found = []
            
            for card in bonus_cards:
                title_elem = card.find('p', class_=lambda x: x and 'AR7Oy1' in str(x) and 'MR7Oy1' in str(x))
                if title_elem:
                    title = title_elem.get_text().strip()
                    
                    if any(skip in title.lower() for skip in ['тариф', 'эквайринг', 'индикатор', 'бухгалтер', 'интернет-банк', 'сервис']):
                        continue
                    
                    if title not in bonuses_found:
                        desc = card.find('p', class_=lambda x: x and 'VR7Oy1' in str(x))
                        description = desc.get_text().strip() if desc else ""
                        bonuses_found.append(title)
                        
                        if len(bonuses_found) == 1:
                            content_blocks.append("Бонусы:")
                        
                        content_blocks.append(f"• {title}: {description}")
                        
                        if len(bonuses_found) >= 7:
                            break
            
            if bonuses_found:
                content_blocks.append("")
            
            award_keywords = ['business one', 'кэшбэк', 'euromoney']
            for card in soup.find_all('div', class_=lambda x: x and 'lcphvj' in str(x)):
                h3 = card.find('h3')
                if h3:
                    text = h3.get_text().strip()
                    if any(kw in text.lower() for kw in award_keywords):
                        desc = card.find('p', class_=lambda x: x and 'VR7Oy1' in str(x))
                        description = desc.get_text().strip() if desc else ""
                        content_blocks.append(f"Награда: {text}")
                        if description:
                            content_blocks.append(f"{description}")
                        content_blocks.append("")
                        break
            
            services_heading = soup.find('h2', string=lambda x: x and 'Сервисы' in str(x) and 'бизнеса' in str(x))
            if services_heading:
                content_blocks.append(services_heading.get_text().strip())
                
                services_container = services_heading.find_parent('div', class_='bZO5Qa')
                
                if services_container:
                    service_links = services_container.find_all('a', class_=lambda x: x and 'aXYDeT' in str(x))
                    
                    for link in service_links:
                        card = link.find('div', class_=lambda x: x and 'lcphvj' in str(x))
                        if card:
                            h3 = card.find('h3')
                            desc_p = card.find('p', class_=lambda x: x and 'VR7Oy1' in str(x))
                            
                            if h3:
                                title = h3.get_text().strip()
                                description = desc_p.get_text().strip() if desc_p else ""
                                content_blocks.append(f"• {title}: {description}")
                
                content_blocks.append("")
            
            seo_section = soup.find('div', id='SEO')
            if seo_section:
                content_blocks.append("Дополнительная информация:")
                content_blocks.append("")
                
                for p in seo_section.find_all('p'):
                    text = p.get_text().strip()
                    if text and len(text) > 20:
                        content_blocks.append(text)
                        content_blocks.append("")
                
                for h2 in seo_section.find_all('h2'):
                    text = h2.get_text().strip()
                    if text:
                        content_blocks.append(text)
                
                for ul in seo_section.find_all('ul'):
                    for li in ul.find_all('li'):
                        li_text = li.get_text().strip()
                        if li_text:
                            content_blocks.append(f"• {li_text}")
                    content_blocks.append("")
            
            accordions = soup.find_all('div', attrs={'data-test-id': lambda x: x and 'accordion-item' in str(x)})[:15]
            faq_added = False
            
            for accordion in accordions:
                question_elem = accordion.find('h3')
                if question_elem:
                    question = question_elem.get_text().strip()
                    
                    if len(question) < 10:
                        continue
                    
                    answer = ""
                    answer_div = accordion.find_next_sibling('div')
                    if answer_div:
                        answer_paragraphs = answer_div.find_all('p', class_=lambda x: x and 'aR7Oy1' in str(x))
                        if answer_paragraphs:
                            answer = ' '.join([p.get_text().strip() for p in answer_paragraphs[:5] if p.get_text().strip()])
                    
                    if not answer:
                        answer_panel = accordion.find('div', class_=lambda x: x and 'AyJgKm' in str(x))
                        if answer_panel:
                            answer_paragraphs = answer_panel.find_all('p')
                            answer = ' '.join([p.get_text().strip() for p in answer_paragraphs if p.get_text().strip()])
                    
                    if question:
                        if not faq_added:
                            content_blocks.append("Часто задаваемые вопросы:")
                            content_blocks.append("")
                            faq_added = True
                        
                        content_blocks.append(f"Вопрос: {question}")
                        content_blocks.append(f"Ответ: {answer}")
                        content_blocks.append("")
            
            browser.close()
            
            result = "\n".join(content_blocks)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = self.debug_dir / f"alfabank_page2_raschetnyj_schet_{timestamp}.txt"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"[DEBUG] Сохранён результат парсинга page 2: {debug_file}")
            
            return result




from openai import OpenAI
import os
import logging
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

api_key = os.getenv("OPENROUTER_API_KEY", "")


class LLMClient:
    """Клиент для работы с LLM API"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
            
        )
        self.model = "google/gemma-3-12b-it"
        logger.info("Инициализирован LLM клиент")
    
    def get_completion(self, messages: list, temperature: float = 0.3, max_tokens: int = 100) -> str:
        """
        Получить ответ от LLM
        
        Args:
            messages: Список сообщений для чата
            temperature: Температура генерации (0-1)
            max_tokens: Максимальное количество токенов
            
        Returns:
            Текст ответа от модели
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=0.9,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Ошибка при обращении к LLM: {str(e)}")


class DocumentRelevanceChecker:
    """Проверка релевантности документа для темы микробизнеса"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    def check_relevance(self, title: str, source: str = "", category: str = "") -> bool:
        """
        Проверяет подходит ли документ под тему микробизнеса
        
        Args:
            title: Заголовок документа
            source: Источник документа
            category: Категория документа
            
        Returns:
            True если документ подходит, False если нет
        """
        
        system_prompt = """Ты - эксперт по анализу документов Центрального Банка РФ.

        Твоя задача: определить, относится ли документ к теме МИКРОБИЗНЕСА, малого бизнеса, ИП, самозанятых или фриланса.

        ПОДХОДЯТ документы о:
        - Малом и среднем бизнесе (МСП)
        - Индивидуальных предпринимателях (ИП)
        - Самозанятых
        - Микрокредитовании
        - Кредитах для малого бизнеса
        - Финансовой поддержке МСП
        - Регулировании малого бизнеса

        НЕ ПОДХОДЯТ документы о:
        - Крупных корпорациях и банках
        - Макроэкономике в целом
        - Валютном регулировании (если не касается МСП)
        - Общих статистических обзорах
        - Международных резервах
        - Межбанковском кредитовании

        Ответь ТОЛЬКО одним словом: "ДА" или "НЕТ"."""

        user_prompt = f"""Заголовок: {title}
        Источник: {source}
        Категория: {category}

        Относится ли к микробизнесу?"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.llm_client.get_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=10
            )
            
            response = response.strip().upper()
            is_relevant = response == "ДА" or response == "YES" or response.startswith("ДА")
            
            logger.info(f"Проверка релевантности '{title[:50]}...': {is_relevant}")
            return is_relevant
            
        except Exception as e:
            logger.error(f"Ошибка при проверке релевантности: {e}")
            return False
    
    def check_relevance_batch(self, titles: List[str], source: str = "", category: str = "") -> Optional[List[int]]:
        """
        Проверяет список титульников (до 10 штук) и возвращает индексы подходящих
        
        Args:
            titles: Список заголовков документов (максимум 10)
            source: Источник документов
            category: Категория документов
            
        Returns:
            Список индексов подходящих титульников (0-based) или None если ни один не подходит
        """
        if not titles:
            return None
        
        titles_to_check = titles[:10]
        
        system_prompt = """Ты - эксперт по анализу документов.

Твоя задача: определить, какие из предложенных документов относятся к теме МИКРОБИЗНЕСА, малого бизнеса, ИП, самозанятых или фриланса.

ПОДХОДЯТ документы о:
- Малом и среднем бизнесе (МСП)
- Индивидуальных предпринимателях (ИП)
- Самозанятых
- Микрокредитовании
- Кредитах для малого бизнеса
- Финансовой поддержке МСП
- Регулировании малого бизнеса

НЕ ПОДХОДЯТ документы о:
- Крупных корпорациях и банках
- Макроэкономике в целом
- Валютном регулировании (если не касается МСП)
- Общих статистических обзорах
- Международных резервах
- Межбанковском кредитовании

Ответь ТОЛЬКО номерами подходящих документов через запятую (например: 1,3,5) или словом "НЕТ" если ни один не подходит.
Нумерация начинается с 1."""

        titles_text = "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles_to_check)])
        
        user_prompt = f"""Заголовки документов:
{titles_text}

Источник: {source}
Категория: {category}

Какие документы относятся к микробизнесу? Укажи номера через запятую или "НЕТ"."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.llm_client.get_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=50
            )
            
            response = response.strip().upper()
            
            if "НЕТ" in response or "НЕТ" == response or "NONE" in response:
                logger.info(f"Проверка батча: ни один документ не подходит")
                return None
            
            indices = []
            parts = response.split(',')
            for part in parts:
                part = part.strip()
                try:
                    num = int(part)
                    if 1 <= num <= len(titles_to_check):
                        indices.append(num - 1)
                except ValueError:
                    continue
            
            if not indices:
                logger.info(f"Проверка батча: не удалось распарсить ответ '{response}'")
                return None
            
            logger.info(f"Проверка батча ({len(titles_to_check)} титульников): подходит {len(indices)}")
            return indices
            
        except Exception as e:
            logger.error(f"Ошибка при проверке релевантности батча: {e}")
            return None




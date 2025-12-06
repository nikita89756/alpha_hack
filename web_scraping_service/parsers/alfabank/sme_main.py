from sme_check import check_urls
from sme import AlfaBankParser
from typing import List

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

def main() -> List[str]:
    """
    Основная функция парсинга страниц Альфа-Банка.
    Возвращает список из двух текстовых блоков, по одному на каждую страницу.
    """
    if check_urls():
        parser = AlfaBankParser()
        text_1 = parser.parse_page_1_start()
        text_2 = parser.parse_page_2_raschetnyj_schet()
        
        return [text_1, text_2]
    else:
        return []

if __name__ == "__main__":
    main()
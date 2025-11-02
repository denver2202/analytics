"""
Парсер продукции с сайта niir.ru
Извлекает товары, категории и их характеристики
"""
import time
import json
import requests
from selectolax.parser import HTMLParser
from loguru import logger
from typing import List, Dict, Optional
from urllib.parse import urljoin

from ..config import SCRAPE_BASE_URL, REQUESTS_TIMEOUT, REQUESTS_SLEEP_BETWEEN, USER_AGENT


class ProductScraper:
    """Парсер товаров с сайта предприятия"""
    
    def __init__(self):
        self.base_url = SCRAPE_BASE_URL or "https://www.jsc-niir.ru"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
    
    def get_page(self, url: str) -> Optional[HTMLParser]:
        """Получить HTML страницы"""
        try:
            response = self.session.get(url, timeout=REQUESTS_TIMEOUT)
            response.raise_for_status()
            return HTMLParser(response.text)
        except Exception as e:
            logger.error(f"Ошибка при запросе {url}: {e}")
            return None
    
    def extract_products_from_page(self, html: HTMLParser) -> List[Dict]:
        """Извлечь товары со страницы каталога"""
        products = []
        
        # Ищем карточки товаров (структура может отличаться, нужно адаптировать под реальный HTML)
        # Типичные селекторы для карточек товаров
        product_cards = html.css("div.product-item, div.product-card, article.product, .product")
        
        if not product_cards:
            # Альтернативные селекторы
            product_cards = html.css("a.product-link, .goods-item")
        
        for card in product_cards:
            try:
                product_data = self._extract_product_data(card)
                if product_data:
                    products.append(product_data)
            except Exception as e:
                logger.warning(f"Ошибка при парсинге карточки товара: {e}")
        
        return products
    
    def _extract_product_data(self, card) -> Optional[Dict]:
        """Извлечь данные одного товара"""
        try:
            # Название товара
            name_elem = card.css_first("h2, h3, .product-title, .goods-title, a")
            name = name_elem.text(strip=True) if name_elem else None
            
            # Ссылка на товар
            link_elem = card.css_first("a")
            url = None
            if link_elem:
                href = link_elem.attributes.get("href")
                if href:
                    url = urljoin(self.base_url, href)
            
            # SKU/артикул (если есть)
            sku = None
            sku_elem = card.css_first(".sku, .article, .articul, [data-sku]")
            if sku_elem:
                sku = sku_elem.text(strip=True) or sku_elem.attributes.get("data-sku")
            
            # Категория
            category = None
            category_elem = card.css_first(".category, .product-category, .breadcrumb-item")
            if category_elem:
                category = category_elem.text(strip=True)
            
            if not name:
                return None
            
            return {
                "name": name,
                "sku": sku or self._generate_sku(name),
                "category": category,
                "url": url
            }
        except Exception as e:
            logger.error(f"Ошибка извлечения данных товара: {e}")
            return None
    
    def _generate_sku(self, name: str) -> str:
        """Генерировать SKU из названия"""
        # Простая генерация SKU из названия
        import hashlib
        return hashlib.md5(name.encode()).hexdigest()[:12]
    
    def extract_product_details(self, product_url: str) -> Dict:
        """Извлечь детальную информацию о товаре со страницы товара"""
        html = self.get_page(product_url)
        if not html:
            return {}
        
        details = {}
        
        # Извлечение характеристик (для шин - тип протектора, размер и т.д.)
        specs = {}
        spec_items = html.css(".spec-item, .characteristic, .param-item, tr")
        
        for item in spec_items:
            try:
                key_elem = item.css_first("dt, .spec-name, .param-name, td:first-child")
                value_elem = item.css_first("dd, .spec-value, .param-value, td:last-child")
                
                if key_elem and value_elem:
                    key = key_elem.text(strip=True).lower()
                    value = value_elem.text(strip=True)
                    if key and value:
                        specs[key] = value
            except Exception:
                continue
        
        # Сохраняем характеристики в JSON формате
        details["specifications"] = json.dumps(specs, ensure_ascii=False) if specs else None
        
        # Извлечение типа протектора для шин
        tread_pattern = self._extract_tread_pattern(specs, html)
        if tread_pattern:
            details["tread_pattern"] = tread_pattern
        
        # Цена (если есть)
        price_elem = html.css_first(".price, .product-price, [data-price]")
        if price_elem:
            price_text = price_elem.text(strip=True) or price_elem.attributes.get("data-price", "")
            try:
                # Извлечь число из текста цены
                import re
                price_match = re.search(r'[\d\s]+', price_text.replace(" ", ""))
                if price_match:
                    details["price"] = float(price_match.group().replace(" ", ""))
            except Exception:
                pass
        
        return details
    
    def _extract_tread_pattern(self, specs: Dict, html: HTMLParser) -> Optional[str]:
        """Извлечь тип протектора для шин"""
        # Поиск в характеристиках
        pattern_keywords = {
            "протектор": ["протектор", "tread", "pattern"],
            "зимние": ["зимн", "winter", "snow"],
            "летние": ["летн", "summer"],
            "всесезонные": ["всесезон", "all-season", "all-weather"],
            "дорожные": ["дорожн", "highway"],
            "внедорожные": ["внедорожн", "off-road", "mud"]
        }
        
        # Проверяем характеристики
        for key, value in specs.items():
            value_lower = value.lower()
            for pattern, keywords in pattern_keywords.items():
                if any(kw in value_lower or kw in key.lower() for kw in keywords):
                    return pattern
        
        # Проверяем описание товара
        desc_elem = html.css_first(".description, .product-description, .content")
        if desc_elem:
            desc_text = desc_elem.text().lower()
            for pattern, keywords in pattern_keywords.items():
                if any(kw in desc_text for kw in keywords):
                    return pattern
        
        return None
    
    def scrape_catalog(self, category_url: Optional[str] = None, max_pages: int = 10) -> List[Dict]:
        """Спарсить каталог товаров"""
        products = []
        
        if not category_url:
            category_url = f"{self.base_url}/produkciya-2/"
        
        page_num = 1
        while page_num <= max_pages:
            page_url = f"{category_url}?page={page_num}" if page_num > 1 else category_url
            logger.info(f"Парсинг страницы {page_num}: {page_url}")
            
            html = self.get_page(page_url)
            if not html:
                break
            
            page_products = self.extract_products_from_page(html)
            if not page_products:
                logger.info(f"Товары не найдены на странице {page_num}, остановка")
                break
            
            # Для каждого товара получаем детали (опционально, можно выключить для ускорения)
            for product in page_products:
                if product.get("url"):
                    try:
                        details = self.extract_product_details(product["url"])
                        product.update(details)
                        time.sleep(REQUESTS_SLEEP_BETWEEN)
                    except Exception as e:
                        logger.warning(f"Не удалось получить детали для {product['url']}: {e}")
            
            products.extend(page_products)
            page_num += 1
            time.sleep(REQUESTS_SLEEP_BETWEEN)
        
        logger.info(f"Найдено товаров: {len(products)}")
        return products


def scrape_products(category_url: Optional[str] = None, max_pages: int = 10) -> List[Dict]:
    """Основная функция для парсинга товаров"""
    scraper = ProductScraper()
    return scraper.scrape_catalog(category_url, max_pages)


if __name__ == "__main__":
    # Тестовый запуск
    products = scrape_products(max_pages=2)
    print(f"Найдено товаров: {len(products)}")
    for p in products[:3]:
        print(f"- {p.get('name')} ({p.get('category')})")


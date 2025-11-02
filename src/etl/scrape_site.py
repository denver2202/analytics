"""
Парсер продукции с сайта niir.ru
Извлекает товары, категории и их характеристики
"""
import time
import json
import requests
from loguru import logger
from typing import List, Dict, Optional
from urllib.parse import urljoin

# Пробуем использовать selectolax, если не работает - используем BeautifulSoup
try:
    from selectolax.parser import HTMLParser
    USE_SELECTOLAX = True
except (ImportError, SystemError, OSError):
    try:
        from bs4 import BeautifulSoup
        USE_SELECTOLAX = False
        logger.info("Используется BeautifulSoup вместо selectolax")
    except ImportError:
        raise ImportError("Необходим selectolax или beautifulsoup4")

from ..config import SCRAPE_BASE_URL, REQUESTS_TIMEOUT, REQUESTS_SLEEP_BETWEEN, USER_AGENT


class ProductScraper:
    """Парсер товаров с сайта предприятия"""
    
    def __init__(self):
        base = SCRAPE_BASE_URL or "https://www.jsc-niir.ru"
        # Нормализуем base_url - оставляем только домен, без пути
        if base.startswith("http"):
            # Извлекаем только домен
            from urllib.parse import urlparse
            parsed = urlparse(base)
            base = f"{parsed.scheme}://{parsed.netloc}"
        # Убираем лишние слэши
        if base.endswith("/"):
            base = base.rstrip("/")
        self.base_url = base
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
    
    def get_page(self, url: str):
        """Получить HTML страницы"""
        try:
            response = self.session.get(url, timeout=REQUESTS_TIMEOUT)
            response.raise_for_status()
            
            if USE_SELECTOLAX:
                try:
                    return HTMLParser(response.text)
                except (SystemError, OSError, MemoryError) as e:
                    logger.warning(f"selectolax вызвал ошибку, переключаюсь на BeautifulSoup: {e}")
                    from bs4 import BeautifulSoup
                    return BeautifulSoup(response.text, 'html.parser')
            else:
                from bs4 import BeautifulSoup
                return BeautifulSoup(response.text, 'html.parser')
                
        except Exception as e:
            logger.error(f"Ошибка при запросе {url}: {e}")
            return None
    
    def extract_products_from_page(self, html: HTMLParser) -> List[Dict]:
        """Извлечь товары со страницы каталога"""
        products = []
        
        # Для страницы шин: ищем товары по разным селекторам
        # Структура сайта: товары в блоках с названиями и ссылками "Подробнее"
        
        # Вариант 1: Ищем ссылки "Подробнее" и берем предыдущий элемент с названием
        detail_links = html.css('a[href*="shini"], a:contains("Подробнее"), a[href*="product"]')
        
        # Вариант 2: Ищем заголовки разделов (h2) и следующие за ними товары
        sections = html.css("h2, h3")
        current_category = None
        
        # Вариант 3: Ищем все ссылки и фильтруем по контексту
        all_links = html.css("a")
        
        # Вариант 4: Ищем по структуре страницы - товары в списках/блоках
        # Попробуем найти блоки с товарами через контекст
        product_blocks = []
        
        # Ищем в секциях (для страницы шин структура может быть в div или списках)
        if USE_SELECTOLAX and hasattr(html, 'css'):
            content_blocks = html.css("div, section, article, li")
        else:
            # BeautifulSoup
            content_blocks = html.find_all(["div", "section", "article", "li"])
        
        for block in content_blocks:
            # Ищем блоки, которые содержат название товара (например, "К-83А") и ссылку
            if USE_SELECTOLAX and hasattr(block, 'text'):
                text = block.text(strip=True)
                links = block.css("a")
            else:
                # BeautifulSoup
                text = block.get_text(strip=True) if hasattr(block, 'get_text') else ""
                links = block.find_all("a") if hasattr(block, 'find_all') else []
            
            # Если в блоке есть ссылка и текст похож на название шины
            if links and text:
                # Проверяем, не является ли это товаром (содержит артикул/модель)
                # Названия шин обычно содержат тире, цифры, буквы (например "К-83А 420/70-457")
                import re
                tire_pattern = r'[КМ]-\d+[А-Я]?\s+\d+[/-]\d+[A-Z]?\d*|КИ-\d+'
                if re.search(tire_pattern, text) or any(char in text for char in ['/', 'R', '-']) and len(text) < 100:
                    # Это похоже на товар
                    product_blocks.append(block)
        
        # Если нашли блоки через паттерн, обрабатываем их
        if product_blocks:
            for block in product_blocks:
                try:
                    product_data = self._extract_product_from_block(block)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    logger.debug(f"Ошибка при парсинге блока: {e}")
        
        # Если ничего не нашли, пробуем альтернативный метод - ищем все ссылки и их контекст
        if not products:
            logger.debug("Пробуем альтернативный метод парсинга через ссылки")
            products = self._extract_from_links(html)
        
        # Удаляем дубликаты
        seen = set()
        unique_products = []
        for p in products:
            key = (p.get("name"), p.get("sku"))
            if key not in seen:
                seen.add(key)
                unique_products.append(p)
        
        return unique_products
    
    def _extract_from_links(self, html) -> List[Dict]:
        """Альтернативный метод: извлечение товаров из ссылок"""
        import re
        products = []
        
        # Ищем все ссылки
        if USE_SELECTOLAX and hasattr(html, 'css'):
            links = html.css("a")
            headings = html.css("h1, h2, h3")
        else:
            # BeautifulSoup
            links = html.find_all("a")
            headings = html.find_all(["h1", "h2", "h3"])
        
        current_category = None
        
        # Сначала определяем категории по заголовкам
        for heading in headings:
            if USE_SELECTOLAX and hasattr(heading, 'text'):
                text = heading.text(strip=True)
            else:
                text = heading.get_text(strip=True) if hasattr(heading, 'get_text') else ""
            if "грузов" in text.lower() and "легко" not in text.lower():
                current_category = "Грузовые шины"
            elif "легко" in text.lower():
                current_category = "Легко Грузовые шины"
        
        # Обрабатываем ссылки
        for link in links:
            try:
                if USE_SELECTOLAX and hasattr(link, 'attributes'):
                    href = link.attributes.get("href", "")
                    link_text = link.text(strip=True)
                    parent = link.parent
                else:
                    # BeautifulSoup
                    href = link.get("href", "")
                    link_text = link.get_text(strip=True)
                    parent = link.parent if hasattr(link, 'parent') else None
                if not parent:
                    continue
                
                # Получаем полный текст родительского элемента
                if parent:
                    if USE_SELECTOLAX and hasattr(parent, 'text'):
                        parent_text = parent.text(strip=True)
                    else:
                        parent_text = parent.get_text(strip=True) if hasattr(parent, 'get_text') else ""
                else:
                    parent_text = ""
                
                # Ищем паттерн названия шины (например: "К-83А 420/70-457" или "КИ-115АМ (САДКО) 12R18")
                tire_pattern = r'(К-?\d+[А-Яа-я]?|КИ-?\d+[А-Яа-яА-Яа-я]*)\s*\(?[А-Яа-я]*\)?\s*(\d+[/-]\d+[A-Z]?\d*|\d+R\d+)'
                
                # Если ссылка содержит "Подробнее" или ссылка ведет на страницу товара
                if "Подробнее" in link_text or "подробнее" in link_text.lower() or "shini" in href:
                    # Берем текст перед ссылкой или весь текст родителя
                    if "Подробнее" in parent_text:
                        # Разделяем по "Подробнее" и берем первую часть
                        name_part = parent_text.split("Подробнее")[0].strip()
                        # Убираем лишние пробелы и переносы строк
                        name_part = re.sub(r'\s+', ' ', name_part)
                    else:
                        # Пробуем найти название в родителе
                        name_part = parent_text.strip()
                        # Убираем "Подробнее" если есть
                        name_part = re.sub(r'\s*Подробнее.*', '', name_part, flags=re.IGNORECASE)
                    
                    # Извлекаем название товара (первая строка с паттерном)
                    if name_part and len(name_part) > 3:
                        # Ищем паттерн шины в тексте
                        match = re.search(tire_pattern, name_part)
                        if match:
                            # Берем найденную часть как название
                            name = match.group(0).strip()
                            
                            # Определяем категорию
                            category = current_category or "Шины"
                            parent_lower = parent_text.lower()
                            if "грузов" in parent_lower and "легко" not in parent_lower:
                                category = "Грузовые шины"
                            elif "легко" in parent_lower:
                                category = "Легко Грузовые шины"
                            
                            # Формируем URL
                            if href.startswith("/"):
                                url = urljoin(self.base_url, href)
                            elif href.startswith("http"):
                                url = href
                            else:
                                url = urljoin(self.base_url, "/" + href)
                            
                            products.append({
                                "name": name,
                                "sku": self._generate_sku(name),
                                "category": category,
                                "url": url,
                                "tread_pattern": None
                            })
            except Exception as e:
                logger.debug(f"Ошибка при обработке ссылки: {e}")
        
        return products
    
    def _extract_product_from_block(self, block) -> Optional[Dict]:
        """Извлечь товар из блока"""
        try:
            # Название товара
            name_elem = block.css_first("strong, b, h3, h4, a")
            if not name_elem:
                # Пробуем найти в тексте блока
                text = block.text(strip=True)
                # Извлекаем первую строку как название
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                name = lines[0] if lines else None
            else:
                name = name_elem.text(strip=True)
            
            if not name or len(name) < 3:
                return None
            
            # Ссылка
            link_elem = block.css_first("a")
            url = None
            if link_elem:
                href = link_elem.attributes.get("href")
                if href:
                    url = urljoin(self.base_url, href)
            
            # Категория - определяем по контексту (смотрим заголовки выше)
            category = "Шины"
            text_lower = block.text().lower()
            if "грузов" in text_lower and "легко" not in text_lower:
                category = "Грузовые шины"
            elif "легко" in text_lower or "легк" in text_lower:
                category = "Легко Грузовые шины"
            
            return {
                "name": name,
                "sku": self._generate_sku(name),
                "category": category,
                "url": url
            }
        except Exception as e:
            logger.debug(f"Ошибка извлечения из блока: {e}")
            return None
    
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
            # Если SCRAPE_BASE_URL уже содержит путь, используем его напрямую
            if SCRAPE_BASE_URL and SCRAPE_BASE_URL != "https://www.jsc-niir.ru":
                category_url = SCRAPE_BASE_URL
            else:
                category_url = f"{self.base_url}/produkciya-2/"
        
        # Нормализуем URL
        if not category_url.startswith("http"):
            if category_url.startswith("/"):
                category_url = f"{self.base_url}{category_url}"
            else:
                category_url = f"{self.base_url}/{category_url}"
        
        # Убираем лишние слэши и нормализуем
        category_url = category_url.rstrip("/")
        
        # Исправляем дублирование пути, если base_url уже содержит путь
        base_domain = "https://www.jsc-niir.ru"
        if self.base_url.startswith(base_domain):
            # Если base_url содержит путь
            base_path = self.base_url.replace(base_domain, "")
            if base_path:
                # Если category_url дублирует путь из base_url
                remaining = category_url.replace(self.base_url, "")
                if remaining.startswith(base_path):
                    # Убираем дублирование
                    category_url = self.base_url + remaining.replace(base_path, "", 1)
                elif category_url.startswith(self.base_url):
                    # Уже правильно сформирован
                    pass
                else:
                    # Если category_url - относительный путь
                    if not category_url.startswith("http"):
                        category_url = base_domain + "/" + category_url.lstrip("/")
        
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


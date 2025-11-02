"""
Безопасная версия парсера с использованием только BeautifulSoup
(для избежания segmentation fault с selectolax)
"""
import time
import json
import requests
from bs4 import BeautifulSoup
from loguru import logger
from typing import List, Dict, Optional
from urllib.parse import urljoin
import re

from ..config import SCRAPE_BASE_URL, REQUESTS_TIMEOUT, REQUESTS_SLEEP_BETWEEN, USER_AGENT


class ProductScraperSafe:
    """Безопасный парсер товаров с сайта предприятия (только BeautifulSoup)"""
    
    def __init__(self):
        base = SCRAPE_BASE_URL or "https://www.jsc-niir.ru"
        # Нормализуем base_url - оставляем только домен, без пути
        if base.startswith("http"):
            from urllib.parse import urlparse
            parsed = urlparse(base)
            base = f"{parsed.scheme}://{parsed.netloc}"
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
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logger.error(f"Ошибка при запросе {url}: {e}")
            return None
    
    def extract_products_from_page(self, html) -> List[Dict]:
        """Извлечь товары со страницы каталога"""
        if not html:
            return []
        
        products = []
        
        # Ищем все ссылки
        links = html.find_all("a")
        current_category = None
        
        # Определяем категории по заголовкам
        headings = html.find_all(["h1", "h2", "h3"])
        for heading in headings:
            text = heading.get_text(strip=True)
            if "грузов" in text.lower() and "легко" not in text.lower():
                current_category = "Грузовые шины"
            elif "легко" in text.lower():
                current_category = "Легко Грузовые шины"
        
        # Паттерн для названий шин
        tire_pattern = re.compile(r'(К-?\d+[А-Яа-я]?|КИ-?\d+[А-Яа-я]*)\s*\(?[А-Яа-я]*\)?\s*(\d+[/-]\d+[A-Z]?\d*|\d+R\d+)', re.IGNORECASE)
        
        for link in links:
            try:
                href = link.get("href", "")
                link_text = link.get_text(strip=True)
                
                # Получаем родительский элемент
                parent = link.parent
                if not parent:
                    continue
                
                parent_text = parent.get_text(strip=True)
                
                # Если ссылка содержит "Подробнее" или ведет на страницу товара
                if "Подробнее" in link_text or "подробнее" in link_text.lower() or "shini" in href:
                    # Извлекаем название
                    if "Подробнее" in parent_text:
                        name_part = parent_text.split("Подробнее")[0].strip()
                    else:
                        name_part = parent_text.strip()
                    
                    name_part = re.sub(r'\s+', ' ', name_part)
                    name_part = re.sub(r'\s*Подробнее.*', '', name_part, flags=re.IGNORECASE)
                    
                    if name_part and len(name_part) > 3:
                        # Ищем паттерн шины
                        match = tire_pattern.search(name_part)
                        if match:
                            name = match.group(0).strip()
                            
                            # Определяем категорию
                            category = current_category or "Шины"
                            parent_lower = parent_text.lower()
                            if "грузов" in parent_lower and "легко" not in parent_lower:
                                category = "Грузовые шины"
                            elif "легко" in parent_lower:
                                category = "Легко Грузовые шины"
                            
                            # URL
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
        
        # Удаляем дубликаты
        seen = set()
        unique_products = []
        for p in products:
            key = (p.get("name"), p.get("sku"))
            if key not in seen:
                seen.add(key)
                unique_products.append(p)
        
        return unique_products
    
    def _generate_sku(self, name: str) -> str:
        """Генерировать SKU из названия"""
        import hashlib
        return hashlib.md5(name.encode()).hexdigest()[:12]
    
    def scrape_catalog(self, category_url: Optional[str] = None, max_pages: int = 10) -> List[Dict]:
        """Спарсить каталог товаров"""
        products = []
        
        if not category_url:
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
        
        category_url = category_url.rstrip("/")
        
        # Исправляем дублирование пути
        base_domain = "https://www.jsc-niir.ru"
        if self.base_url.startswith(base_domain):
            base_path = self.base_url.replace(base_domain, "")
            if base_path:
                remaining = category_url.replace(self.base_url, "")
                if remaining.startswith(base_path):
                    category_url = self.base_url + remaining.replace(base_path, "", 1)
                elif not category_url.startswith("http"):
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
            
            products.extend(page_products)
            page_num += 1
            time.sleep(REQUESTS_SLEEP_BETWEEN)
        
        logger.info(f"Найдено товаров: {len(products)}")
        return products


def scrape_products_safe(category_url: Optional[str] = None, max_pages: int = 10) -> List[Dict]:
    """Безопасная функция для парсинга товаров (только BeautifulSoup)"""
    scraper = ProductScraperSafe()
    return scraper.scrape_catalog(category_url, max_pages)


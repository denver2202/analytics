"""
Простой тест парсера без Streamlit
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from loguru import logger
from src.etl.scrape_site import scrape_products
from src.etl.load_to_db import save_products

def test_scrape_tires():
    """Тест парсинга страницы шин"""
    logger.info("Тестирую парсер для страницы шин...")
    
    # Прямой URL к странице шин
    url = "https://www.jsc-niir.ru/produkciya-2/shini/"
    
    try:
        products = scrape_products(url, max_pages=1)
        logger.info(f"✓ Найдено товаров: {len(products)}")
        
        if products:
            print("\n" + "="*60)
            print("НАЙДЕННЫЕ ТОВАРЫ:")
            print("="*60)
            for i, p in enumerate(products, 1):
                print(f"\n{i}. {p.get('name')}")
                print(f"   Категория: {p.get('category', '-')}")
                print(f"   SKU: {p.get('sku', '-')}")
                if p.get('url'):
                    print(f"   URL: {p.get('url')[:70]}...")
            
            # Сохранение в БД (если настроено)
            try:
                saved = save_products(products)
                logger.info(f"✓ Сохранено в БД: {len(saved)} товаров")
            except Exception as e:
                logger.warning(f"Не удалось сохранить в БД: {e}")
                logger.info("(Это нормально, если БД не настроена)")
        else:
            logger.warning("Товары не найдены. Проверьте:")
            logger.info("1. Структура страницы могла измениться")
            logger.info("2. Нужно обновить селекторы в парсере")
            
    except Exception as e:
        logger.error(f"Ошибка при парсинге: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scrape_tires()


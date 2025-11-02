"""
Основной пайплайн для сбора данных и анализа спроса
"""
from datetime import date, timedelta
from loguru import logger

from .scrape_site import scrape_products
from .external.trends import collect_tire_trends
from .load_to_db import save_products, save_traffic_metrics


def run_data_collection_pipeline():
    """Запустить полный пайплайн сбора данных"""
    logger.info("=== Начало сбора данных ===")
    
    # 1. Парсинг продукции с сайта
    logger.info("Шаг 1: Парсинг продукции...")
    try:
        products = scrape_products(max_pages=5)  # Начать с 5 страниц для теста
        saved_products = save_products(products)
        logger.info(f"✓ Сохранено товаров: {len(saved_products)}")
    except Exception as e:
        logger.error(f"✗ Ошибка парсинга продукции: {e}")
        return False
    
    # 2. Сбор данных о трендах
    logger.info("Шаг 2: Сбор данных Google Trends...")
    try:
        trend_records = collect_tire_trends()
        saved_count = save_traffic_metrics(trend_records)
        logger.info(f"✓ Сохранено метрик трендов: {saved_count}")
    except Exception as e:
        logger.error(f"✗ Ошибка сбора трендов: {e}")
        return False
    
    logger.info("=== Сбор данных завершен ===")
    return True


if __name__ == "__main__":
    run_data_collection_pipeline()


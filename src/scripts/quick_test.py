"""
Быстрый тест без подключения к БД
"""
import sys
from loguru import logger

def test_imports():
    """Тест импортов"""
    logger.info("=== Тест импортов ===")
    
    try:
        from src.config import DATABASE_URL, SCRAPE_BASE_URL
        logger.info(f"✓ Config импортирован")
        logger.info(f"  DATABASE_URL: {'установлен' if DATABASE_URL else 'не установлен'}")
        logger.info(f"  SCRAPE_BASE_URL: {SCRAPE_BASE_URL}")
    except Exception as e:
        logger.error(f"✗ Ошибка импорта config: {e}")
        return False
    
    try:
        from src.db import Base, engine, SessionLocal
        logger.info(f"✓ DB модуль импортирован")
        logger.info(f"  Engine: {'создан' if engine else 'не создан'}")
        logger.info(f"  SessionLocal: {'создан' if SessionLocal else 'не создан'}")
    except Exception as e:
        logger.error(f"✗ Ошибка импорта db: {e}")
        return False
    
    try:
        from src.models import Product, TrafficMetric, Forecast
        logger.info(f"✓ Models импортированы")
    except Exception as e:
        logger.error(f"✗ Ошибка импорта models: {e}")
        return False
    
    try:
        from src.etl.scrape_site import ProductScraper
        logger.info(f"✓ Scraper импортирован")
    except Exception as e:
        logger.error(f"✗ Ошибка импорта scraper: {e}")
        return False
    
    try:
        from src.etl.external.trends import TrendsCollector
        logger.info(f"✓ Trends collector импортирован")
    except Exception as e:
        logger.error(f"✗ Ошибка импорта trends: {e}")
        return False
    
    try:
        from src.features.make_features import create_feature_vector
        logger.info(f"✓ Features модуль импортирован")
    except Exception as e:
        logger.error(f"✗ Ошибка импорта features: {e}")
        return False
    
    try:
        from src.modeling.train import train_demand_model
        logger.info(f"✓ Modeling модуль импортирован")
    except Exception as e:
        logger.error(f"✗ Ошибка импорта modeling: {e}")
        return False
    
    return True

def test_scraper_creation():
    """Тест создания парсера"""
    logger.info("\n=== Тест создания парсера ===")
    try:
        from src.etl.scrape_site import ProductScraper
        scraper = ProductScraper()
        logger.info(f"✓ Парсер создан успешно")
        logger.info(f"  Base URL: {scraper.base_url}")
        return True
    except Exception as e:
        logger.error(f"✗ Ошибка создания парсера: {e}")
        return False

def test_trends_creation():
    """Тест создания trends collector"""
    logger.info("\n=== Тест создания Trends Collector ===")
    try:
        from src.etl.external.trends import TrendsCollector
        collector = TrendsCollector()
        logger.info(f"✓ Trends Collector создан успешно")
        return True
    except Exception as e:
        logger.error(f"✗ Ошибка создания Trends Collector: {e}")
        return False

def main():
    """Основная функция"""
    logger.info("=" * 60)
    logger.info("БЫСТРЫЙ ТЕСТ БЕЗ ПОДКЛЮЧЕНИЯ К БД")
    logger.info("=" * 60)
    
    all_ok = True
    
    # Тест импортов
    if not test_imports():
        all_ok = False
    
    # Тест создания объектов
    if not test_scraper_creation():
        all_ok = False
    
    if not test_trends_creation():
        all_ok = False
    
    logger.info("\n" + "=" * 60)
    if all_ok:
        logger.info("✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        logger.info("\nДля полного теста с БД:")
        logger.info("1. Настройте DATABASE_URL в .env файле")
        logger.info("2. Примените миграции: alembic upgrade head")
        logger.info("3. Запустите: python -m src.scripts.test_pipeline")
    else:
        logger.error("✗ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        sys.exit(1)
    logger.info("=" * 60)

if __name__ == "__main__":
    main()


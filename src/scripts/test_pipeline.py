"""
Тестовый скрипт для проверки пайплайна без интерфейса
"""
from loguru import logger
from src.etl.scrape_site import scrape_products
from src.etl.external.trends import collect_tire_trends
from src.etl.load_to_db import save_products, save_traffic_metrics
from src.db import SessionLocal
from src.models import Product, TrafficMetric, Forecast
from src.modeling.train import train_demand_model
from src.modeling.forecast import get_tread_pattern_recommendations

def test_scraping():
    """Тест парсинга продукции"""
    logger.info("=== Тест парсинга продукции ===")
    try:
        products = scrape_products(max_pages=2)  # Парсим 2 страницы для теста
        logger.info(f"✓ Найдено товаров: {len(products)}")
        if products:
            logger.info(f"Пример: {products[0].get('name')}")
        return products
    except Exception as e:
        logger.error(f"✗ Ошибка: {e}")
        return []

def test_save_products(products):
    """Тест сохранения товаров"""
    logger.info("=== Тест сохранения товаров ===")
    try:
        saved = save_products(products)
        logger.info(f"✓ Сохранено товаров: {len(saved)}")
        return saved
    except Exception as e:
        logger.error(f"✗ Ошибка: {e}")
        return []

def test_trends():
    """Тест сбора трендов"""
    logger.info("=== Тест сбора трендов ===")
    try:
        trends = collect_tire_trends()
        logger.info(f"✓ Собрано записей трендов: {len(trends)}")
        if trends:
            logger.info(f"Пример: {trends[0]}")
        return trends
    except Exception as e:
        logger.error(f"✗ Ошибка: {e}")
        return []

def test_save_trends(trends):
    """Тест сохранения трендов"""
    logger.info("=== Тест сохранения трендов ===")
    try:
        saved = save_traffic_metrics(trends)
        logger.info(f"✓ Сохранено метрик: {saved}")
        return saved
    except Exception as e:
        logger.error(f"✗ Ошибка: {e}")
        return []

def test_db_stats():
    """Проверка статистики БД"""
    logger.info("=== Статистика БД ===")
    session = SessionLocal()
    try:
        products_count = session.query(Product).count()
        trends_count = session.query(TrafficMetric).count()
        forecasts_count = session.query(Forecast).count()
        
        logger.info(f"✓ Товаров в БД: {products_count}")
        logger.info(f"✓ Метрик трендов: {trends_count}")
        logger.info(f"✓ Прогнозов: {forecasts_count}")
        
        # Показываем примеры товаров
        products = session.query(Product).limit(5).all()
        if products:
            logger.info("\nПримеры товаров:")
            for p in products:
                logger.info(f"  - {p.name} ({p.category}, протектор: {p.tread_pattern or 'не указан'})")
        
        return {
            "products": products_count,
            "trends": trends_count,
            "forecasts": forecasts_count
        }
    finally:
        session.close()

def test_model():
    """Тест обучения модели"""
    logger.info("=== Тест обучения модели ===")
    try:
        model, metrics = train_demand_model()
        if model and metrics:
            logger.info(f"✓ Модель обучена")
            logger.info(f"  Test R2: {metrics.get('test_r2', 0):.3f}")
            logger.info(f"  Test MAE: {metrics.get('test_mae', 0):.3f}")
            
            # Показываем топ важных признаков
            if 'feature_importance' in metrics:
                importances = metrics['feature_importance']
                top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]
                logger.info("\nТоп-5 важных признаков:")
                for feature, importance in top_features:
                    logger.info(f"  - {feature}: {importance:.3f}")
        return model, metrics
    except Exception as e:
        logger.error(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None, {}

def test_recommendations():
    """Тест получения рекомендаций"""
    logger.info("=== Тест рекомендаций ===")
    try:
        recommendations = get_tread_pattern_recommendations()
        if not recommendations.empty:
            logger.info("✓ Рекомендации получены:")
            logger.info(f"\n{recommendations}")
        return recommendations
    except Exception as e:
        logger.error(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Основная функция тестирования"""
    logger.info("=" * 50)
    logger.info("ТЕСТИРОВАНИЕ ПАЙПЛАЙНА АНАЛИЗА СПРОСА")
    logger.info("=" * 50)
    
    # 1. Проверка БД
    stats = test_db_stats()
    print()
    
    # 2. Тест парсинга (опционально, раскомментировать для реального парсинга)
    # products = test_scraping()
    # if products:
    #     test_save_products(products)
    # print()
    
    # 3. Тест трендов (опционально, раскомментировать для реального запроса)
    # trends = test_trends()
    # if trends:
    #     test_save_trends(trends)
    # print()
    
    # 4. Проверка статистики после загрузки
    stats = test_db_stats()
    print()
    
    # 5. Тест модели (если есть данные)
    if stats['products'] > 0 and stats['trends'] > 0:
        test_model()
        print()
        test_recommendations()
    else:
        logger.warning("⚠ Недостаточно данных для обучения модели")
        logger.info("Сначала выполните:")
        logger.info("  1. Парсинг продукции: python -m src.etl.pipeline")
        logger.info("  2. Или вручную: python -m src.scripts.test_pipeline (раскомментировав соответствующие строки)")

if __name__ == "__main__":
    main()


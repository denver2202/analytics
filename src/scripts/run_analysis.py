"""
Полный цикл анализа: сбор данных -> обучение -> прогнозы
"""
from datetime import date, timedelta
from loguru import logger
from src.etl.pipeline import run_data_collection_pipeline
from src.modeling.train import train_demand_model, save_model
from src.modeling.forecast import generate_forecasts, get_tread_pattern_recommendations
from src.db import SessionLocal
from src.models import Product

def full_analysis_pipeline():
    """Запустить полный цикл анализа"""
    logger.info("=" * 60)
    logger.info("ПОЛНЫЙ ЦИКЛ АНАЛИЗА СПРОСА")
    logger.info("=" * 60)
    
    # Шаг 1: Сбор данных
    logger.info("\n[1/4] СБОР ДАННЫХ")
    logger.info("-" * 60)
    if run_data_collection_pipeline():
        logger.info("✓ Данные собраны успешно")
    else:
        logger.error("✗ Ошибка при сборе данных")
        return
    
    # Шаг 2: Обучение модели
    logger.info("\n[2/4] ОБУЧЕНИЕ МОДЕЛИ")
    logger.info("-" * 60)
    model, metrics = train_demand_model()
    if model:
        logger.info(f"✓ Модель обучена. Test R2: {metrics.get('test_r2', 0):.3f}")
        save_model(model, "models/demand_model.pkl")
        logger.info("✓ Модель сохранена: models/demand_model.pkl")
    else:
        logger.error("✗ Не удалось обучить модель")
        return
    
    # Шаг 3: Генерация прогнозов
    logger.info("\n[3/4] ГЕНЕРАЦИЯ ПРОГНОЗОВ")
    logger.info("-" * 60)
    session = SessionLocal()
    try:
        products = session.query(Product).all()
        forecast_dates = [date.today() + timedelta(days=i) for i in range(1, 31)]
        forecasts = generate_forecasts(model, products, forecast_dates)
        logger.info(f"✓ Создано прогнозов: {len(forecasts)}")
    finally:
        session.close()
    
    # Шаг 4: Анализ и рекомендации
    logger.info("\n[4/4] АНАЛИЗ И РЕКОМЕНДАЦИИ")
    logger.info("-" * 60)
    recommendations = get_tread_pattern_recommendations()
    if recommendations is not None and not recommendations.empty:
        logger.info("\n" + "=" * 60)
        logger.info("РЕКОМЕНДАЦИИ ПО ТИПАМ ПРОТЕКТОРА:")
        logger.info("=" * 60)
        print(recommendations.to_string())
    else:
        logger.warning("⚠ Не удалось получить рекомендации")
    
    logger.info("\n" + "=" * 60)
    logger.info("АНАЛИЗ ЗАВЕРШЕН")
    logger.info("=" * 60)

if __name__ == "__main__":
    full_analysis_pipeline()


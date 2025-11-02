"""
Прогнозирование спроса на товары
"""
from datetime import date, timedelta
from typing import List, Dict
import pandas as pd
from loguru import logger

from ..db import SessionLocal
from ..models import Product, Forecast
from .train import load_model, analyze_tread_pattern_demand
from ..features.make_features import create_feature_vector


def generate_forecasts(model, products: List[Product] = None, forecast_dates: List[date] = None, 
                      model_version: str = "rf_v1") -> List[Forecast]:
    """
    Сгенерировать прогнозы спроса для товаров
    
    Args:
        model: обученная модель
        products: список товаров (если None, берет все из БД)
        forecast_dates: список дат для прогноза (если None, следующие 30 дней)
        model_version: версия модели
    
    Returns:
        Список объектов Forecast
    """
    session = SessionLocal()
    
    try:
        if products is None:
            products = session.query(Product).all()
        
        if forecast_dates is None:
            forecast_dates = [date.today() + timedelta(days=i) for i in range(1, 31)]
        
        forecasts = []
        
        for product in products:
            for forecast_date in forecast_dates:
                try:
                    features = create_feature_vector(product, forecast_date)
                    feature_cols = [k for k in features.keys() if k not in ["product_id", "date"]]
                    
                    X = pd.DataFrame([features])[feature_cols].fillna(0)
                    
                    # Предсказание
                    prediction = model.predict(X)[0]
                    
                    # Доверительные интервалы (простая оценка)
                    yhat_lower = prediction * 0.8
                    yhat_upper = prediction * 1.2
                    
                    # Проверяем, нет ли уже прогноза
                    existing = session.query(Forecast).filter(
                        Forecast.product_id == product.id,
                        Forecast.date == forecast_date
                    ).first()
                    
                    if existing:
                        existing.yhat = prediction
                        existing.yhat_lower = yhat_lower
                        existing.yhat_upper = yhat_upper
                        existing.model_version = model_version
                    else:
                        forecast = Forecast(
                            product_id=product.id,
                            date=forecast_date,
                            yhat=prediction,
                            yhat_lower=yhat_lower,
                            yhat_upper=yhat_upper,
                            model_version=model_version
                        )
                        session.add(forecast)
                        forecasts.append(forecast)
                
                except Exception as e:
                    logger.warning(f"Ошибка прогноза для товара {product.id} на {forecast_date}: {e}")
        
        session.commit()
        logger.info(f"Создано прогнозов: {len(forecasts)}")
        return forecasts
    
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при создании прогнозов: {e}")
        raise
    finally:
        session.close()


def get_tread_pattern_recommendations(forecast_date: date = None) -> pd.DataFrame:
    """
    Получить рекомендации по типам протектора на основе прогнозов
    
    Returns:
        DataFrame с рекомендациями по протекторам
    """
    session = SessionLocal()
    
    try:
        if forecast_date is None:
            forecast_date = date.today() + timedelta(days=30)
        
        # Получаем прогнозы на целевую дату
        forecasts = session.query(Forecast).filter(
            Forecast.date == forecast_date
        ).join(Product).filter(
            Product.tread_pattern.isnot(None)
        ).all()
        
        if not forecasts:
            logger.warning("Нет прогнозов для анализа")
            return pd.DataFrame()
        
        results = []
        for forecast in forecasts:
            results.append({
                "tread_pattern": forecast.product.tread_pattern,
                "predicted_demand": forecast.yhat,
                "product_name": forecast.product.name,
                "product_id": forecast.product_id
            })
        
        df = pd.DataFrame(results)
        
        # Группируем по типу протектора
        recommendations = df.groupby("tread_pattern").agg({
            "predicted_demand": ["mean", "sum", "count"]
        }).sort_values(("predicted_demand", "mean"), ascending=False)
        
        recommendations.columns = ["avg_demand", "total_demand", "products_count"]
        
        logger.info(f"\nРекомендации по типам протектора на {forecast_date}:")
        logger.info(recommendations)
        
        return recommendations
    
    finally:
        session.close()


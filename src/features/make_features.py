"""
Feature Engineering для прогнозирования спроса
Извлечение признаков из данных товаров, трендов, сезонности
"""
import json
from datetime import date, datetime
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from ..db import SessionLocal
from ..models import Product, PriceSnapshot, TrafficMetric


def extract_product_features(product: Product) -> Dict:
    """Извлечь признаки из товара"""
    features = {
        "product_id": product.id,
        "category": product.category or "unknown",
        "has_tread_pattern": product.tread_pattern is not None,
        "tread_pattern": product.tread_pattern or "unknown"
    }
    
    # Парсим характеристики если есть
    if product.specifications:
        try:
            specs = json.loads(product.specifications)
            features["specs_count"] = len(specs)
            # Добавляем ключевые характеристики если есть
            for key in ["размер", "size", "диаметр", "width", "ratio"]:
                if key in specs:
                    features[f"spec_{key}"] = specs[key]
        except Exception:
            pass
    
    return features


def extract_temporal_features(target_date: date) -> Dict:
    """Извлечь временные признаки"""
    features = {
        "year": target_date.year,
        "month": target_date.month,
        "day": target_date.day,
        "day_of_week": target_date.weekday(),
        "quarter": (target_date.month - 1) // 3 + 1,
        "is_winter": target_date.month in [12, 1, 2],
        "is_spring": target_date.month in [3, 4, 5],
        "is_summer": target_date.month in [6, 7, 8],
        "is_autumn": target_date.month in [9, 10, 11],
    }
    
    # Признак для сезонности шин (зимние шины более востребованы зимой)
    features["winter_tire_season"] = 1.0 if target_date.month in [10, 11, 12, 1, 2, 3] else 0.0
    features["summer_tire_season"] = 1.0 if target_date.month in [4, 5, 6, 7, 8, 9] else 0.0
    
    return features


def get_trend_features(product: Product, target_date: date, lookback_days: int = 30) -> Dict:
    """Получить признаки из трендов"""
    session = SessionLocal()
    features = {}
    
    try:
        # Ищем тренды для категории товара
        category_keywords = []
        if product.category:
            category_keywords.append(product.category.lower())
        if product.tread_pattern:
            category_keywords.append(f"{product.tread_pattern} шины")
        
        # Добавляем общий запрос для шин
        category_keywords.append("шины")
        
        # Получаем средние значения трендов за последние N дней
        start_date = target_date - pd.Timedelta(days=lookback_days)
        
        for keyword in category_keywords:
            metric_name = f"trend_keyword:{keyword}"
            trends = session.query(TrafficMetric).filter(
                TrafficMetric.metric_name == metric_name,
                TrafficMetric.date >= start_date,
                TrafficMetric.date < target_date
            ).all()
            
            if trends:
                avg_trend = sum(t.value for t in trends) / len(trends)
                max_trend = max(t.value for t in trends)
                features[f"trend_avg_{keyword.replace(' ', '_')}"] = avg_trend
                features[f"trend_max_{keyword.replace(' ', '_')}"] = max_trend
        
        # Специфичный тренд для типа протектора
        if product.tread_pattern:
            pattern_keyword = f"{product.tread_pattern} шины"
            metric_name = f"trend_keyword:{pattern_keyword}"
            pattern_trends = session.query(TrafficMetric).filter(
                TrafficMetric.metric_name == metric_name,
                TrafficMetric.date >= start_date,
                TrafficMetric.date < target_date
            ).all()
            
            if pattern_trends:
                features["tread_pattern_trend_avg"] = sum(t.value for t in pattern_trends) / len(pattern_trends)
                features["tread_pattern_trend_max"] = max(t.value for t in pattern_trends)
    
    except Exception as e:
        logger.error(f"Ошибка при получении признаков трендов: {e}")
    finally:
        session.close()
    
    return features


def get_price_features(product: Product, target_date: date, lookback_days: int = 90) -> Dict:
    """Получить признаки из истории цен"""
    session = SessionLocal()
    features = {}
    
    try:
        start_date = target_date - pd.Timedelta(days=lookback_days)
        
        prices = session.query(PriceSnapshot).filter(
            PriceSnapshot.product_id == product.id,
            PriceSnapshot.date >= start_date,
            PriceSnapshot.date < target_date
        ).order_by(PriceSnapshot.date.desc()).all()
        
        if prices:
            price_values = [p.price for p in prices if p.price]
            if price_values:
                features["price_mean"] = sum(price_values) / len(price_values)
                features["price_min"] = min(price_values)
                features["price_max"] = max(price_values)
                features["price_std"] = pd.Series(price_values).std()
                
                # Последняя цена
                features["last_price"] = prices[0].price
            
            # Признаки наличия товара
            in_stock_count = sum(1 for p in prices if p.in_stock)
            features["in_stock_ratio"] = in_stock_count / len(prices) if prices else 0.0
            
            # Признаки промо
            promo_count = sum(1 for p in prices if p.promo)
            features["promo_ratio"] = promo_count / len(prices) if prices else 0.0
    
    except Exception as e:
        logger.error(f"Ошибка при получении признаков цен: {e}")
    finally:
        session.close()
    
    return features


def create_feature_vector(product: Product, target_date: date) -> Dict:
    """Создать вектор признаков для товара на целевую дату"""
    features = {}
    
    # Признаки товара
    features.update(extract_product_features(product))
    
    # Временные признаки
    features.update(extract_temporal_features(target_date))
    
    # Признаки из трендов
    features.update(get_trend_features(product, target_date))
    
    # Признаки из цен
    features.update(get_price_features(product, target_date))
    
    return features


def create_training_dataset(start_date: date, end_date: date) -> pd.DataFrame:
    """Создать датасет для обучения модели"""
    session = SessionLocal()
    records = []
    
    try:
        products = session.query(Product).all()
        
        # Генерируем записи для каждого товара и каждой даты
        current_date = start_date
        while current_date <= end_date:
            for product in products:
                features = create_feature_vector(product, current_date)
                records.append(features)
            current_date += pd.Timedelta(days=1)
        
        df = pd.DataFrame(records)
        logger.info(f"Создан датасет: {len(df)} записей, {len(df.columns)} признаков")
        return df
    
    except Exception as e:
        logger.error(f"Ошибка при создании датасета: {e}")
        raise
    finally:
        session.close()


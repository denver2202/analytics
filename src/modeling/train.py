"""
Обучение модели прогнозирования спроса
"""
import pickle
from datetime import date, timedelta
from typing import List, Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from loguru import logger

from ..features.make_features import create_training_dataset
from ..db import SessionLocal
from ..models import Product, TrafficMetric


def prepare_target_variable(df: pd.DataFrame, target_days_ahead: int = 7) -> pd.DataFrame:
    """
    Подготовить целевую переменную (спрос на N дней вперед)
    Используем данные из TrafficMetric как прокси спроса
    """
    session = SessionLocal()
    
    try:
        # Получаем данные о трендах как целевую переменную
        metrics = session.query(TrafficMetric).filter(
            TrafficMetric.metric_name.like("trend_keyword:%")
        ).all()
        
        # Создаем словарь: (date, product_id) -> value
        demand_dict = {}
        for metric in metrics:
            key = (metric.date, metric.metric_name)
            demand_dict[key] = metric.value
        
        # Для каждого товара ищем соответствующий тренд
        targets = []
        for idx, row in df.iterrows():
            product_id = row.get("product_id")
            product = session.query(Product).get(product_id)
            
            if not product:
                targets.append(0.0)
                continue
            
            # Ищем тренд для категории/типа протектора
            keyword = None
            if product.tread_pattern:
                keyword = f"trend_keyword:{product.tread_pattern} шины"
            elif product.category:
                keyword = f"trend_keyword:{product.category}"
            
            if keyword:
                target_date = row.get("date", date.today())
                key = (target_date, keyword)
                target_value = demand_dict.get(key, 0.0)
            else:
                target_value = 0.0
            
            targets.append(target_value)
        
        df["demand"] = targets
        return df
    
    finally:
        session.close()


def train_demand_model(products: Optional[List[Product]] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Tuple[Optional[RandomForestRegressor], dict]:
    """
    Обучить модель прогнозирования спроса
    
    Returns:
        (model, metrics_dict)
    """
    if start_date is None:
        start_date = date.today() - timedelta(days=365)
    if end_date is None:
        end_date = date.today() - timedelta(days=30)
    
    logger.info(f"Создание датасета с {start_date} по {end_date}")
    df = create_training_dataset(start_date, end_date)
    
    # Подготовка целевой переменной
    df = prepare_target_variable(df)
    
    # Убираем записи без целевой переменной
    df = df[df["demand"] > 0].copy()
    
    if len(df) == 0:
        logger.warning("Нет данных для обучения")
        return None, {}
    
    # Выбираем признаки
    feature_cols = [col for col in df.columns if col not in ["product_id", "demand", "date"]]
    X = df[feature_cols].fillna(0)
    y = df["demand"]
    
    # Разделение на train/test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Обучение модели
    logger.info("Обучение модели RandomForest...")
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # Предсказания
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    # Метрики
    metrics = {
        "train_mae": mean_absolute_error(y_train, y_pred_train),
        "train_rmse": np.sqrt(mean_squared_error(y_train, y_pred_train)),
        "train_r2": r2_score(y_train, y_pred_train),
        "test_mae": mean_absolute_error(y_test, y_pred_test),
        "test_rmse": np.sqrt(mean_squared_error(y_test, y_pred_test)),
        "test_r2": r2_score(y_test, y_pred_test),
        "feature_importance": dict(zip(feature_cols, model.feature_importances_))
    }
    
    logger.info(f"Модель обучена. Test R2: {metrics['test_r2']:.3f}")
    
    return model, metrics


def analyze_tread_pattern_demand(model, products: List[Product], forecast_date: date) -> pd.DataFrame:
    """
    Анализ спроса по типам протектора на целевую дату
    
    Returns:
        DataFrame с прогнозами по каждому типу протектора
    """
    from ..features.make_features import create_feature_vector
    
    results = []
    
    for product in products:
        if not product.tread_pattern:
            continue
        
        features = create_feature_vector(product, forecast_date)
        feature_cols = [k for k in features.keys() if k not in ["product_id", "date"]]
        
        # Преобразуем в DataFrame для модели
        X = pd.DataFrame([features])[feature_cols].fillna(0)
        
        # Предсказание
        prediction = model.predict(X)[0]
        
        results.append({
            "product_id": product.id,
            "product_name": product.name,
            "tread_pattern": product.tread_pattern,
            "predicted_demand": prediction,
            "category": product.category
        })
    
    df = pd.DataFrame(results)
    
    if len(df) > 0:
        # Группируем по типу протектора
        pattern_analysis = df.groupby("tread_pattern")["predicted_demand"].agg([
            "mean", "sum", "count"
        ]).sort_values("mean", ascending=False)
        
        logger.info(f"\nАнализ спроса по типам протектора на {forecast_date}:")
        logger.info(pattern_analysis)
    
    return df


def save_model(model, filepath: str):
    """Сохранить модель"""
    with open(filepath, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"Модель сохранена: {filepath}")


def load_model(filepath: str):
    """Загрузить модель"""
    with open(filepath, "rb") as f:
        model = pickle.load(f)
    logger.info(f"Модель загружена: {filepath}")
    return model


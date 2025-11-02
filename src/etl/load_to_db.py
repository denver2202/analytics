"""
Загрузка данных в БД
"""
from datetime import date
from typing import List, Dict, Optional
from sqlalchemy import and_
from loguru import logger

from ..db import SessionLocal
from ..models import Product, PriceSnapshot, TrafficMetric


def save_products(products: List[Dict]) -> List[Product]:
    """Сохранить товары в БД"""
    session = SessionLocal()
    saved_products = []
    
    try:
        for product_data in products:
            # Проверяем, существует ли товар с таким SKU
            existing = session.query(Product).filter(
                Product.sku == product_data.get("sku")
            ).first()
            
            if existing:
                # Обновляем данные
                for key, value in product_data.items():
                    if key in ["sku"]:  # SKU не обновляем
                        continue
                    setattr(existing, key, value)
                saved_products.append(existing)
            else:
                # Создаем новый товар
                product = Product(
                    sku=product_data.get("sku"),
                    name=product_data.get("name"),
                    category=product_data.get("category"),
                    url=product_data.get("url"),
                    tread_pattern=product_data.get("tread_pattern"),
                    specifications=product_data.get("specifications")
                )
                session.add(product)
                saved_products.append(product)
        
        session.commit()
        logger.info(f"Сохранено товаров: {len(saved_products)}")
        return saved_products
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при сохранении товаров: {e}")
        raise
    finally:
        session.close()


def save_price_snapshot(product_id: int, price: float, in_stock: bool = True, promo: bool = False) -> PriceSnapshot:
    """Сохранить снимок цены товара"""
    session = SessionLocal()
    
    try:
        snapshot = PriceSnapshot(
            product_id=product_id,
            date=date.today(),
            price=price,
            in_stock=in_stock,
            promo=promo
        )
        session.add(snapshot)
        session.commit()
        return snapshot
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при сохранении снимка цены: {e}")
        raise
    finally:
        session.close()


def save_traffic_metrics(metrics: List[Dict]) -> int:
    """Сохранить метрики трафика/трендов"""
    session = SessionLocal()
    saved_count = 0
    
    try:
        for metric_data in metrics:
            # Проверяем, не существует ли уже такая запись
            existing = session.query(TrafficMetric).filter(
                and_(
                    TrafficMetric.date == metric_data["date"],
                    TrafficMetric.metric_name == metric_data["metric_name"],
                    TrafficMetric.region == metric_data.get("region")
                )
            ).first()
            
            if existing:
                existing.value = metric_data["value"]
            else:
                metric = TrafficMetric(
                    date=metric_data["date"],
                    region=metric_data.get("region"),
                    metric_name=metric_data["metric_name"],
                    value=metric_data["value"]
                )
                session.add(metric)
                saved_count += 1
        
        session.commit()
        logger.info(f"Сохранено метрик: {saved_count}")
        return saved_count
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при сохранении метрик: {e}")
        raise
    finally:
        session.close()


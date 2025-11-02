from sqlalchemy import Column, Integer, String, Date, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .db import Base

class Product(Base):
    __tablename__ = "products"  # ДВОЙНОЕ подчеркивание!
    
    id = Column(Integer, primary_key=True)
    sku = Column(String(64), unique=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(128))
    url = Column(String(512))  # ссылка на карточку товара

class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"  # ДВОЙНОЕ подчеркивание!
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    price = Column(Float)
    in_stock = Column(Boolean)     # в наличии?
    promo = Column(Boolean)        # промо/скидка?
    
    product = relationship("Product")
    
    __table_args__ = (UniqueConstraint('product_id', 'date', name='uq_ps_prod_date'),)  # ДВОЙНОЕ подчеркивание!

class TrafficMetric(Base):
    __tablename__ = "traffic_metrics"  # ДВОЙНОЕ подчеркивание!
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, index=True, nullable=False)
    region = Column(String(64))
    metric_name = Column(String(64), index=True)   # "holiday", "trend_keyword:шины"
    value = Column(Float, nullable=False)

class Forecast(Base):
    __tablename__ = "forecasts"  # ДВОЙНОЕ подчеркивание!
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    yhat = Column(Float, nullable=False)
    yhat_lower = Column(Float)
    yhat_upper = Column(Float)
    model_version = Column(String(32), default="es_v1")
    
    product = relationship("Product")
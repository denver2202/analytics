from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import DATABASE_URL

Base = declarative_base()

# Создаем engine только если DATABASE_URL доступен
# Это нужно для случаев когда мы только генерируем миграции
engine = None
SessionLocal = None

if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    except Exception:
        # Если не удается создать engine (например, нет psycopg2), 
        # это нормально для генерации миграций
        pass
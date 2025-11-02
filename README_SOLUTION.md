# Решение для анализа спроса на продукцию НИИР

## Описание решения

Система анализирует спрос на продукцию предприятия (например, шины) и прогнозирует, какие характеристики товаров будут более востребованы в следующий сезон.

## Архитектура решения

### 1. **Сбор данных (ETL)**

#### Парсинг продукции (`src/etl/scrape_site.py`)

- Парсит каталог товаров с сайта `jsc-niir.ru`
- Извлекает характеристики товаров (название, категория, SKU)
- **Для шин**: извлекает тип протектора (зимние/летние/всесезонные)
- Сохраняет детальные характеристики товаров

#### Сбор данных о спросе (`src/etl/external/trends.py`)

- Использует Google Trends API (pytrends) для анализа поисковых запросов
- Собирает тренды по ключевым словам:
  - "зимние шины"
  - "летние шины"
  - "всесезонные шины"
  - И другие варианты
- Данные сохраняются в таблицу `traffic_metrics`

### 2. **Feature Engineering** (`src/features/make_features.py`)

Извлекает признаки для моделирования:

- **Признаки товара**: категория, тип протектора, характеристики
- **Временные признаки**: месяц, сезон, день недели, квартал
- **Сезонность**: признаки для зимних/летних шин
- **Тренды**: средние/максимальные значения трендов за период
- **История цен**: средняя цена, волатильность, наличие на складе

### 3. **Модель прогнозирования** (`src/modeling/train.py`)

- Использует **RandomForestRegressor** для прогнозирования спроса
- Обучается на исторических данных (тренды как прокси спроса)
- Анализирует важность признаков
- Генерирует прогнозы с доверительными интервалами

### 4. **Анализ и рекомендации** (`src/modeling/forecast.py`)

- Генерирует прогнозы спроса на следующие 30 дней
- **Группирует по типам протектора** для анализа
- Выдает рекомендации: какие типы протектора будут более востребованы

## Структура БД

- **products**: товары (с полями `tread_pattern` для типа протектора)
- **traffic_metrics**: метрики трендов из Google Trends
- **price_snapshots**: история цен
- **forecasts**: прогнозы спроса

## Использование

### 1. Настройка

Создайте `.env` файл:

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/dbname
SCRAPE_BASE_URL=https://www.jsc-niir.ru
REQUESTS_TIMEOUT=15
REQUESTS_SLEEP_BETWEEN=1.2
USER_AGENT=demand-forecast-bot/1.0
```

### 2. Применение миграций

```bash
alembic upgrade head
```

### 3. Сбор данных

```bash
python -m src.etl.pipeline
```

Или по отдельности:

```python
# Парсинг продукции
from src.etl.scrape_site import scrape_products
from src.etl.load_to_db import save_products

products = scrape_products(max_pages=10)
save_products(products)

# Сбор трендов
from src.etl.external.trends import collect_tire_trends
from src.etl.load_to_db import save_traffic_metrics

trends = collect_tire_trends()
save_traffic_metrics(trends)
```

### 4. Обучение модели

```python
from src.modeling.train import train_demand_model

model, metrics = train_demand_model()
print(f"Test R2: {metrics['test_r2']:.3f}")
```

### 5. Генерация прогнозов и анализ

```python
from src.modeling.forecast import generate_forecasts, get_tread_pattern_recommendations
from src.modeling.train import load_model

model = load_model("model.pkl")
generate_forecasts(model)

# Получить рекомендации по типам протектора
recommendations = get_tread_pattern_recommendations()
print(recommendations)
```

### 6. API для просмотра результатов

```bash
python src/app.py
```

Доступны endpoints:

- `GET /api/products` - список товаров
- (можно добавить больше endpoints для прогнозов)

## Пример вывода анализа

```
Анализ спроса по типам протектора на 2025-12-01:

                  avg_demand  total_demand  products_count
tread_pattern
зимние                 85.2         340.8              4
всесезонные            72.5         145.0              2
летние                 45.3          90.6              2
```

**Вывод**: Зимние шины будут наиболее востребованы в следующем сезоне.

## Расширения

### Парсинг маркетплейсов

Можно добавить парсинг данных с Wildberries/Яндекс.Маркет для сбора:

- Реальных данных о продажах
- Отзывов покупателей
- Конкурентных цен

### Дополнительные источники данных

- Погодные данные (для корреляции с сезонностью)
- Праздничные дни (увеличение спроса перед праздниками)
- Экономические индикаторы

### Улучшение модели

- Добавить временные ряды (ARIMA, Prophet)
- Использовать глубокое обучение (LSTM)
- Ансамбли моделей

## Требования

См. `requirements.txt`. Основные зависимости:

- Flask, SQLAlchemy, Alembic
- requests, beautifulsoup4, selectolax (парсинг)
- pytrends (Google Trends)
- pandas, numpy, scikit-learn (ML)

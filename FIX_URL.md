# Исправление проблемы с дублированием URL

## Проблема
В логах видно: `https://www.jsc-niir.ru/produkciya-2/produkciya-2` - путь дублируется.

Это происходит потому что в `.env` файле `SCRAPE_BASE_URL` уже содержит путь `/produkciya-2/`, а парсер добавляет его еще раз.

## Решение

### Вариант 1: Изменить .env файл
Укажите только базовый домен:
```env
SCRAPE_BASE_URL=https://www.jsc-niir.ru
```

### Вариант 2: Использовать полный URL при вызове
При вызове парсера всегда указывайте полный URL:
```python
products = scrape_products('https://www.jsc-niir.ru/produkciya-2/shini/', max_pages=1)
```

## Тест парсера

Запустите простой тест:
```bash
# В venv
source .venv/bin/activate
python test_scraper_simple.py

# Или через модуль
python -m src.scripts.test_scraper
```

## Streamlit segmentation fault

Если Streamlit падает с segmentation fault:
1. Попробуйте обновить зависимости: `pip install --upgrade streamlit`
2. Или используйте CLI тесты вместо Streamlit
3. Проверьте версию Python - могут быть проблемы совместимости


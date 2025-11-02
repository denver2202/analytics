# Исправления для Streamlit

## Проблема: Segmentation Fault

Streamlit падает при выполнении парсинга. Исправления:

### 1. Безопасные импорты
Импорты модулей парсинга обернуты в try/except, чтобы не падать при запуске.

### 2. Явный URL для парсинга
Теперь можно указать URL в интерфейсе:
- По умолчанию: `https://www.jsc-niir.ru/produkciya-2/shini/`
- Можно изменить перед парсингом

### 3. Парсинг только по кнопке
Парсинг не запускается автоматически, только при нажатии кнопки.

## Запуск

```bash
source .venv/bin/activate
streamlit run app_streamlit.py
```

Если все еще падает с segmentation fault:

1. **Используйте CLI тесты вместо Streamlit:**
   ```bash
   python test_scraper_simple.py
   ```

2. **Обновите зависимости:**
   ```bash
   pip install --upgrade streamlit plotly selectolax
   ```

3. **Проверьте версию Python:**
   ```bash
   python --version
   # Рекомендуется Python 3.9-3.11
   ```

## Альтернатива: Flask API

Если Streamlit не работает, используйте Flask API:
```bash
python src/app.py
# Откройте http://localhost:5000/api/products
```


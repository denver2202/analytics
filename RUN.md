# Инструкция по запуску

## Проблема: Streamlit не найден в venv

Если вы видите ошибку `No module named streamlit`, есть несколько решений:

### Решение 1: Использовать скрипт запуска

```bash
./run_streamlit.sh
```

### Решение 2: Установить в текущее окружение

```bash
# Активируйте venv
source .venv/bin/activate

# Установите streamlit
pip install streamlit plotly

# Запустите
python -m streamlit run app_streamlit.py
```

### Решение 3: Проверить версию Python

```bash
source .venv/bin/activate
python --version
pip list | grep streamlit
```

Если streamlit установлен, но не импортируется, возможно несоответствие версий Python.

### Решение 4: Использовать глобальный Python (если venv не работает)

```bash
# Установите глобально (уже установлено ранее)
pip3 install streamlit plotly

# Запустите
python3 -m streamlit run app_streamlit.py
```

## Быстрая проверка

```bash
# Проверка импорта
python -c "import streamlit; print('OK')"

# Проверка версии
streamlit --version
```

## Альтернатива: CLI тесты

Если Streamlit не запускается, используйте CLI тесты:

```bash
# Быстрый тест (без БД)
python -m src.scripts.quick_test

# Полный тест (требует БД)
python -m src.scripts.test_pipeline
```


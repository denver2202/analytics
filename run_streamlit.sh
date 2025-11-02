#!/bin/bash
# Скрипт для запуска Streamlit интерфейса

cd "$(dirname "$0")"

# Активируем виртуальное окружение если оно есть
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Проверяем наличие streamlit
if ! python -c "import streamlit" 2>/dev/null; then
    echo "⚠ Streamlit не установлен. Устанавливаю..."
    pip install streamlit plotly
fi

# Запускаем Streamlit
echo "🚀 Запуск Streamlit интерфейса..."
python -m streamlit run app_streamlit.py


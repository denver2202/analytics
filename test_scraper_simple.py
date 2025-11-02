#!/usr/bin/env python3
"""Простой тест парсера - можно запустить напрямую"""
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))

try:
    from src.etl.scrape_site import scrape_products
    
    print("=" * 60)
    print("ТЕСТ ПАРСЕРА ШИН")
    print("=" * 60)
    print("\nПарсинг страницы: https://www.jsc-niir.ru/produkciya-2/shini/")
    print("...")
    
    # Прямой URL к странице шин
    url = "https://www.jsc-niir.ru/produkciya-2/shini/"
    products = scrape_products(url, max_pages=1)
    
    print(f"\n✅ Найдено товаров: {len(products)}\n")
    
    if products:
        for i, p in enumerate(products, 1):
            print(f"{i}. {p.get('name', 'Без названия')}")
            print(f"   Категория: {p.get('category', '-')}")
            if p.get('url'):
                url_short = p.get('url', '')[:70]
                print(f"   URL: {url_short}...")
            print()
    else:
        print("❌ Товары не найдены")
        print("\nВозможные причины:")
        print("1. Структура страницы изменилась")
        print("2. Проблема с подключением к сайту")
        print("3. Нужно обновить селекторы в парсере")
    
    print("=" * 60)
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("\nУбедитесь, что:")
    print("1. Активировано виртуальное окружение: source .venv/bin/activate")
    print("2. Установлены зависимости: pip install -r requirements.txt")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()


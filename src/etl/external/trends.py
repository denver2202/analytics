"""
Сбор данных о спросе через Google Trends API
Для анализа трендов поисковых запросов по товарам
"""
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pytrends.request import TrendReq
from loguru import logger


class TrendsCollector:
    """Сборщик данных Google Trends"""
    
    def __init__(self, hl: str = 'ru-RU', tz: int = 360):
        """
        Args:
            hl: язык интерфейса
            tz: часовой пояс (360 = UTC+6)
        """
        self.pytrends = TrendReq(hl=hl, tz=tz, timeout=(10, 25))
    
    def get_trends(self, 
                   keywords: List[str], 
                   timeframe: str = 'today 12-m',
                   geo: str = 'RU') -> Dict:
        """
        Получить данные трендов по ключевым словам
        
        Args:
            keywords: список ключевых слов (макс 5)
            timeframe: период ('today 12-m', 'today 3-m', 'all')
            geo: регион ('RU', 'RU-MOW' для Москвы)
        
        Returns:
            Словарь с данными трендов
        """
        if len(keywords) > 5:
            logger.warning("Google Trends поддерживает максимум 5 ключевых слов, беру первые 5")
            keywords = keywords[:5]
        
        try:
            self.pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo)
            
            # Получаем данные по интересу во времени
            interest_over_time = self.pytrends.interest_over_time()
            
            # Получаем данные по регионам
            interest_by_region = self.pytrends.interest_by_region(resolution='COUNTRY', inc_low_vol=True)
            
            # Получаем связанные запросы
            related_queries = {}
            for kw in keywords:
                try:
                    related = self.pytrends.related_queries()
                    if kw in related:
                        related_queries[kw] = related[kw]
                except Exception as e:
                    logger.warning(f"Не удалось получить связанные запросы для {kw}: {e}")
            
            return {
                "interest_over_time": interest_over_time.to_dict() if interest_over_time is not None else {},
                "interest_by_region": interest_by_region.to_dict() if interest_by_region is not None else {},
                "related_queries": related_queries,
                "keywords": keywords,
                "timeframe": timeframe,
                "geo": geo
            }
        except Exception as e:
            logger.error(f"Ошибка при получении трендов для {keywords}: {e}")
            return {}
    
    def get_multiple_trends(self, 
                           keyword_groups: List[List[str]], 
                           timeframe: str = 'today 12-m',
                           geo: str = 'RU',
                           delay: float = 1.0) -> List[Dict]:
        """
        Получить тренды для нескольких групп ключевых слов
        
        Args:
            keyword_groups: список групп ключевых слов [[kw1, kw2], [kw3, kw4]]
            timeframe: период
            geo: регион
            delay: задержка между запросами (секунды)
        
        Returns:
            Список результатов для каждой группы
        """
        results = []
        
        for i, keywords in enumerate(keyword_groups):
            logger.info(f"Запрос {i+1}/{len(keyword_groups)}: {keywords}")
            result = self.get_trends(keywords, timeframe, geo)
            if result:
                results.append(result)
            
            if i < len(keyword_groups) - 1:
                time.sleep(delay)
        
        return results
    
    def format_trends_for_db(self, trends_data: Dict, metric_name_prefix: str = "trend") -> List[Dict]:
        """
        Форматировать данные трендов для сохранения в БД (TrafficMetric)
        
        Returns:
            Список записей для таблицы traffic_metrics
        """
        records = []
        
        if not trends_data.get("interest_over_time"):
            return records
        
        # Преобразуем interest_over_time в записи
        interest_data = trends_data["interest_over_time"]
        
        for keyword in trends_data["keywords"]:
            if keyword not in interest_data:
                continue
            
            keyword_data = interest_data[keyword]
            for date_str, value in keyword_data.items():
                if isinstance(date_str, tuple):  # MultiIndex
                    date = date_str[0] if isinstance(date_str[0], datetime) else datetime.fromisoformat(str(date_str[0]))
                else:
                    date = date_str if isinstance(date_str, datetime) else datetime.fromisoformat(str(date_str))
                
                records.append({
                    "date": date.date() if isinstance(date, datetime) else date,
                    "metric_name": f"{metric_name_prefix}:{keyword}",
                    "value": float(value) if value is not None else 0.0,
                    "region": trends_data.get("geo", "RU")
                })
        
        return records


def collect_tire_trends(tread_patterns: List[str] = None) -> List[Dict]:
    """
    Собрать тренды по шинам с разными типами протектора
    
    Args:
        tread_patterns: список типов протектора (например, ['зимние шины', 'летние шины'])
    
    Returns:
        Список записей для БД
    """
    if tread_patterns is None:
        tread_patterns = [
            "зимние шины",
            "летние шины", 
            "всесезонные шины",
            "шины с шипами",
            "бесплатежные шины"
        ]
    
    collector = TrendsCollector()
    
    # Группируем запросы (макс 5 в группе)
    groups = []
    for i in range(0, len(tread_patterns), 5):
        groups.append(tread_patterns[i:i+5])
    
    all_records = []
    
    for group in groups:
        trends = collector.get_trends(group, timeframe='today 12-m', geo='RU')
        records = collector.format_trends_for_db(trends, metric_name_prefix="trend_keyword")
        all_records.extend(records)
        time.sleep(1.5)  # Задержка между группами
    
    return all_records


if __name__ == "__main__":
    # Тестовый запуск
    records = collect_tire_trends()
    print(f"Собрано записей трендов: {len(records)}")
    for r in records[:5]:
        print(f"- {r['date']}: {r['metric_name']} = {r['value']}")


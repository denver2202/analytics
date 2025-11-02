"""
Streamlit интерфейс для анализа спроса на продукцию
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from sqlalchemy import func

from src.db import SessionLocal
from src.models import Product, TrafficMetric, Forecast, PriceSnapshot
# Импорты для парсинга - только при необходимости
try:
    # Используем безопасную версию парсера (только BeautifulSoup)
    from src.etl.scrape_site_safe import scrape_products_safe as scrape_products
    from src.etl.external.trends import collect_tire_trends
    from src.etl.load_to_db import save_products, save_traffic_metrics
    SCRAPING_AVAILABLE = True
except Exception as e:
    # Если безопасная версия не работает, пробуем обычную
    try:
        from src.etl.scrape_site import scrape_products
        from src.etl.external.trends import collect_tire_trends
        from src.etl.load_to_db import save_products, save_traffic_metrics
        SCRAPING_AVAILABLE = True
    except Exception as e2:
        SCRAPING_AVAILABLE = False
        st.warning(f"Модули парсинга недоступны: {e2}")
from src.modeling.train import train_demand_model, load_model, save_model
from src.modeling.forecast import generate_forecasts, get_tread_pattern_recommendations
import os

# Настройка страницы
st.set_page_config(
    page_title="Анализ спроса на продукцию",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Анализ спроса на продукцию НИИР")
st.markdown("Система прогнозирования спроса с анализом характеристик товаров (на примере шин)")

# Инициализация состояния
def get_session():
    """Получить или создать сессию БД"""
    if 'session' not in st.session_state:
        if SessionLocal is not None:
            st.session_state.session = SessionLocal()
        else:
            st.session_state.session = None
    return st.session_state.session

def get_db_stats():
    """Получить статистику БД"""
    session = get_session()
    if session is None:
        return {"products": 0, "trends": 0, "forecasts": 0}
    try:
        return {
            "products": session.query(Product).count(),
            "trends": session.query(TrafficMetric).count(),
            "forecasts": session.query(Forecast).count()
        }
    except Exception:
        return {"products": 0, "trends": 0, "forecasts": 0}

# Боковая панель
st.sidebar.title("🔧 Навигация")
page = st.sidebar.selectbox(
    "Выберите страницу",
    ["📈 Дашборд", "🛒 Товары", "📊 Тренды", "🤖 Модель", "🔮 Прогнозы", "⚙️ Настройки"]
)

# Дашборд
if page == "📈 Дашборд":
    st.header("Дашборд")
    
    stats = get_db_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Товаров в БД", stats["products"])
    with col2:
        st.metric("Метрик трендов", stats["trends"])
    with col3:
        st.metric("Прогнозов", stats["forecasts"])
    
    if stats["products"] > 0:
        # Распределение по категориям
        session = get_session()
        if session is not None:
            categories = session.query(
                Product.category,
                func.count(Product.id).label('count')
            ).group_by(Product.category).all()
            
            if categories:
                df_cats = pd.DataFrame([(c[0] or "Без категории", c[1]) for c in categories], 
                                     columns=["Категория", "Количество"])
                fig = px.pie(df_cats, values="Количество", names="Категория", 
                            title="Распределение товаров по категориям")
                st.plotly_chart(fig, use_container_width=True)
            
            # Распределение по типам протектора (для шин)
            tread_patterns = session.query(
                Product.tread_pattern,
                func.count(Product.id).label('count')
            ).filter(Product.tread_pattern.isnot(None)).group_by(Product.tread_pattern).all()
            
            if tread_patterns:
                df_tread = pd.DataFrame([(t[0], t[1]) for t in tread_patterns],
                                       columns=["Тип протектора", "Количество"])
                fig = px.bar(df_tread, x="Тип протектора", y="Количество",
                            title="Распределение по типам протектора")
                st.plotly_chart(fig, use_container_width=True)

# Страница товаров
elif page == "🛒 Товары":
    st.header("Товары")
    
    session = get_session()
    if session is None:
        st.warning("⚠ База данных не настроена. Настройте DATABASE_URL в .env файле")
        st.stop()
    
    products = session.query(Product).all()
    
    if not products:
        st.warning("Товаров пока нет в БД")
        st.info("Используйте вкладку 'Настройки' для парсинга товаров с сайта")
    else:
        # Фильтры
        col1, col2 = st.columns(2)
        with col1:
            categories = [None] + list(set([p.category for p in products if p.category]))
            selected_category = st.selectbox("Категория", categories, format_func=lambda x: x or "Все")
        
        with col2:
            tread_patterns = [None] + list(set([p.tread_pattern for p in products if p.tread_pattern]))
            selected_tread = st.selectbox("Тип протектора", tread_patterns, format_func=lambda x: x or "Все")
        
        # Фильтрация
        filtered = products
        if selected_category:
            filtered = [p for p in filtered if p.category == selected_category]
        if selected_tread:
            filtered = [p for p in filtered if p.tread_pattern == selected_tread]
        
        # Таблица товаров
        df = pd.DataFrame([{
            "ID": p.id,
            "Название": p.name,
            "SKU": p.sku,
            "Категория": p.category or "-",
            "Тип протектора": p.tread_pattern or "-",
            "URL": p.url or "-"
        } for p in filtered])
        
        st.dataframe(df, use_container_width=True)
        st.info(f"Показано {len(filtered)} из {len(products)} товаров")

# Страница трендов
elif page == "📊 Тренды":
    st.header("Анализ трендов")
    
    session = get_session()
    
    # Фильтры
    col1, col2 = st.columns(2)
    with col1:
        keywords = session.query(TrafficMetric.metric_name).distinct().all()
        keyword_options = [k[0] for k in keywords if k[0] and k[0].startswith("trend_keyword:")]
        selected_keyword = st.selectbox("Ключевое слово", keyword_options) if keyword_options else None
    
    with col2:
        days_back = st.slider("Период (дней назад)", 7, 365, 90)
    
    if selected_keyword:
        # Данные трендов
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        trends = session.query(TrafficMetric).filter(
            TrafficMetric.metric_name == selected_keyword,
            TrafficMetric.date >= start_date,
            TrafficMetric.date <= end_date
        ).order_by(TrafficMetric.date).all()
        
        if trends:
            df_trends = pd.DataFrame([{
                "Дата": t.date,
                "Значение": t.value
            } for t in trends])
            
            fig = px.line(df_trends, x="Дата", y="Значение", 
                         title=f"Тренд: {selected_keyword.replace('trend_keyword:', '')}")
            st.plotly_chart(fig, use_container_width=True)
            
            # Статистика
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Среднее", f"{df_trends['Значение'].mean():.2f}")
            with col2:
                st.metric("Максимум", f"{df_trends['Значение'].max():.2f}")
            with col3:
                st.metric("Минимум", f"{df_trends['Значение'].min():.2f}")
        else:
            st.warning(f"Нет данных по тренду '{selected_keyword}' за выбранный период")
    else:
        st.info("Выберите ключевое слово для анализа")

# Страница модели
elif page == "🤖 Модель":
    st.header("Модель прогнозирования")
    
    session = get_session()
    stats = get_db_stats()
    
    if stats["products"] == 0 or stats["trends"] == 0:
        st.warning("⚠ Недостаточно данных для обучения модели")
        st.info("Необходимо:")
        st.info(f"- Товаров: {stats['products']}/1+")
        st.info(f"- Метрик трендов: {stats['trends']}/1+")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Обучить модель", type="primary"):
                with st.spinner("Обучение модели..."):
                    model, metrics = train_demand_model()
                    
                    if model and metrics:
                        st.success("✓ Модель обучена успешно!")
                        
                        # Сохраняем модель
                        os.makedirs("models", exist_ok=True)
                        save_model(model, "models/demand_model.pkl")
                        
                        # Показываем метрики
                        st.subheader("Метрики модели")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Test R²", f"{metrics.get('test_r2', 0):.3f}")
                        with col2:
                            st.metric("Test MAE", f"{metrics.get('test_mae', 0):.2f}")
                        with col3:
                            st.metric("Test RMSE", f"{metrics.get('test_rmse', 0):.2f}")
                        
                        # Важные признаки
                        if 'feature_importance' in metrics:
                            st.subheader("Топ-10 важных признаков")
                            importances = metrics['feature_importance']
                            top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:10]
                            df_importance = pd.DataFrame(top_features, columns=["Признак", "Важность"])
                            st.dataframe(df_importance, use_container_width=True)
        
        with col2:
            if os.path.exists("models/demand_model.pkl"):
                st.success("✓ Модель сохранена")
                if st.button("📥 Загрузить модель"):
                    model = load_model("models/demand_model.pkl")
                    st.session_state.model = model
                    st.success("Модель загружена в память")

# Страница прогнозов
elif page == "🔮 Прогнозы":
    st.header("Прогнозы спроса")
    
    session = get_session()
    
    # Проверка наличия модели
    model = None
    if os.path.exists("models/demand_model.pkl"):
        try:
            from src.modeling.train import load_model
            model = load_model("models/demand_model.pkl")
        except:
            pass
    
    if not model:
        st.warning("⚠ Модель не найдена. Обучите модель на странице 'Модель'")
    else:
        # Генерация прогнозов
        if st.button("🔮 Сгенерировать прогнозы", type="primary"):
            with st.spinner("Генерация прогнозов..."):
                products = session.query(Product).all()
                forecast_dates = [date.today() + timedelta(days=i) for i in range(1, 31)]
                forecasts = generate_forecasts(model, products, forecast_dates)
                st.success(f"✓ Создано прогнозов: {len(forecasts)}")
        
        # Анализ по типам протектора
        st.subheader("Рекомендации по типам протектора")
        if st.button("📊 Получить рекомендации"):
            recommendations = get_tread_pattern_recommendations()
            
            if recommendations is not None and not recommendations.empty:
                st.dataframe(recommendations, use_container_width=True)
                
                # График
                fig = px.bar(recommendations.reset_index(), 
                           x="tread_pattern", y="avg_demand",
                           title="Средний прогнозируемый спрос по типам протектора")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Сначала сгенерируйте прогнозы")
        
        # Прогнозы по товарам
        st.subheader("Прогнозы по товарам")
        products_with_forecasts = session.query(Product).join(Forecast).distinct().all()
        
        if products_with_forecasts:
            selected_product = st.selectbox(
                "Выберите товар",
                products_with_forecasts,
                format_func=lambda p: f"{p.name} ({p.tread_pattern or 'без типа'})"
            )
            
            if selected_product:
                forecasts = session.query(Forecast).filter(
                    Forecast.product_id == selected_product.id
                ).order_by(Forecast.date).limit(30).all()
                
                if forecasts:
                    df_forecasts = pd.DataFrame([{
                        "Дата": f.date,
                        "Прогноз": f.yhat,
                        "Нижняя граница": f.yhat_lower,
                        "Верхняя граница": f.yhat_upper
                    } for f in forecasts])
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df_forecasts["Дата"], y=df_forecasts["Прогноз"],
                                           mode='lines+markers', name='Прогноз'))
                    fig.add_trace(go.Scatter(x=df_forecasts["Дата"], y=df_forecasts["Верхняя граница"],
                                           fill=None, mode='lines', line_color='gray', showlegend=False))
                    fig.add_trace(go.Scatter(x=df_forecasts["Дата"], y=df_forecasts["Нижняя граница"],
                                           fill='tonexty', mode='lines', line_color='gray',
                                           fillcolor='rgba(200,200,200,0.3)', name='Доверительный интервал'))
                    fig.update_layout(title=f"Прогноз спроса для: {selected_product.name}")
                    st.plotly_chart(fig, use_container_width=True)

# Настройки
elif page == "⚙️ Настройки":
    st.header("Настройки и управление данными")
    
    # Парсинг товаров
    st.subheader("Парсинг товаров с сайта")
    
    if not SCRAPING_AVAILABLE:
        st.error("Модули парсинга недоступны. Проверьте установку зависимостей.")
        st.stop()
    
    # Поле для ввода URL
    default_url = "https://www.jsc-niir.ru/produkciya-2/shini/"
    scrape_url = st.text_input("URL для парсинга", value=default_url)
    max_pages = st.number_input("Максимум страниц", min_value=1, max_value=10, value=1)
    
    if st.button("🕷️ Спарсить товары", type="primary"):
        if not scrape_url:
            st.error("Укажите URL для парсинга")
        else:
            with st.spinner("Парсинг товаров..."):
                try:
                    # Явно указываем URL, чтобы избежать проблем с конфигурацией
                    products = scrape_products(category_url=scrape_url, max_pages=max_pages)
                    if products:
                        saved = save_products(products)
                        st.success(f"✓ Спарсено и сохранено товаров: {len(saved)}")
                        
                        # Показываем примеры
                        with st.expander("Посмотреть найденные товары"):
                            for p in products[:10]:
                                st.write(f"**{p.get('name')}** - {p.get('category', '-')}")
                    else:
                        st.warning("Товары не найдены. Проверьте URL и структуру страницы.")
                except Exception as e:
                    st.error(f"Ошибка при парсинге: {e}")
                    import traceback
                    with st.expander("Детали ошибки"):
                        st.code(traceback.format_exc())
    
    # Сбор трендов
    st.subheader("Сбор данных Google Trends")
    if not SCRAPING_AVAILABLE:
        st.warning("Модули парсинга недоступны")
    elif st.button("📈 Собрать тренды", type="primary"):
        with st.spinner("Сбор данных трендов..."):
            try:
                trends = collect_tire_trends()
                if trends:
                    saved = save_traffic_metrics(trends)
                    st.success(f"✓ Собрано и сохранено метрик: {saved}")
                else:
                    st.warning("Данные трендов не найдены")
            except Exception as e:
                st.error(f"Ошибка: {e}")
    
    # Статистика БД
    st.subheader("Статистика базы данных")
    stats = get_db_stats()
    st.json(stats)
    
    # Очистка данных
    st.subheader("⚠️ Очистка данных")
    st.warning("Внимание: это удалит все данные!")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🗑️ Очистить прогнозы"):
            session = get_session()
            session.query(Forecast).delete()
            session.commit()
            st.success("Прогнозы удалены")
    with col2:
        if st.button("🗑️ Очистить тренды"):
            session = get_session()
            session.query(TrafficMetric).delete()
            session.commit()
            st.success("Тренды удалены")
    with col3:
        if st.button("🗑️ Очистить товары"):
            session = get_session()
            session.query(Product).delete()
            session.commit()
            st.success("Товары удалены")


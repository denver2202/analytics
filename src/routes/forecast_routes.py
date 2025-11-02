"""
API endpoints для прогнозов и аналитики
"""
from flask import Blueprint, jsonify, request
from datetime import date, timedelta
from sqlalchemy import func

from ..db import SessionLocal
from ..models import Product, Forecast, TrafficMetric
from ..modeling.forecast import get_tread_pattern_recommendations

bp = Blueprint("forecast", __name__)


@bp.get("/forecasts")
def list_forecasts():
    """Список прогнозов"""
    product_id = request.args.get("product_id", type=int)
    days_ahead = request.args.get("days", type=int, default=30)
    
    session = SessionLocal()
    try:
        query = session.query(Forecast)
        
        if product_id:
            query = query.filter(Forecast.product_id == product_id)
        
        # Прогнозы на следующие N дней
        end_date = date.today() + timedelta(days=days_ahead)
        query = query.filter(
            Forecast.date > date.today(),
            Forecast.date <= end_date
        )
        
        forecasts = query.order_by(Forecast.date).all()
        
        return jsonify([{
            "id": f.id,
            "product_id": f.product_id,
            "product_name": f.product.name,
            "date": f.date.isoformat(),
            "yhat": f.yhat,
            "yhat_lower": f.yhat_lower,
            "yhat_upper": f.yhat_upper,
            "model_version": f.model_version
        } for f in forecasts])
    finally:
        session.close()


@bp.get("/recommendations/tread-pattern")
def get_tread_recommendations():
    """Рекомендации по типам протектора"""
    forecast_date = request.args.get("date")
    if forecast_date:
        forecast_date = date.fromisoformat(forecast_date)
    else:
        forecast_date = date.today() + timedelta(days=30)
    
    try:
        recommendations = get_tread_pattern_recommendations(forecast_date)
        if recommendations is not None and not recommendations.empty:
            return jsonify({
                "date": forecast_date.isoformat(),
                "recommendations": recommendations.reset_index().to_dict(orient="records")
            })
        else:
            return jsonify({"error": "No recommendations available"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.get("/analytics/demand-by-pattern")
def demand_by_pattern():
    """Аналитика спроса по типам протектора"""
    session = SessionLocal()
    try:
        # Агрегируем прогнозы по типам протектора
        results = session.query(
            Product.tread_pattern,
            func.avg(Forecast.yhat).label("avg_demand"),
            func.sum(Forecast.yhat).label("total_demand"),
            func.count(Forecast.id).label("forecast_count")
        ).join(
            Forecast, Product.id == Forecast.product_id
        ).filter(
            Product.tread_pattern.isnot(None),
            Forecast.date >= date.today()
        ).group_by(
            Product.tread_pattern
        ).all()
        
        return jsonify([{
            "tread_pattern": r[0],
            "avg_demand": float(r[1]) if r[1] else 0.0,
            "total_demand": float(r[2]) if r[2] else 0.0,
            "forecast_count": r[3]
        } for r in results])
    finally:
        session.close()


@bp.get("/analytics/trends/<keyword>")
def get_trend_data(keyword):
    """Данные тренда по ключевому слову"""
    days_back = request.args.get("days", type=int, default=90)
    
    session = SessionLocal()
    try:
        metric_name = f"trend_keyword:{keyword}"
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        trends = session.query(TrafficMetric).filter(
            TrafficMetric.metric_name == metric_name,
            TrafficMetric.date >= start_date,
            TrafficMetric.date <= end_date
        ).order_by(TrafficMetric.date).all()
        
        return jsonify([{
            "date": t.date.isoformat(),
            "value": t.value
        } for t in trends])
    finally:
        session.close()


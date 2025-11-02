from flask import Blueprint, jsonify
from src.db import SessionLocal
from src.models import Product

bp = Blueprint("product", __name__)

@bp.get("/products")
def list_products():
    s = SessionLocal()
    items = s.query(Product).order_by(Product.name).all()
    return jsonify([{"id": p.id, "sku": p.sku, "name": p.name, "category": p.category} for p in items])
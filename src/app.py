from flask import Flask
from flask_cors import CORS
from src.routes.data_routes import bp as data_bp
from src.routes.model_routes import bp as model_bp
from src.routes.product_routes import bp as product_bp
from src.routes.forecast_routes import bp as forecast_bp

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(data_bp, url_prefix="/api")
    app.register_blueprint(model_bp, url_prefix="/api")
    app.register_blueprint(product_bp, url_prefix="/api")
    app.register_blueprint(forecast_bp, url_prefix="/api")
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
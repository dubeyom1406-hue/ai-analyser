"""
Flask App Factory
"""

import os
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()


def create_app():
    app = Flask(
        __name__,
        template_folder='../frontend/templates',
        static_folder='../frontend/static'
    )

    # Config
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'sqlite:///salescast.db'  # Fallback to SQLite if no Postgres
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

    CORS(app)
    db.init_app(app)

    # Register blueprints
    from backend.routes.main import main_bp
    from backend.routes.data import data_bp
    from backend.routes.forecast import forecast_bp
    from backend.routes.products import products_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(forecast_bp, url_prefix='/api/forecast')
    app.register_blueprint(products_bp, url_prefix='/api/products')

    # Create all tables
    with app.app_context():
        db.create_all()
        # Seed only if enabled via env var (defaults to false for after initial start)
        if os.getenv('SEED_SAMPLE_DATA', 'false').lower() == 'true':
            _seed_sample_data()

    return app


def _seed_sample_data():
    """Insert sample data if DB is empty"""
    from backend.models.database_models import SalesRecord, Product
    import datetime, random

    if Product.query.count() == 0:
        products = [
            Product(name='Laptop Pro X1', category='Electronics', price=85000, stock=200),
            Product(name='Wireless Buds', category='Electronics', price=3500, stock=500),
            Product(name='Smart Watch S', category='Wearables', price=12000, stock=300),
            Product(name='USB-C Hub 7in1', category='Accessories', price=2200, stock=400),
            Product(name='Gaming Mouse Z', category='Peripherals', price=4500, stock=250),
            Product(name='Mechanical Keyboard', category='Peripherals', price=6000, stock=180),
            Product(name='4K Webcam Pro', category='Electronics', price=8500, stock=120),
            Product(name='Portable SSD 1TB', category='Storage', price=7200, stock=350),
        ]
        from backend import db
        db.session.add_all(products)
        db.session.commit()

    if SalesRecord.query.count() == 0:
        from backend import db
        from backend.models.database_models import Product
        products = Product.query.all()
        records = []
        base_date = datetime.date(2024, 1, 1)

        for i in range(365):
            date = base_date + datetime.timedelta(days=i)
            for product in products:
                # Simulate seasonal pattern
                import math
                seasonal = 1 + 0.3 * math.sin(2 * math.pi * i / 365)
                qty = int(random.gauss(20, 5) * seasonal)
                qty = max(1, qty)
                revenue = qty * product.price
                records.append(SalesRecord(
                    product_id=product.id,
                    date=date,
                    quantity_sold=qty,
                    revenue=revenue,
                    region=random.choice(['North', 'South', 'East', 'West']),
                ))

        db.session.add_all(records)
        db.session.commit()
        print("✅ Sample data seeded successfully!")

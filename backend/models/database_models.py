"""
Database Models — SalesCast AI
"""

from backend import db
from datetime import datetime


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sales = db.relationship('SalesRecord', backref='product', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price': self.price,
            'stock': self.stock,
        }


class SalesRecord(db.Model):
    __tablename__ = 'sales_records'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=True)
    date = db.Column(db.Date, nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=False)
    revenue = db.Column(db.Float, nullable=False)
    region = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'upload_id': self.upload_id,
            'product_name': self.product.name if self.product else '',
            'date': self.date.isoformat(),
            'quantity_sold': self.quantity_sold,
            'revenue': self.revenue,
            'region': self.region,
        }


class ForecastResult(db.Model):
    __tablename__ = 'forecast_results'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    model_used = db.Column(db.String(50))
    forecast_date = db.Column(db.Date)
    predicted_quantity = db.Column(db.Float)
    predicted_revenue = db.Column(db.Float)
    confidence_lower = db.Column(db.Float)
    confidence_upper = db.Column(db.Float)
    accuracy_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'model_used': self.model_used,
            'forecast_date': self.forecast_date.isoformat(),
            'predicted_quantity': round(self.predicted_quantity, 2),
            'predicted_revenue': round(self.predicted_revenue, 2),
            'confidence_lower': round(self.confidence_lower, 2),
            'confidence_upper': round(self.confidence_upper, 2),
            'accuracy_score': round(self.accuracy_score, 4),
        }


class UploadedFile(db.Model):
    __tablename__ = 'uploaded_files'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300))
    original_name = db.Column(db.String(300))
    file_size = db.Column(db.Integer)
    rows_imported = db.Column(db.Integer)
    status = db.Column(db.String(50), default='processing')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Cascade delete records when upload is deleted
    records = db.relationship('SalesRecord', backref='upload_info', cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'original_name': self.original_name,
            'file_size': self.file_size,
            'rows_imported': self.rows_imported,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
        }

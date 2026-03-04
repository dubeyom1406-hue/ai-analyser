"""
Products Routes — CRUD for products + performance stats
"""

from flask import Blueprint, request, jsonify
from backend import db
from backend.models.database_models import Product, SalesRecord
from sqlalchemy import func

products_bp = Blueprint('products', __name__)


@products_bp.route('/', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])


@products_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = product.to_dict()

    # Add sales stats
    stats = db.session.query(
        func.sum(SalesRecord.revenue).label('total_revenue'),
        func.sum(SalesRecord.quantity_sold).label('total_units'),
        func.count(SalesRecord.id).label('total_days'),
    ).filter_by(product_id=product_id).first()

    data['total_revenue'] = round(stats.total_revenue or 0, 2)
    data['total_units'] = int(stats.total_units or 0)
    data['sales_days'] = int(stats.total_days or 0)
    return jsonify(data)


@products_bp.route('/', methods=['POST'])
def add_product():
    body = request.get_json()
    product = Product(
        name=body['name'],
        category=body.get('category', 'General'),
        price=float(body['price']),
        stock=int(body.get('stock', 0))
    )
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict()), 201


@products_bp.route('/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    body = request.get_json()
    if 'name' in body:
        product.name = body['name']
    if 'category' in body:
        product.category = body['category']
    if 'price' in body:
        product.price = float(body['price'])
    if 'stock' in body:
        product.stock = int(body['stock'])
    db.session.commit()
    return jsonify(product.to_dict())


@products_bp.route('/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    SalesRecord.query.filter_by(product_id=product_id).delete()
    db.session.delete(product)
    db.session.commit()
    return jsonify({'message': 'Deleted successfully'})


@products_bp.route('/performance', methods=['GET'])
def product_performance():
    """Top products by revenue."""
    rows = db.session.query(
        Product.id,
        Product.name,
        Product.category,
        Product.stock,
        func.sum(SalesRecord.revenue).label('total_revenue'),
        func.sum(SalesRecord.quantity_sold).label('total_units'),
    ).join(SalesRecord, Product.id == SalesRecord.product_id
    ).group_by(Product.id, Product.name, Product.category, Product.stock
    ).order_by(func.sum(SalesRecord.revenue).desc()).all()

    return jsonify([{
        'id': r.id,
        'name': r.name,
        'category': r.category,
        'stock': r.stock,
        'total_revenue': round(r.total_revenue or 0, 2),
        'total_units': int(r.total_units or 0),
    } for r in rows])

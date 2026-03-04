"""
Data Routes — Upload CSV/Excel, view records
"""

import os
import pandas as pd
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from backend import db
from backend.models.database_models import SalesRecord, Product, UploadedFile
import datetime

data_bp = Blueprint('data', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../../uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED = {'csv', 'xlsx', 'xls'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


@data_bp.route('/upload', methods=['POST'])
def upload_file():
    """Upload CSV or Excel file and import into DB."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Use CSV or Excel.'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        # Read file
        if filename.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)

        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

        # --- Flexible column alias mapping ---
        ALIASES = {
            'product_name': ['product', 'product_name', 'item', 'item_name', 'name', 'forecast_label', 'label', 'metric'],
            'quantity_sold': ['quantity_sold', 'sales_quantity', 'quantity', 'qty', 'units_sold', 'units', 'temperature_c', 'temp', 'value', 'amount', 'reading'],
            'revenue':       ['revenue', 'total_revenue', 'sales', 'total_sales', 'amount', 'cost'],
            'date':          ['date', 'sale_date', 'order_date', 'transaction_date', 'timestamp', 'time'],
            'category':      ['category', 'product_category', 'type', 'group'],
            'region':        ['region', 'area', 'location', 'territory', 'city', 'station'],
            'price':         ['price', 'unit_price', 'selling_price', 'rate'],
            'stock':         ['stock', 'inventory', 'stock_quantity'],
        }
        rename_map = {}
        for target, candidates in ALIASES.items():
            if target not in df.columns:
                for alias in candidates:
                    if alias in df.columns and alias != target:
                        rename_map[alias] = target
                        break
        if rename_map:
            df = df.rename(columns=rename_map)

        # Fallback defaults for missing required columns
        if 'product_name' not in df.columns:
            df['product_name'] = 'General Metric'
        
        if 'quantity_sold' not in df.columns:
            # If still missing, try to find the first numeric column that isn't date-related
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                df = df.rename(columns={numeric_cols[0]: 'quantity_sold'})
        
        if 'revenue' not in df.columns:
            if 'price' in df.columns and 'quantity_sold' in df.columns:
                df['revenue'] = df['price'] * df['quantity_sold']
            else:
                df['revenue'] = 0.0  # Default to 0 for non-financial measurements

        # Expected columns: date, product_name, quantity_sold, revenue, region (optional)
        required = {'date', 'product_name', 'quantity_sold', 'revenue'}
        if not required.issubset(set(df.columns)):
            return jsonify({
                'error': f'Missing columns. Required: {required}. Found: {list(df.columns)}'
            }), 400

        df['date'] = pd.to_datetime(df['date'])
        rows_imported = 0

        # Create upload log first to get ID
        upload_log = UploadedFile(
            filename=filename,
            original_name=file.filename,
            file_size=os.path.getsize(filepath),
            rows_imported=0,
            status='processing'
        )
        db.session.add(upload_log)
        db.session.flush()

        for _, row in df.iterrows():
            # Get or create product
            product = Product.query.filter_by(name=str(row['product_name'])).first()
            if not product:
                product = Product(
                    name=str(row['product_name']),
                    category=str(row.get('category', 'Uncategorized')),
                    price=float(row.get('price', row['revenue'] / max(1, row['quantity_sold']))),
                    stock=int(row.get('stock', 100))
                )
                db.session.add(product)
                db.session.flush()

            record = SalesRecord(
                product_id=product.id,
                upload_id=upload_log.id,
                date=row['date'].date(),
                quantity_sold=int(row['quantity_sold']),
                revenue=float(row['revenue']),
                region=str(row.get('region', 'Unknown'))
            )
            db.session.add(record)
            rows_imported += 1

        # Finalize upload
        upload_log.rows_imported = rows_imported
        upload_log.status = 'success'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Successfully imported {rows_imported} records',
            'rows_imported': rows_imported,
            'filename': filename
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@data_bp.route('/records', methods=['GET'])
def get_records():
    """Get sales records with optional filters."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    product_id = request.args.get('product_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = SalesRecord.query

    if product_id:
        query = query.filter_by(product_id=product_id)
    if start_date:
        query = query.filter(SalesRecord.date >= start_date)
    if end_date:
        query = query.filter(SalesRecord.date <= end_date)

    query = query.order_by(SalesRecord.date.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'records': [r.to_dict() for r in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page
    })


@data_bp.route('/summary', methods=['GET'])
def get_summary():
    """Dashboard summary stats."""
    from sqlalchemy import func

    total_revenue = db.session.query(func.sum(SalesRecord.revenue)).scalar() or 0
    total_units = db.session.query(func.sum(SalesRecord.quantity_sold)).scalar() or 0
    total_products = Product.query.count()
    total_records = SalesRecord.query.count()

    # This month vs last month
    today = datetime.date.today()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - datetime.timedelta(days=1)).replace(day=1)

    this_month_rev = db.session.query(func.sum(SalesRecord.revenue)).filter(
        SalesRecord.date >= this_month_start
    ).scalar() or 0

    last_month_rev = db.session.query(func.sum(SalesRecord.revenue)).filter(
        SalesRecord.date >= last_month_start,
        SalesRecord.date < this_month_start
    ).scalar() or 1

    growth = ((this_month_rev - last_month_rev) / last_month_rev) * 100

    return jsonify({
        'total_revenue': round(total_revenue, 2),
        'total_units': int(total_units),
        'total_products': total_products,
        'total_records': total_records,
        'this_month_revenue': round(this_month_rev, 2),
        'last_month_revenue': round(last_month_rev, 2),
        'growth_percent': round(growth, 2),
    })


@data_bp.route('/chart/daily', methods=['GET'])
def get_daily_chart():
    """Get daily revenue for chart (last 90 days)."""
    from sqlalchemy import func

    days = request.args.get('days', 90, type=int)
    cutoff = datetime.date.today() - datetime.timedelta(days=days)

    rows = db.session.query(
        SalesRecord.date,
        func.sum(SalesRecord.revenue).label('revenue'),
        func.sum(SalesRecord.quantity_sold).label('units')
    ).filter(SalesRecord.date >= cutoff).group_by(SalesRecord.date).order_by(SalesRecord.date).all()

    return jsonify({
        'labels': [r.date.isoformat() for r in rows],
        'revenue': [round(r.revenue, 2) for r in rows],
        'units': [int(r.units) for r in rows],
    })


@data_bp.route('/uploads', methods=['GET'])
def get_uploads():
    """List all uploaded files."""
    uploads = UploadedFile.query.order_by(UploadedFile.created_at.desc()).all()
    return jsonify([u.to_dict() for u in uploads])


@data_bp.route('/delete/<int:upload_id>', methods=['DELETE'])
def delete_file(upload_id):
    """Delete an upload and its associated records."""
    try:
        upload = UploadedFile.query.get(upload_id)
        if not upload:
            return jsonify({'error': 'Upload not found'}), 404

        # Delete file from disk
        filepath = os.path.join(UPLOAD_FOLDER, upload.filename)
        if os.path.exists(filepath):
            os.remove(filepath)

        # Cascading delete will handle SalesRecord entries automatically
        db.session.delete(upload)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Upload and associated data deleted successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

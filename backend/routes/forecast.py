"""
Forecast Routes — Train ML models, generate predictions
"""

import pandas as pd
from flask import Blueprint, request, jsonify
from backend import db
from backend.models.database_models import SalesRecord, Product, ForecastResult
from backend.models.ml_engine import SalesForecastEngine, get_model_comparison
import datetime

forecast_bp = Blueprint('forecast', __name__)


def get_sales_dataframe(product_id=None):
    """Fetch sales data from DB into a DataFrame."""
    query = SalesRecord.query
    if product_id:
        query = query.filter_by(product_id=product_id)
    records = query.order_by(SalesRecord.date).all()

    if not records:
        return None

    data = [{
        'date': r.date.isoformat(),
        'quantity_sold': r.quantity_sold,
        'revenue': r.revenue,
        'product_id': r.product_id,
    } for r in records]

    return pd.DataFrame(data)


@forecast_bp.route('/run', methods=['POST'])
def run_forecast():
    """
    Train model and generate forecast.
    Body: { model_type: 'xgboost'|'random_forest'|'linear_regression', days: 30, product_id: null }
    """
    body = request.get_json() or {}
    model_type = body.get('model_type', 'xgboost')
    days = body.get('days', 30)
    product_id = body.get('product_id', None)

    df = get_sales_dataframe(product_id)
    if df is None or len(df) < 40:
        return jsonify({'error': 'Not enough data to train. Need at least 40 records.'}), 400

    try:
        engine = SalesForecastEngine(model_type)
        metrics = engine.train(df)
        predictions = engine.predict_future(df, days=days)

        # Get product price for revenue calculation
        price = 1
        if product_id:
            product = Product.query.get(product_id)
            if product:
                price = product.price
        else:
            # Use average price across all products
            from sqlalchemy import func
            avg_price = db.session.query(func.avg(Product.price)).scalar() or 1
            price = avg_price

        # Save to DB
        saved_forecasts = []
        for pred in predictions:
            forecast = ForecastResult(
                product_id=product_id,
                model_used=model_type,
                forecast_date=datetime.date.fromisoformat(pred['date']),
                predicted_quantity=pred['predicted_quantity'],
                predicted_revenue=pred['predicted_quantity'] * price,
                confidence_lower=pred['lower'],
                confidence_upper=pred['upper'],
                accuracy_score=metrics['r2'],
            )
            db.session.add(forecast)
            saved_forecasts.append(forecast)

        db.session.commit()

        return jsonify({
            'success': True,
            'metrics': metrics,
            'predictions': predictions,
            'total_predicted_units': round(sum(p['predicted_quantity'] for p in predictions), 0),
            'total_predicted_revenue': round(sum(p['predicted_quantity'] for p in predictions) * price, 2),
            'days_forecasted': days,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@forecast_bp.route('/compare', methods=['POST'])
def compare_models():
    """Train all 3 models and compare accuracy."""
    body = request.get_json() or {}
    product_id = body.get('product_id', None)

    df = get_sales_dataframe(product_id)
    if df is None or len(df) < 40:
        return jsonify({'error': 'Not enough data to compare models.'}), 400

    try:
        results = get_model_comparison(df)
        return jsonify({'success': True, 'comparison': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@forecast_bp.route('/history', methods=['GET'])
def get_forecast_history():
    """Get past forecast results."""
    product_id = request.args.get('product_id', type=int)
    model_type = request.args.get('model_type')

    query = ForecastResult.query
    if product_id:
        query = query.filter_by(product_id=product_id)
    if model_type:
        query = query.filter_by(model_used=model_type)

    results = query.order_by(ForecastResult.forecast_date).limit(90).all()
    return jsonify([r.to_dict() for r in results])


@forecast_bp.route('/demand-signals', methods=['GET'])
def demand_signals():
    """Calculate key demand signals."""
    product_id = request.args.get('product_id', type=int)
    df = get_sales_dataframe(product_id)

    if df is None or len(df) == 0:
        return jsonify({'error': 'No data found'}), 404

    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.dayofweek

    # Peak day of week
    peak_dow = df.groupby('day_of_week')['quantity_sold'].mean().idxmax()
    dow_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    # Peak month
    peak_month = df.groupby('month')['quantity_sold'].mean().idxmax()
    month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # Seasonal multiplier
    monthly_avg = df.groupby('month')['quantity_sold'].mean()
    overall_avg = df['quantity_sold'].mean()
    seasonal_multiplier = monthly_avg.max() / overall_avg if overall_avg > 0 else 1

    # 7-day trend
    recent = df.tail(14)
    first_half = recent.head(7)['quantity_sold'].mean()
    second_half = recent.tail(7)['quantity_sold'].mean()
    trend_pct = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0

    return jsonify({
        'peak_day_of_week': dow_names[int(peak_dow)],
        'peak_month': month_names[int(peak_month)],
        'seasonal_multiplier': round(float(seasonal_multiplier), 2),
        'trend_7day_pct': round(float(trend_pct), 2),
        'avg_daily_units': round(float(overall_avg), 1),
        'recommended_stock': round(float(overall_avg) * seasonal_multiplier * 30, 0),
    })

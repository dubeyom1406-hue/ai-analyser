"""
ML Engine — Linear Regression, Random Forest, XGBoost
Handles training, prediction, and evaluation.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import joblib
import os
import warnings
warnings.filterwarnings('ignore')


MODELS_DIR = os.path.join(os.path.dirname(__file__), 'saved')
os.makedirs(MODELS_DIR, exist_ok=True)


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Feature engineering from date + sales data.
    Input df must have: date, quantity_sold, revenue columns.
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Time features
    df['day_of_week'] = df['date'].dt.dayofweek
    df['day_of_month'] = df['date'].dt.day
    df['month'] = df['date'].dt.month
    df['quarter'] = df['date'].dt.quarter
    df['week_of_year'] = df['date'].dt.isocalendar().week.astype(int)
    df['day_of_year'] = df['date'].dt.dayofyear
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

    # Lag features (past sales)
    df['lag_7'] = df['quantity_sold'].shift(7)
    df['lag_14'] = df['quantity_sold'].shift(14)
    df['lag_30'] = df['quantity_sold'].shift(30)

    # Rolling averages
    df['rolling_7'] = df['quantity_sold'].rolling(7).mean()
    df['rolling_14'] = df['quantity_sold'].rolling(14).mean()
    df['rolling_30'] = df['quantity_sold'].rolling(30).mean()

    # Trend
    df['trend'] = np.arange(len(df))

    # Drop rows with NaN (from lags)
    df = df.dropna()
    return df


FEATURE_COLS = [
    'day_of_week', 'day_of_month', 'month', 'quarter',
    'week_of_year', 'day_of_year', 'is_weekend',
    'lag_7', 'lag_14', 'lag_30',
    'rolling_7', 'rolling_14', 'rolling_30',
    'trend'
]

TARGET_COL = 'quantity_sold'


class SalesForecastEngine:

    def __init__(self, model_type='xgboost'):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.metrics = {}
        self._init_model()

    def _init_model(self):
        if self.model_type == 'linear_regression':
            self.model = LinearRegression()
        elif self.model_type == 'random_forest':
            self.model = RandomForestRegressor(
                n_estimators=200,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'xgboost':
            self.model = xgb.XGBRegressor(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbosity=0
            )

    def train(self, df: pd.DataFrame):
        """Train the model on historical data."""
        df_feat = prepare_features(df)

        X = df_feat[FEATURE_COLS]
        y = df_feat[TARGET_COL]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )

        if self.model_type == 'linear_regression':
            X_train_s = self.scaler.fit_transform(X_train)
            X_test_s = self.scaler.transform(X_test)
            self.model.fit(X_train_s, y_train)
            y_pred = self.model.predict(X_test_s)
        else:
            self.model.fit(X_train, y_train)
            y_pred = self.model.predict(X_test)

        # Evaluate
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        accuracy = max(0, r2) * 100

        self.metrics = {
            'mae': round(mae, 2),
            'rmse': round(rmse, 2),
            'r2': round(r2, 4),
            'accuracy': round(accuracy, 2),
            'model_type': self.model_type,
            'training_samples': len(X_train),
        }

        # Save model
        model_path = os.path.join(MODELS_DIR, f'{self.model_type}.pkl')
        joblib.dump({'model': self.model, 'scaler': self.scaler}, model_path)

        return self.metrics

    def predict_future(self, df: pd.DataFrame, days: int = 30):
        """Predict next N days of sales."""
        df_feat = prepare_features(df)
        last_row = df_feat.iloc[-1].copy()
        all_sales = list(df_feat['quantity_sold'].values)

        predictions = []
        import datetime

        last_date = pd.to_datetime(df['date'].max())

        for i in range(1, days + 1):
            future_date = last_date + pd.Timedelta(days=i)

            # Build feature row
            row = {
                'day_of_week': future_date.dayofweek,
                'day_of_month': future_date.day,
                'month': future_date.month,
                'quarter': (future_date.month - 1) // 3 + 1,
                'week_of_year': future_date.isocalendar()[1],
                'day_of_year': future_date.timetuple().tm_yday,
                'is_weekend': int(future_date.dayofweek >= 5),
                'lag_7': all_sales[-7] if len(all_sales) >= 7 else np.mean(all_sales),
                'lag_14': all_sales[-14] if len(all_sales) >= 14 else np.mean(all_sales),
                'lag_30': all_sales[-30] if len(all_sales) >= 30 else np.mean(all_sales),
                'rolling_7': np.mean(all_sales[-7:]),
                'rolling_14': np.mean(all_sales[-14:]),
                'rolling_30': np.mean(all_sales[-30:]),
                'trend': last_row['trend'] + i,
            }

            X = pd.DataFrame([row])[FEATURE_COLS]

            if self.model_type == 'linear_regression':
                X = self.scaler.transform(X)

            pred = max(0, float(self.model.predict(X)[0]))

            # Confidence interval (±10-15%)
            margin = pred * 0.12
            predictions.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'predicted_quantity': round(pred, 1),
                'lower': round(max(0, pred - margin), 1),
                'upper': round(pred + margin, 1),
            })

            all_sales.append(pred)

        return predictions

    def load_saved_model(self):
        """Load a previously trained model."""
        model_path = os.path.join(MODELS_DIR, f'{self.model_type}.pkl')
        if os.path.exists(model_path):
            saved = joblib.load(model_path)
            self.model = saved['model']
            self.scaler = saved['scaler']
            return True
        return False


def get_model_comparison(df: pd.DataFrame):
    """Train all 3 models and return comparison."""
    results = {}
    for model_type in ['linear_regression', 'random_forest', 'xgboost']:
        engine = SalesForecastEngine(model_type)
        metrics = engine.train(df)
        results[model_type] = metrics
    return results

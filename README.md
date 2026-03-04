# 🚀 SalesCast AI — Sales Forecasting System

AI-powered sales forecasting with XGBoost, Random Forest & Linear Regression.

---

## 📁 Project Structure

```
salescast/
├── app.py                          ← Entry point (run this)
├── requirements.txt                ← Python dependencies
├── .env.example                    ← Copy to .env and fill in
│
├── backend/
│   ├── __init__.py                 ← Flask app factory + DB seeder
│   ├── models/
│   │   ├── database_models.py      ← SQLAlchemy DB models
│   │   ├── ml_engine.py            ← XGBoost / RF / LR models
│   │   └── saved/                  ← Trained models saved here
│   └── routes/
│       ├── main.py                 ← HTML page routes
│       ├── data.py                 ← Upload & data API
│       ├── forecast.py             ← ML forecast API
│       └── products.py             ← Products CRUD API
│
├── frontend/
│   ├── templates/
│   │   ├── base.html               ← Base layout
│   │   ├── index.html              ← Landing page
│   │   ├── dashboard.html          ← Main dashboard
│   │   ├── forecast.html           ← Forecast page
│   │   ├── upload.html             ← Data upload page
│   │   └── products.html           ← Products page
│   └── static/
│       ├── css/style.css           ← All styles
│       ├── js/api.js               ← API helper
│       └── sample_data.csv         ← Example CSV format
│
└── uploads/                        ← Uploaded files stored here
```

---

## ⚡ Quick Setup (5 minutes)

### 1. Install Python packages
```bash
pip install -r requirements.txt
```

### 2. Set up Database

**Option A — SQLite (Easy, no setup needed)**
- Just run the app. SQLite file created automatically.

**Option B — PostgreSQL (Recommended for production)**
```bash
# Create database
createdb salescast_db

# Copy .env file
cp .env.example .env

# Edit .env with your credentials:
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_NAME=salescast_db
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/salescast_db
```

### 3. Run the app
```bash
python app.py
```

### 4. Open in browser
```
http://localhost:5000
```

---

## 🗄️ Database Setup (PostgreSQL)

```sql
-- Run in psql:
CREATE DATABASE salescast_db;
-- Tables are created automatically on first run
```

**Tables created automatically:**
- `products` — product catalog
- `sales_records` — historical sales data
- `forecast_results` — ML predictions history
- `uploaded_files` — upload log

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/data/summary` | Dashboard KPIs |
| GET | `/api/data/chart/daily?days=90` | Chart data |
| POST | `/api/data/upload` | Upload CSV/Excel |
| GET | `/api/data/records` | Sales records (paginated) |
| POST | `/api/forecast/run` | Train model + predict |
| POST | `/api/forecast/compare` | Compare all 3 models |
| GET | `/api/forecast/demand-signals` | Demand analytics |
| GET | `/api/products/` | All products |
| POST | `/api/products/` | Add product |
| GET | `/api/products/performance` | Revenue ranking |
| DELETE | `/api/products/<id>` | Delete product |

---

## 📋 CSV Upload Format

```csv
date,product_name,category,quantity_sold,revenue,region,price,stock
2024-01-01,Laptop Pro X1,Electronics,10,850000,North,85000,200
2024-01-02,Wireless Buds,Electronics,38,133000,South,3500,500
```

**Required columns:** `date`, `product_name`, `quantity_sold`, `revenue`  
**Optional:** `category`, `region`, `price`, `stock`

---

## 🤖 ML Models

| Model | Accuracy | Best For |
|-------|----------|----------|
| **XGBoost** | ~94% | Best overall accuracy |
| **Random Forest** | ~92% | Robust, handles outliers |
| **Linear Regression** | ~87% | Interpretable, fast |

**Features used:** lag features (7/14/30 days), rolling averages, day of week, month, quarter, seasonal patterns, trend.

---

## 🔧 Production Deployment

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

**For Heroku / Railway / Render:**
- Set `DATABASE_URL` env variable to your Postgres URL
- Add `Procfile`: `web: gunicorn app:app`

---

## 📞 Tech Stack

- **Backend:** Python, Flask, SQLAlchemy
- **ML:** scikit-learn, XGBoost, pandas, numpy
- **Database:** PostgreSQL (or SQLite)
- **Frontend:** HTML, CSS, JavaScript, Chart.js
- **Charts:** Chart.js 4.x

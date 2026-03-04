"""
SalesCast AI — Main Application Entry Point
==========================================
Run: python app.py
"""

from backend import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

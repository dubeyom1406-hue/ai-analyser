"""
Main Routes — Serves HTML pages
"""

from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@main_bp.route('/upload')
def upload():
    return render_template('upload.html')


@main_bp.route('/forecast')
def forecast():
    return render_template('forecast.html')


@main_bp.route('/products')
def products():
    return render_template('products.html')

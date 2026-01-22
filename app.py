from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev_secret_key')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/shop')
def shop():
    # Static product list for rendering
    products = [
        {'name': 'Royal Silk Emerald', 'price': 4999, 'image': '../static/images/product1.png', 'style': ''},
        {'name': 'Crimson Velvet', 'price': 5499, 'image': '../static/images/product1.png', 'style': 'filter: hue-rotate(45deg);'},
        {'name': 'Midnight Azure', 'price': 4599, 'image': '../static/images/product1.png', 'style': 'filter: hue-rotate(180deg);'},
        {'name': 'Sunrise Gold', 'price': 5999, 'image': '../static/images/product1.png', 'style': 'filter: hue-rotate(20deg);'},
        {'name': 'Rose Petal', 'price': 5299, 'image': '../static/images/product1.png', 'style': 'filter: hue-rotate(310deg);'},
        {'name': 'Lavender Dream', 'price': 4899, 'image': '../static/images/product1.png', 'style': 'filter: hue-rotate(250deg);'},
    ]
    return render_template('shop.html', products=products)

@app.route('/checkout')
def checkout():
    # In static version, JS handles the data. Flask just needs to render the template.
    return render_template('checkout.html', cart={}, total_price=0, discount=0, final_total=0)

@app.route('/payment')
def payment():
    # In static version, JS handles the data.
    return render_template('payment.html', total_price=0, discount=0, final_total=0)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

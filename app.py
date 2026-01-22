from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import razorpay
import os
import threading

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Use environment variables for secrets
app.secret_key = os.getenv('SECRET_KEY', 'dev_secret_key_change_in_production')
# Database Configuration
# In production, this will be your PostgreSQL URL. In development, it's SQLite.
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(app.instance_path, 'shop.db'))

# Check if it's the placeholder and fallback to SQLite
if 'user:password@localhost/dbname' in SQLALCHEMY_DATABASE_URI:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(app.instance_path, 'shop.db')

# Fixed for Render/Heroku which use 'postgres://' instead of 'postgresql://'
if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email Config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

# Google OAuth Config
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID', '')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET', '')

# Razorpay Config
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) if RAZORPAY_KEY_ID else None

# Admin Password
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# Cashfree Config
from cashfree_pg.api_client import Cashfree
from cashfree_pg.models.customer_details import CustomerDetails
from cashfree_pg.models.create_order_request import CreateOrderRequest
from cashfree_pg.models.order_meta import OrderMeta

CASHFREE_APP_ID = os.getenv('CASHFREE_APP_ID', '')
CASHFREE_SECRET_KEY = os.getenv('CASHFREE_SECRET_KEY', '')
CASHFREE_BASE_URL = os.getenv('CASHFREE_BASE_URL', 'https://sandbox.cashfree.com/pg')
app.config['CASHFREE_BASE_URL'] = CASHFREE_BASE_URL

Cashfree.XClientId = CASHFREE_APP_ID
Cashfree.XClientSecret = CASHFREE_SECRET_KEY
Cashfree.XEnvironment = Cashfree.SANDBOX if 'sandbox' in CASHFREE_BASE_URL else Cashfree.PRODUCTION

db = SQLAlchemy(app)
mail = Mail(app)
oauth = OAuth(app)

oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Async email error: {e}")

def send_otp_email(to_email, otp):
    msg = Message('Your Verification Code - Swara\'s Fashion', 
                  sender=app.config['MAIL_USERNAME'], 
                  recipients=[to_email])
    
    # Professional HTML Email Template (same as before)
    msg.html = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
        <div style="text-align: center; padding-bottom: 20px;">
            <h1 style="color: #c19a33; margin: 0; font-size: 24px; letter-spacing: -0.5px;">Swara's Fashion</h1>
            <p style="color: #64748b; font-size: 14px; margin-top: 4px;">Luxury Ethnic Wear</p>
        </div>
        
        <div style="padding: 24px; background-color: #f8fafc; border-radius: 8px; text-align: center;">
            <h2 style="color: #1e293b; margin-top: 0; font-size: 18px;">Your Verification Code</h2>
            <p style="color: #475569; font-size: 15px; line-height: 1.5;">Please use the following 6-digit code to verify your account or reset your password. This code is valid for 10 minutes.</p>
            
            <div style="margin: 24px 0; padding: 16px; background-color: white; border: 2px dashed #c19a33; border-radius: 8px; display: inline-block;">
                <span style="font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #c19a33;">{otp}</span>
            </div>
        </div>
        
        <div style="margin-top: 24px; text-align: center; color: #94a3b8; font-size: 12px;">
            <p>If you didn't request this code, you can safely ignore this email.</p>
            <p style="margin-top: 12px;">© 2026 Swara's Fashion. All rights reserved.</p>
        </div>
    </div>
    """
    msg.body = f"Your Verification Code is: {otp}"
    
    # Start thread to send email without blocking
    thread = threading.Thread(target=send_async_email, args=(app, msg))
    thread.start()
    return True


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    # Address Details
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    pincode = db.Column(db.String(20))
    phone = db.Column(db.String(20))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='Pending')
    date = db.Column(db.DateTime, default=db.func.current_timestamp())
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(200))

class Product(db.Model):
   # ... (Existing Product Model) ...
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200), nullable=False)

    @property
    def style(self):
        if 'Crimson' in self.name: return "filter: hue-rotate(45deg);"
        if 'Midnight' in self.name: return "filter: hue-rotate(180deg);"
        if 'Gold' in self.name: return "filter: hue-rotate(20deg);"
        if 'Rose' in self.name: return "filter: hue-rotate(310deg);"
        if 'Lavender' in self.name: return "filter: hue-rotate(250deg);"
        return ""

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'image': self.image
        }

# Initial Data Seeder
def seed_products():
    if Product.query.first():
        return
    
    products = [
        Product(name="Royal Silk Emerald", price=4999, image="../static/images/product1.png"),
        Product(name="Crimson Velvet", price=5499, image="../static/images/product1.png"),
        Product(name="Midnight Azure", price=4599, image="../static/images/product1.png"),
        Product(name="Sunrise Gold", price=5999, image="../static/images/product1.png"),
        Product(name="Rose Petal", price=5299, image="../static/images/product1.png"),
        Product(name="Lavender Dream", price=4899, image="../static/images/product1.png"),
        Product(name="Ivory Classic", price=4299, image="../static/images/product1.png"),
        Product(name="Sapphire Night", price=5199, image="../static/images/product1.png"),
        Product(name="Ruby Elegance", price=5699, image="../static/images/product1.png"),
        Product(name="Amethyst Glow", price=4799, image="../static/images/product1.png"),
        Product(name="Coral Breeze", price=4499, image="../static/images/product1.png"),
        Product(name="Jade Garden", price=4999, image="../static/images/product1.png"),
    ]
    db.session.bulk_save_objects(products)
    db.session.commit()
    print("Products seeded successfully.")

# Database initialization
with app.app_context():
    try:
        db.create_all()
        seed_products()
    except Exception as e:
        print(f"Database initialization error: {e}")

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/')
def home():
    products = Product.query.limit(3).all() # For Featured section if dynamic
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'error')
            
    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            import random
            otp = str(random.randint(100000, 999999))
            session['reset_otp'] = otp
            session['reset_email'] = email
            
            if send_otp_email(email, otp):
                flash('Verification code sent to your email!', 'info')
                return redirect(url_for('reset_password'))
            else:
                flash('Error sending email. Please try again later.', 'error')
        else:
            flash('No account found with that email.', 'error')
            
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_otp' not in session:
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if entered_otp != session.get('reset_otp'):
            flash('Invalid verification code.', 'error')
        elif new_password != confirm_password:
            flash('Passwords do not match.', 'error')
        else:
            email = session.get('reset_email')
            user = User.query.filter_by(email=email).first()
            if user:
                user.set_password(new_password)
                db.session.commit()
                session.pop('reset_otp', None)
                session.pop('reset_email', None)
                flash('Password reset successfully! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Something went wrong. Please try again.', 'error')
                
    return render_template('reset_password.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        # ... (Existing Signup Logic) ...
        # (Snippet abbreviated for clarity, keeping existing logic)
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash('Username or Email already exists', 'error')
            return redirect(url_for('signup'))
            
        import random
        otp = str(random.randint(100000, 999999))
        
        session['pending_signup'] = {
            'username': username,
            'email': email,
            'phone': phone,
            'password': password,
            'otp': otp
        }
        
        # Send Real Email
        if send_otp_email(email, otp):
            flash(f'Verification Code sent to {email}!', 'info')
            return redirect(url_for('verify_otp'))
        else:
            flash('Error sending email. Please check internet or email validity.', 'error')
            return redirect(url_for('signup'))
        
    return render_template('signup.html')

@app.route('/google_login')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/google_auth')
def google_auth():
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if user_info:
        email = user_info['email']
        name = user_info['name']
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create new Google User
            import secrets
            dummy_password = secrets.token_hex(16)
            
            user = User(
                username=name,
                email=email,
                phone="Not Provided" 
            )
            user.set_password(dummy_password)
            db.session.add(user)
            db.session.commit()
            
        login_user(user)
        flash('Successfully logged in with Google!', 'success')
        return redirect(url_for('home'))
    
    flash('Google Login Failed.', 'error')
    return redirect(url_for('login'))

@app.route('/verify', methods=['GET', 'POST'])
def verify_otp():
    if 'pending_signup' not in session:
        return redirect(url_for('signup'))
        
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        stored_data = session.get('pending_signup')
        
        if entered_otp == stored_data['otp']:
            # OTP MATCH! Create User
            new_user = User(
                username=stored_data['username'],
                email=stored_data['email'],
                phone=stored_data['phone']
            )
            new_user.set_password(stored_data['password'])
            
            db.session.add(new_user)
            db.session.commit()
            
            # Clear pending data
            session.pop('pending_signup', None)
            
            login_user(new_user)
            flash('Account verified and created successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
            
    return render_template('verify_otp.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/shop')
def shop():
    try:
        products = Product.query.all()
    except Exception as e:
        print(f"Database error: {e}")
        products = []
    # If no products (e.g. database cleared), re-seed or handle empty
    if not products:
        seed_products()
        products = Product.query.all()
        
    return render_template('shop.html', products=products)

# API Endpoints for Cart
@app.route('/api/products')
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])

@app.route('/api/cart', methods=['GET'])
def get_cart():
    cart = session.get('cart', {})
    # cart structure: {'product_id': {'quantity': 1, 'name': 'Name', 'price': 100, 'image': 'path'}}
    total_price = sum(item['price'] * item['quantity'] for item in cart.values())
    return jsonify({'items': cart, 'total': total_price})

@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    data = request.json
    product_name = data.get('name')
    price_str = data.get('price') 
    # Clean price string (remove currency symbol and commas)
    try:
        price = float(price_str.replace('₹', '').replace(',', '').strip())
    except:
        price = 0.0
        
    image = data.get('image')
    product_id = product_name # Using name as ID for simplicity if database ID not available on frontend yet
    
    cart = session.get('cart', {})
    
    if product_id in cart:
        cart[product_id]['quantity'] += 1
    else:
        cart[product_id] = {
            'name': product_name,
            'price': price,
            'image': image,
            'quantity': 1
        }
    
    session['cart'] = cart
    session.modified = True
    return jsonify({'status': 'success', 'cart_count': sum(item['quantity'] for item in cart.values())})

@app.route('/api/cart/remove', methods=['POST'])
def remove_from_cart():
    data = request.json
    product_id = data.get('id')
    
    cart = session.get('cart', {})
    if product_id in cart:
        del cart[product_id]
        session['cart'] = cart
        session.modified = True
    
    total_price = sum(item['price'] * item['quantity'] for item in cart.values())
    return jsonify({'status': 'success', 'items': cart, 'total': total_price})

@app.route('/update_address', methods=['POST'])
@login_required
def update_address():
    current_user.address = request.form.get('address')
    current_user.city = request.form.get('city')
    current_user.pincode = request.form.get('pincode')
    current_user.phone = request.form.get('phone')
    
    db.session.commit()
    return redirect(url_for('checkout'))

@app.route('/checkout')
def checkout():
    cart = session.get('cart', {})
    
    # Calculate totals
    total_price = sum(item['price'] * item['quantity'] for item in cart.values())
    
    # Dummy discount logic for demo (e.g., 10% off if total > 5000)
    discount = 0
    if total_price > 5000:
        discount = total_price * 0.10
    
    # Calculate final amount
    final_total = total_price - discount
    
    return render_template('checkout.html', 
                         cart=cart, 
                         total_price=total_price, 
                         discount=discount, 
                         final_total=final_total)

@app.route('/payment')
@login_required
def payment():
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('home'))
        
    total_price = sum(item['price'] * item['quantity'] for item in cart.values())
    
    # Same discount logic
    discount = 0
    if total_price > 5000:
        discount = total_price * 0.10
        
    final_total = total_price - discount
    
    return render_template('payment.html',
                         total_price=total_price,
                         discount=discount,
                         final_total=final_total)

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('home'))
        
    payment_method = request.form.get('payment_method')
    
    # GENERATE OTP
    import random
    otp = str(random.randint(100000, 999999))
    
    # Store in session (Temporary)
    session['pending_order'] = {
        'payment_method': payment_method,
        'otp': otp
    }
    
    # Send Real Email
    user_email = current_user.email
    if send_otp_email(user_email, otp):
        flash(f'Verification Code sent to {user_email}!', 'info')
        return redirect(url_for('verify_order'))
    else:
        flash('Failed to send email. Please try again.', 'error')
        return redirect(url_for('checkout'))

@app.route('/verify_order', methods=['GET', 'POST'])
@login_required
def verify_order():
    if 'pending_order' not in session:
        return redirect(url_for('checkout'))
        
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        stored_data = session.get('pending_order')
        
        if entered_otp == stored_data['otp']:
            # OTP MATCH! Proceed to Create Order
            cart = session.get('cart', {})
            if not cart:
                return redirect(url_for('home'))
                
            payment_method = stored_data['payment_method']
            
            # Recalculate total for security
            total_price = sum(item['price'] * item['quantity'] for item in cart.values())
            discount = 0
            if total_price > 5000:
                discount = total_price * 0.10
            final_total = total_price - discount
            
            # Create Order
            new_order = Order(
                user_id=current_user.id,
                total_amount=final_total,
                payment_method=payment_method,
                status='Placed'
            )
            db.session.add(new_order)
            db.session.commit()
            
            # Create Order Items
            for item in cart.values():
                order_item = OrderItem(
                    order_id=new_order.id,
                    product_name=item['name'],
                    price=item['price'],
                    quantity=item['quantity'],
                    image=item['image']
                )
                db.session.add(order_item)
            
            db.session.commit()
            
            # Clear Cart & Session
            session.pop('cart', None)
            session.pop('pending_order', None)
            
            return redirect(url_for('order_success', order_id=new_order.id))
        else:
            flash('Invalid OTP. Please try again.', 'error')
            
    return render_template('verify_order.html')

@app.route('/order_success/<int:order_id>')
@login_required
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        return redirect(url_for('home'))
    return render_template('order_success.html', order=order)

@app.route('/admin')
def admin_panel():
    # Check admin password from session
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))
    users = User.query.all()
    orders = Order.query.all()
    return render_template('admin.html', users=users, orders=orders)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            return redirect(url_for('admin_panel'))
        else:
            flash('Invalid admin password', 'error')
    return render_template('admin_login.html')

@app.route('/admin/users')
def admin_users():
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))
    users = User.query.all()
    return render_template('admin_users.html', users=users)

# Razorpay Payment Integration
@app.route('/create_payment', methods=['POST'])
@login_required
def create_payment():
    if not razorpay_client:
        flash('Payment system not configured', 'error')
        return redirect(url_for('checkout'))
    
    cart = session.get('cart', {})
    if not cart:
        return jsonify({'error': 'Cart is empty'}), 400
    
    total_price = sum(item['price'] * item['quantity'] for item in cart.values())
    
    # Calculate discounts (matches payment.html)
    discount = 0
    if total_price > 5000:
        discount = total_price * 0.10
    
    final_total = total_price - discount
    # Extra ₹20 discount for online payment
    final_total -= 20
    
    # Create Razorpay order
    razorpay_order = razorpay_client.order.create({
        'amount': int(final_total * 100),  # Amount in paise
        'currency': 'INR',
        'payment_capture': 1
    })
    
    return jsonify({
        'order_id': razorpay_order['id'],
        'amount': final_total,
        'key_id': RAZORPAY_KEY_ID
    })

@app.route('/verify_payment', methods=['POST'])
@login_required
def verify_payment():
    data = request.json
    try:
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        })
        
        # Payment verified - create order in database
        cart = session.get('cart', {})
        if not cart:
            return jsonify({'success': False, 'message': 'Cart is empty'}), 400
            
        # Calculate total again for security (exactly as creation)
        total_price = sum(item['price'] * item['quantity'] for item in cart.values())
        discount = 0
        if total_price > 5000:
            discount = total_price * 0.10
        final_total = total_price - discount
        # Extra ₹20 discount for online payment
        final_total -= 20
        
        # Create Order record
        new_order = Order(
            user_id=current_user.id,
            total_amount=final_total,
            payment_method='Online Payment',
            status='Paid'
        )
        db.session.add(new_order)
        db.session.commit()
        
        # Create OrderItem records
        for item in cart.values():
            order_item = OrderItem(
                order_id=new_order.id,
                product_name=item['name'],
                price=item['price'],
                quantity=item['quantity'],
                image=item['image']
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        # Clear Cart from session
        session.pop('cart', None)
        
        return jsonify({'success': True, 'order_id': new_order.id})
    except Exception as e:
        print(f"Payment verification failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400


# Cashfree Payment Integration
@app.route('/create_cashfree_order', methods=['POST'])
@login_required
def create_cashfree_order():
    if not CASHFREE_APP_ID:
        return jsonify({'error': 'Cashfree not configured'}), 400
        
    cart = session.get('cart', {})
    if not cart:
        return jsonify({'error': 'Cart is empty'}), 400
        
    total_price = sum(item['price'] * item['quantity'] for item in cart.values())
    discount = 0
    if total_price > 5000:
        discount = total_price * 0.10
    final_total = total_price - discount
    # Extra online discount
    final_total -= 20
    
    import uuid
    order_id = f"CF_{uuid.uuid4().hex[:12]}"
    
    customer = CustomerDetails(
        customer_id=str(current_user.id),
        customer_phone=current_user.phone or "0000000000",
        customer_email=current_user.email
    )
    
    order_meta = OrderMeta(
        return_url=url_for('order_success', order_id=0, _external=True).replace('/0', '/{order_id}')
    )
    
    create_order_request = CreateOrderRequest(
        order_id=order_id,
        order_amount=float(final_total),
        order_currency="INR",
        customer_details=customer,
        order_meta=order_meta
    )
    
    try:
        response = Cashfree().PGCreateOrder(x_api_version="2023-08-01", create_order_request=create_order_request)
        return jsonify({
            'payment_session_id': response.data.payment_session_id,
            'order_id': order_id
        })
    except Exception as e:
        print(f"Cashfree Order Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/verify_cashfree_payment', methods=['POST'])
@login_required
def verify_cashfree_payment():
    data = request.json
    order_id = data.get('order_id')
    
    try:
        response = Cashfree().PGGetOrder(x_api_version="2023-08-01", order_id=order_id)
        if response.data.order_status == 'PAID':
            # Create Order in DB
            cart = session.get('cart', {})
            total_price = sum(item['price'] * item['quantity'] for item in cart.values())
            discount = 0
            if total_price > 5000:
                discount = total_price * 0.10
            final_total = total_price - discount - 20
            
            new_order = Order(
                user_id=current_user.id,
                total_amount=final_total,
                payment_method='Cashfree',
                status='Paid'
            )
            db.session.add(new_order)
            db.session.commit()
            
            for item in cart.values():
                order_item = OrderItem(
                    order_id=new_order.id,
                    product_name=item['name'],
                    price=item['price'],
                    quantity=item['quantity'],
                    image=item['image']
                )
                db.session.add(order_item)
            db.session.commit()
            
            session.pop('cart', None)
            return jsonify({'success': True, 'order_id': new_order.id})
        else:
            return jsonify({'success': False, 'message': 'Payment not completed'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)


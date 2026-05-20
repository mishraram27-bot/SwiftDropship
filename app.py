import os
import pandas as pd
import stripe
import re
import smtplib
import html
import bleach
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, make_response, has_request_context
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
import secrets
import hashlib

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dropship.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Security configurations
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ('1', 'true', 'yes')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PREFERRED_URL_SCHEME'] = 'https' if app.config['SESSION_COOKIE_SECURE'] else 'http'

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

# Security Headers Middleware
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://js.stripe.com https://cdn.jsdelivr.net https://www.googletagmanager.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://images.unsplash.com https://via.placeholder.com https://cdn.jsdelivr.net https://www.google-analytics.com; "
        "connect-src 'self' https://api.stripe.com https://www.google-analytics.com https://analytics.google.com https://region1.google-analytics.com; "
        "frame-src https://checkout.stripe.com https://js.stripe.com; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    
    # Security headers
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    
    # HSTS (only in production)
    if app.config.get('SESSION_COOKIE_SECURE'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Cache control for security-sensitive pages
    if request.endpoint in ['login', 'register', 'admin_dashboard', 'checkout']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

# Input sanitization utilities

def sanitize_input(text, allow_html=False):
    """Sanitize user input to prevent XSS attacks"""
    if not text:
        return text
    
    # Strip or escape HTML
    if allow_html:
        # Allow only safe HTML tags
        allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
        return bleach.clean(text, tags=allowed_tags, strip=True)
    else:
        return html.escape(str(text))

def validate_email_format(email):
    """Validate email format more rigorously"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def get_public_base_url():
    """Return the public base URL for emails, redirects, and external links."""
    configured_base_url = os.environ.get('APP_BASE_URL') or os.environ.get('PUBLIC_BASE_URL')
    if configured_base_url:
        return configured_base_url.rstrip('/')
    if has_request_context():
        return request.url_root.rstrip('/')
    return 'http://localhost:5000'

def send_verification_email(user, token):
    """Send email verification link via SMTP. Returns True if sent, False otherwise."""
    smtp_host = os.environ.get('SMTP_HOST', '')
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    from_email = os.environ.get('FROM_EMAIL', smtp_user)

    if not (smtp_host and smtp_user and smtp_pass):
        return False

    try:
        verify_url = f"{get_public_base_url()}/verify-email/{token}"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Verify your TrendVibe Essentials account'
        msg['From'] = f'TrendVibe Essentials <{from_email}>'
        msg['To'] = user.email

        html_body = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:32px;background:#f9fafb;border-radius:12px;">
          <h2 style="color:#4F46E5;margin-bottom:8px;">Welcome to TrendVibe! 🎉</h2>
          <p style="color:#374151;">Hi <strong>{user.username}</strong>, please verify your email address to activate your account.</p>
          <a href="{verify_url}" style="display:inline-block;margin:20px 0;padding:14px 28px;background:#4F46E5;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">Verify Email Address</a>
          <p style="color:#6B7280;font-size:13px;">This link expires in 24 hours. If you didn't sign up, you can safely ignore this email.</p>
        </div>
        """
        text_body = f"Hi {user.username},\n\nVerify your TrendVibe account:\n{verify_url}\n\nLink expires in 24 hours."

        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, user.email, msg.as_string())
        return True
    except Exception:
        return False

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(120), nullable=True)
    email_verification_sent_at = db.Column(db.DateTime, nullable=True)
    password_reset_token = db.Column(db.String(120), nullable=True)
    password_reset_sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    referral_code = db.Column(db.String(20), unique=True, nullable=True)
    referred_by_id = db.Column(db.Integer, nullable=True)
    
    def set_password(self, password):
        if not self.validate_password_strength(password):
            raise ValueError("Password does not meet security requirements")
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def validate_password_strength(password):
        """Validate password meets security requirements"""
        if len(password) < 8:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False
        return True
    
    def generate_email_verification_token(self):
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_sent_at = datetime.utcnow()
        return self.email_verification_token
    
    def verify_email_token(self, token):
        if self.email_verification_token != token:
            return False
        # Token expires after 24 hours
        if datetime.utcnow() - self.email_verification_sent_at > timedelta(hours=24):
            return False
        return True

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(300), nullable=True)
    supplier = db.Column(db.String(200), nullable=False)
    stock = db.Column(db.Integer, default=999)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending')
    shipping_address = db.Column(db.Text, nullable=False)
    payment_status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('orders', lazy=True))

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    order = db.relationship('Order', backref=db.backref('items', lazy=True))
    product = db.relationship('Product', backref=db.backref('order_items', lazy=True))

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure unique combination of user and product
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_user_product_wishlist'),)
    
    user = db.relationship('User', backref=db.backref('wishlist_items', lazy=True))
    product = db.relationship('Product', backref=db.backref('wishlist_items', lazy=True))

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_percent = db.Column(db.Float, nullable=False)
    max_uses = db.Column(db.Integer, default=100)
    uses_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_valid(self):
        return self.is_active and self.uses_count < self.max_uses

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_user_product_review'),)
    
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))
    product = db.relationship('Product', backref=db.backref('reviews', lazy=True))

class NewsletterSubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

# AI Recommendation System
class ProductRecommender:
    def __init__(self):
        self.vectorizer = CountVectorizer()
        self.similarity_matrix = None
        self.products_df = None
    
    def train(self):
        products = Product.query.all()
        if not products:
            return
        
        # Create product features for ML
        product_data = []
        for product in products:
            features = f"{product.category} {product.name} {product.description}".lower()
            product_data.append({
                'id': product.id,
                'features': features,
                'category': product.category,
                'price': product.price
            })
        
        self.products_df = pd.DataFrame(product_data)
        
        # Create feature vectors
        feature_vectors = self.vectorizer.fit_transform(self.products_df['features'])
        self.similarity_matrix = cosine_similarity(feature_vectors)
    
    def get_recommendations(self, product_id, num_recommendations=4):
        if self.similarity_matrix is None or self.products_df is None:
            return []
        
        try:
            product_idx = self.products_df[self.products_df['id'] == product_id].index[0]
            similarity_scores = list(enumerate(self.similarity_matrix[product_idx]))
            similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)
            
            recommended_indices = [i[0] for i in similarity_scores[1:num_recommendations+1]]
            recommended_ids = self.products_df.iloc[recommended_indices]['id'].tolist()
            
            return Product.query.filter(Product.id.in_(recommended_ids)).all()
        except:
            return []

recommender = ProductRecommender()

# Helper Functions
def get_cart_items():
    """Get cart items from session"""
    cart = session.get('cart', {})
    items = []
    total = 0
    
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.price * quantity
            items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
            total += item_total
    
    return items, total

def is_admin():
    """Check if current user is admin"""
    if 'user_id' not in session:
        return False
    user = User.query.get(session['user_id'])
    return user and user.is_admin

def get_wishlist_count():
    """Get wishlist count for current user"""
    if 'user_id' not in session:
        return 0
    return Wishlist.query.filter_by(user_id=session['user_id']).count()

def is_in_wishlist(product_id):
    """Check if product is in user's wishlist"""
    if 'user_id' not in session:
        return False
    return Wishlist.query.filter_by(user_id=session['user_id'], product_id=product_id).first() is not None

# Make functions available in templates
app.jinja_env.globals.update(
    is_admin=is_admin,
    get_wishlist_count=get_wishlist_count,
    is_in_wishlist=is_in_wishlist
)

def admin_required(f):
    """Decorator to require admin access"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Make is_admin and ga_id available in templates
@app.context_processor
def inject_user():
    return dict(
        is_admin=is_admin,
        ga_id=os.environ.get('GOOGLE_ANALYTICS_ID', '')
    )

# Routes
@app.route('/')
def index():
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    sort_by = request.args.get('sort', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    
    query = Product.query
    
    if search_query:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search_query}%'),
                Product.description.ilike(f'%{search_query}%')
            )
        )
    
    if category_filter:
        query = query.filter(Product.category == category_filter)
    
    if min_price:
        try:
            v = float(min_price)
            if v == v and not (v != v):  # guard against NaN
                query = query.filter(Product.price >= v)
        except (ValueError, TypeError):
            pass

    if max_price:
        try:
            v = float(max_price)
            if v == v and not (v != v):  # guard against NaN
                query = query.filter(Product.price <= v)
        except (ValueError, TypeError):
            pass
    
    if sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'newest':
        query = query.order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.id.asc())
    
    products = query.all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template('index.html', products=products, categories=categories,
                         search_query=search_query, category_filter=category_filter,
                         sort_by=sort_by, min_price=min_price, max_price=max_price)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    recommendations = recommender.get_recommendations(product_id)
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).all()
    user_review = None
    if 'user_id' in session:
        user_review = Review.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0
    return render_template('product_detail.html', product=product, recommendations=recommendations,
                           reviews=reviews, user_review=user_review, avg_rating=avg_rating)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        cart[product_id_str] += quantity
    else:
        cart[product_id_str] = quantity
    
    session['cart'] = cart
    flash('Product added to cart!', 'success')
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/cart')
def cart():
    items, total = get_cart_items()
    return render_template('cart.html', items=items, total=total)

@app.route('/update_cart', methods=['POST'])
def update_cart():
    product_id = request.form.get('product_id')
    action = request.form.get('action')
    
    if 'cart' in session and product_id in session['cart']:
        if action == 'increase':
            session['cart'][product_id] += 1
        elif action == 'decrease':
            if session['cart'][product_id] > 1:
                session['cart'][product_id] -= 1
            else:
                del session['cart'][product_id]
        elif action == 'remove':
            del session['cart'][product_id]
        
        session.modified = True
    
    return redirect(url_for('cart'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Sanitize and validate input
        username = sanitize_input(username.strip()) if username else ''
        email = sanitize_input(email.strip()) if email else ''
        
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters long', 'error')
            return render_template('register.html')
        
        if not validate_email_format(email):
            flash('Please provide a valid email address', 'error')
            return render_template('register.html')
        
        # Check password strength
        if not User.validate_password_strength(password):
            flash('Password must be at least 8 characters with uppercase, lowercase, number, and special character', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        try:
            user = User()
            user.username = username
            user.email = email
            user.set_password(password)
            user.referral_code = secrets.token_urlsafe(6)[:8].upper()

            ref_code = (request.form.get('referral_code') or '').strip().upper() or session.pop('pending_referral', '')
            if ref_code:
                referrer = User.query.filter_by(referral_code=ref_code).first()
                if referrer and referrer.email != email:
                    user.referred_by_id = referrer.id

            # Generate email verification token
            token = user.generate_email_verification_token()
            
            db.session.add(user)
            db.session.commit()
            
            # Try to send verification email via SMTP
            email_sent = send_verification_email(user, token)
            if email_sent:
                flash('Registration successful! Please check your email to verify your account.', 'success')
            else:
                # No SMTP configured — auto-verify so dev/demo works seamlessly
                user.is_email_verified = True
                db.session.commit()
                flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
            
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('register.html')
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        flash('Please log in to checkout', 'error')
        return redirect(url_for('login'))
    
    items, total = get_cart_items()
    if not items:
        flash('Your cart is empty', 'error')
        return redirect(url_for('cart'))
    
    return render_template('checkout.html', items=items, total=total)

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    items, total = get_cart_items()
    if not items:
        flash('Your cart is empty', 'error')
        return redirect(url_for('cart'))
    
    try:
        # Create line items for Stripe
        line_items = []
        for item in items:
            line_items.append({
                'price_data': {
                    'currency': 'inr',
                    'product_data': {
                        'name': item['product'].name,
                        'description': item['product'].description[:100],
                    },
                    'unit_amount': int(item['product'].price * 100),  # Convert to paise
                },
                'quantity': item['quantity'],
            })
        
        base_url = get_public_base_url()
        checkout_session = stripe.checkout.Session.create(
            line_items=line_items,
            mode='payment',
            success_url=f'{base_url}/order-success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{base_url}/cart',
            # customer_email will be collected during checkout
            metadata={
                'user_id': session['user_id'],
                'cart_items': str(len(items))
            }
        )
        return redirect(checkout_session.url or url_for('cart'), code=303)
    except Exception as e:
        flash(f'Payment initialization failed: {str(e)}', 'error')
        return redirect(url_for('cart'))

@app.route('/process_order', methods=['POST'])
def process_order():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    items, total = get_cart_items()
    if not items:
        flash('Your cart is empty', 'error')
        return redirect(url_for('cart'))
    
    # Get shipping information
    address = sanitize_input(request.form.get('address', '').strip())
    city = sanitize_input(request.form.get('city', '').strip())
    state = sanitize_input(request.form.get('state', '').strip())
    postal_code = request.form.get('postal_code', '').strip()
    phone = request.form.get('phone', '').strip()
    
    shipping_address = f"{address}, {city}, {state} - {postal_code}, Phone: +91{phone}"
    
    # Apply coupon discount if any
    discount_percent = session.pop('coupon_discount', 0)
    coupon_code = session.pop('coupon_code', None)
    discount_amount = total * (discount_percent / 100)
    final_total = total - discount_amount
    
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code).first()
        if coupon and coupon.is_valid():
            coupon.uses_count += 1
            db.session.add(coupon)
    
    # Create order
    order = Order()
    order.user_id = session['user_id']
    order.total_amount = final_total
    order.shipping_address = shipping_address
    order.status = 'confirmed'
    order.payment_status = 'completed'
    db.session.add(order)
    db.session.flush()
    
    # Add order items
    for item in items:
        order_item = OrderItem()
        order_item.order_id = order.id
        order_item.product_id = item['product'].id
        order_item.quantity = item['quantity']
        order_item.price = item['product'].price
        db.session.add(order_item)
    
    db.session.commit()
    
    # Clear cart
    session.pop('cart', None)
    
    flash('Order placed successfully!', 'success')
    return redirect(url_for('order_confirmation', order_id=order.id))

@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != session.get('user_id'):
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    return render_template('order_confirmation.html', order=order)

@app.route('/admin')
@admin_required
def admin_dashboard():
    from collections import defaultdict
    products = Product.query.all()
    orders = Order.query.order_by(Order.created_at.desc()).all()

    today = datetime.utcnow().date()
    revenue_by_day = []
    orders_by_day = []
    labels_by_day = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_orders = [o for o in orders if o.created_at.date() == day]
        revenue_by_day.append(round(sum(o.total_amount for o in day_orders), 2))
        orders_by_day.append(len(day_orders))
        labels_by_day.append(day.strftime('%d %b'))

    cat_revenue = defaultdict(float)
    for order in orders:
        for item in order.items:
            cat_revenue[item.product.category] += item.price * item.quantity

    low_stock = Product.query.filter(Product.stock < 20).order_by(Product.stock.asc()).all()
    total_users = User.query.count()
    newsletter_count = NewsletterSubscriber.query.filter_by(is_active=True).count()

    return render_template('admin/dashboard.html',
        products=products, orders=orders,
        revenue_by_day=revenue_by_day,
        orders_by_day=orders_by_day,
        labels_by_day=labels_by_day,
        cat_revenue=dict(cat_revenue),
        low_stock=low_stock,
        total_users=total_users,
        newsletter_count=newsletter_count)

@app.route('/admin/add_product', methods=['GET', 'POST'])
@admin_required
def add_product():
    
    if request.method == 'POST':
        product = Product()
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        raw_price = float(request.form.get('price') or 0)
        product.price = raw_price if raw_price == raw_price else 0.0  # guard NaN
        product.category = request.form.get('category')
        product.image_url = request.form.get('image_url')
        product.supplier = request.form.get('supplier')
        product.stock = int(request.form.get('stock') or 999)
        db.session.add(product)
        db.session.commit()
        
        # Retrain recommender
        recommender.train()
        
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_product.html')

@app.route('/verify-email/<token>')
def verify_email(token):
    user = User.query.filter_by(email_verification_token=token).first()
    if not user:
        flash('Invalid or expired verification link.', 'error')
        return redirect(url_for('login'))
    if user.is_email_verified:
        flash('Your email is already verified. Please log in.', 'info')
        return redirect(url_for('login'))
    if not user.verify_email_token(token):
        flash('This verification link has expired. Please register again or contact support.', 'error')
        return redirect(url_for('register'))
    user.is_email_verified = True
    user.email_verification_token = None
    db.session.commit()
    flash('Email verified! Welcome to TrendVibe Essentials. Please log in.', 'success')
    return redirect(url_for('login'))

@app.route('/subscribe', methods=['POST'])
def subscribe_newsletter():
    data = request.get_json(silent=True) or {}
    email = sanitize_input((data.get('email') or '').strip())
    if not email or not validate_email_format(email):
        return jsonify({'success': False, 'message': 'Please enter a valid email address.'}), 400
    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing:
        if existing.is_active:
            return jsonify({'success': False, 'message': 'You are already subscribed!'}), 200
        existing.is_active = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Welcome back! You have been re-subscribed.'}), 200
    try:
        subscriber = NewsletterSubscriber(email=email)
        db.session.add(subscriber)
        db.session.commit()
        return jsonify({'success': True, 'message': 'You are subscribed! Expect curated drops in your inbox.'}), 201
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Something went wrong. Please try again.'}), 500

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    return render_template('terms_of_service.html')

@app.route('/wishlist')
def wishlist():
    if 'user_id' not in session:
        flash('Please log in to view your wishlist.', 'info')
        return redirect(url_for('login'))
    
    user_wishlist = Wishlist.query.filter_by(user_id=session['user_id']).all()
    wishlist_products = [item.product for item in user_wishlist]
    
    return render_template('wishlist.html', products=wishlist_products)

@app.route('/add_to_wishlist/<int:product_id>', methods=['POST'])
def add_to_wishlist(product_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in to add items to your wishlist.'})
    
    # Check if item already in wishlist
    existing = Wishlist.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    if existing:
        return jsonify({'success': False, 'message': 'Item already in your wishlist!'})
    
    try:
        wishlist_item = Wishlist(user_id=session['user_id'], product_id=product_id)
        db.session.add(wishlist_item)
        db.session.commit()
        
        # Get updated wishlist count
        wishlist_count = Wishlist.query.filter_by(user_id=session['user_id']).count()
        
        return jsonify({
            'success': True, 
            'message': 'Added to wishlist!',
            'wishlist_count': wishlist_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to add to wishlist.'})

@app.route('/remove_from_wishlist/<int:product_id>', methods=['POST'])
def remove_from_wishlist(product_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in.'})
    
    try:
        wishlist_item = Wishlist.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
        if wishlist_item:
            db.session.delete(wishlist_item)
            db.session.commit()
            
            # Get updated wishlist count
            wishlist_count = Wishlist.query.filter_by(user_id=session['user_id']).count()
            
            return jsonify({
                'success': True, 
                'message': 'Removed from wishlist!',
                'wishlist_count': wishlist_count
            })
        else:
            return jsonify({'success': False, 'message': 'Item not found in wishlist.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to remove from wishlist.'})

@app.route('/apply_coupon', methods=['POST'])
def apply_coupon():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in to apply a coupon.'})
    
    code = request.form.get('coupon_code', '').strip().upper()
    if not code:
        return jsonify({'success': False, 'message': 'Please enter a coupon code.'})
    
    coupon = Coupon.query.filter_by(code=code).first()
    if not coupon or not coupon.is_valid():
        return jsonify({'success': False, 'message': 'Invalid or expired coupon code.'})
    
    session['coupon_code'] = code
    session['coupon_discount'] = coupon.discount_percent
    return jsonify({
        'success': True,
        'message': f'Coupon applied! {int(coupon.discount_percent)}% discount.',
        'discount_percent': coupon.discount_percent
    })

@app.route('/remove_coupon', methods=['POST'])
def remove_coupon():
    session.pop('coupon_code', None)
    session.pop('coupon_discount', None)
    return jsonify({'success': True, 'message': 'Coupon removed.'})

@app.route('/add_review/<int:product_id>', methods=['POST'])
def add_review(product_id):
    if 'user_id' not in session:
        flash('Please log in to write a review.', 'info')
        return redirect(url_for('login'))
    
    try:
        rating = int(request.form.get('rating', 5))
        comment = sanitize_input(request.form.get('comment', '').strip())
        
        if rating < 1 or rating > 5:
            flash('Please select a valid rating between 1 and 5.', 'error')
            return redirect(url_for('product_detail', product_id=product_id))
        
        existing = Review.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
        if existing:
            existing.rating = rating
            existing.comment = comment
            flash('Your review has been updated!', 'success')
        else:
            review = Review(user_id=session['user_id'], product_id=product_id, rating=rating, comment=comment)
            db.session.add(review)
            flash('Thank you for your review!', 'success')
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('Failed to submit review. Please try again.', 'error')
    
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/my-orders')
def my_orders():
    if 'user_id' not in session:
        flash('Please log in to view your orders.', 'info')
        return redirect(url_for('login'))
    
    orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.created_at.desc()).all()
    return render_template('my_orders.html', orders=orders)

@app.route('/order-success')
def order_success():
    session_id = request.args.get('session_id')
    if session_id and 'user_id' in session:
        # Clear cart after successful payment
        session.pop('cart', None)
        flash('Payment successful! Your order has been confirmed.', 'success')
    return redirect(url_for('index'))

@app.route('/api/search-suggest')
@csrf.exempt
def search_suggest():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    results = Product.query.filter(
        db.or_(
            Product.name.ilike(f'%{q}%'),
            Product.description.ilike(f'%{q}%')
        )
    ).limit(6).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'price': int(p.price),
        'category': p.category.title(),
        'image_url': p.image_url or ''
    } for p in results])

@app.route('/ref/<code>')
def referral_redirect(code):
    session['pending_referral'] = code.upper()
    flash('You were referred by a friend! Register now and use code WELCOME10 for 10% off your first order.', 'info')
    return redirect(url_for('register'))

@app.route('/my-referral')
def my_referral():
    if 'user_id' not in session:
        flash('Please log in to view your referral page.', 'info')
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user.referral_code:
        user.referral_code = secrets.token_urlsafe(6)[:8].upper()
        db.session.commit()
    referred_count = User.query.filter_by(referred_by_id=user.id).count()
    referral_url = f"{get_public_base_url()}/ref/{user.referral_code}"
    return render_template('my_referral.html', user=user, referred_count=referred_count, referral_url=referral_url)

@app.route('/api/recommend/<int:product_id>')
def api_recommendations(product_id):
    recommendations = recommender.get_recommendations(product_id)
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'price': p.price,
        'image_url': p.image_url or '/static/images/placeholder.jpg'
    } for p in recommendations])

def create_sample_data():
    """Create sample products and admin user"""
    # Create a bootstrap admin only when credentials are provided explicitly.
    bootstrap_username = os.environ.get('ADMIN_BOOTSTRAP_USERNAME', '').strip()
    bootstrap_email = os.environ.get('ADMIN_BOOTSTRAP_EMAIL', '').strip()
    bootstrap_password = os.environ.get('ADMIN_BOOTSTRAP_PASSWORD', '')

    if bootstrap_username and bootstrap_email and bootstrap_password:
        admin = User.query.filter_by(username=bootstrap_username).first()
        if not admin:
            admin = User()
            admin.username = bootstrap_username
            admin.email = bootstrap_email
            admin.is_admin = True
            admin.is_email_verified = True
            admin.set_password(bootstrap_password)
            db.session.add(admin)
    
    # Sample products data - TrendVibe Essentials 5-category model
    sample_products = [
        # Beauty Category (K-Beauty Focus)
        {
            'name': 'Niacinamide Serum 10%',
            'description': 'Korean skincare serum with 10% niacinamide for pore refinement and oil control. Perfect for Indian skin.',
            'price': 599.0,
            'category': 'beauty',
            'supplier': 'K-Beauty India',
            'image_url': 'https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?w=400'
        },
        {
            'name': 'Ceramide Moisturizer',
            'description': 'Lightweight K-beauty moisturizer with ceramides and hyaluronic acid. Hydrates without greasiness.',
            'price': 699.0,
            'category': 'beauty',
            'supplier': 'Seoul Skincare Co.',
            'image_url': 'https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=400'
        },
        {
            'name': 'Korean Sheet Mask Set',
            'description': 'Set of 10 Korean sheet masks with snail mucin, collagen, and vitamin C for glowing skin.',
            'price': 399.0,
            'category': 'beauty',
            'supplier': 'Asian Beauty Hub',
            'image_url': 'https://images.unsplash.com/photo-1596755389378-c31d21fd1273?w=400'
        },
        {
            'name': 'Vitamin C Glow Serum',
            'description': 'Brightening serum with 20% vitamin C, perfect for Indian skin tone enhancement and dark spot reduction.',
            'price': 799.0,
            'category': 'beauty',
            'supplier': 'Glow Essentials',
            'image_url': 'https://images.unsplash.com/photo-1617897903246-719242758050?w=400'
        },
        # Lifestyle Category (Eco and Tech Essentials)
        {
            'name': 'Smart Fitness Watch',
            'description': 'Waterproof fitness tracker with heart rate monitor, sleep tracking, and 7-day battery life.',
            'price': 1299.0,
            'category': 'lifestyle',
            'supplier': 'TechVibe India',
            'image_url': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400'
        },
        {
            'name': 'Wireless Bluetooth Earbuds',
            'description': 'True wireless earbuds with active noise cancellation and 24-hour battery case. Perfect for work and workouts.',
            'price': 899.0,
            'category': 'lifestyle',
            'supplier': 'Audio Pro Delhi',
            'image_url': 'https://images.unsplash.com/photo-1572569511254-d8f925fe2cbb?w=400'
        },
        {
            'name': 'Eco-Friendly Water Bottle',
            'description': 'Insulated stainless steel water bottle keeps drinks cold for 24 hours. BPA-free and leak-proof.',
            'price': 449.0,
            'category': 'lifestyle',
            'supplier': 'EcoLife Products',
            'image_url': 'https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400'
        },
        {
            'name': 'Portable Power Bank 20000mAh',
            'description': 'High-capacity power bank with fast charging and multiple ports. Essential for busy urban lifestyle.',
            'price': 999.0,
            'category': 'lifestyle',
            'supplier': 'PowerTech Mumbai',
            'image_url': '/static/images/power_bank.svg'
        },
        # Pooja/Spiritual Category
        {
            'name': 'Brass Pooja Thali Set',
            'description': 'Traditional brass pooja thali with diya, incense holder, and sacred symbols. Perfect for daily worship.',
            'price': 799.0,
            'category': 'spiritual',
            'supplier': 'Sacred Crafts Jaipur',
            'image_url': '/static/images/pooja_thali.svg'
        },
        {
            'name': 'Premium Incense Stick Collection',
            'description': 'Handcrafted incense sticks in 12 fragrances: Sandalwood, Jasmine, Rose, and traditional Indian scents.',
            'price': 399.0,
            'category': 'spiritual',
            'supplier': 'Mysore Agarbatti Co.',
            'image_url': '/static/images/incense_sticks.svg'
        },
        {
            'name': 'Sacred Ganesha Idol',
            'description': 'Beautiful handcrafted brass Ganesha idol for home temple. Brings prosperity and removes obstacles.',
            'price': 1199.0,
            'category': 'spiritual',
            'supplier': 'Divine Sculptures',
            'image_url': '/static/images/ganesha_idol.svg'
        },
        {
            'name': 'Japa Mala Prayer Beads',
            'description': 'Traditional 108-bead sandalwood mala for meditation and prayer. Handmade with authentic materials.',
            'price': 599.0,
            'category': 'spiritual',
            'supplier': 'Spiritual Beads India',
            'image_url': '/static/images/japa_mala.svg'
        },
        # Health & Wellness Category
        {
            'name': 'Ashwagandha Capsules',
            'description': 'Pure Ayurvedic ashwagandha extract capsules for stress relief and energy. 60 capsules, 1-month supply.',
            'price': 699.0,
            'category': 'wellness',
            'supplier': 'Ayur Wellness',
            'image_url': 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400'
        },
        {
            'name': 'Premium Yoga Mat',
            'description': 'Non-slip eco-friendly yoga mat with alignment lines. Perfect for home workouts and yoga practice.',
            'price': 999.0,
            'category': 'wellness',
            'supplier': 'Yoga Essentials',
            'image_url': 'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=400'
        },
        {
            'name': 'Essential Oil Diffuser',
            'description': 'Ultrasonic aromatherapy diffuser with LED lights and timer. Includes lavender and eucalyptus oils.',
            'price': 1299.0,
            'category': 'wellness',
            'supplier': 'Aroma India',
            'image_url': 'https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=400'
        },
        {
            'name': 'Resistance Band Set',
            'description': 'Complete resistance band workout set with 5 resistance levels. Perfect for home fitness routines.',
            'price': 799.0,
            'category': 'wellness',
            'supplier': 'Fit Life India',
            'image_url': 'https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=400'
        },
        # Pet Supplies Category
        {
            'name': 'Interactive Pet Toy Set',
            'description': 'Set of 5 interactive toys for dogs and cats. Includes puzzle feeders, rope toys, and catnip mice.',
            'price': 599.0,
            'category': 'pets',
            'supplier': 'Pet Paradise Mumbai',
            'image_url': 'https://images.unsplash.com/photo-1601758228041-f3b2795255f1?w=400'
        },
        {
            'name': 'Premium Pet Grooming Kit',
            'description': 'Complete grooming kit with nail clippers, brushes, and shampoo. Suitable for dogs and cats.',
            'price': 899.0,
            'category': 'pets',
            'supplier': 'Pet Care Solutions',
            'image_url': 'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=400'
        },
        {
            'name': 'Portable Pet Water Bowl',
            'description': 'Collapsible silicone water bowl for travel and outdoor activities with your pets. BPA-free and dishwasher safe.',
            'price': 299.0,
            'category': 'pets',
            'supplier': 'Travel Pets India',
            'image_url': 'https://images.unsplash.com/photo-1615751072497-5f5169febe17?w=400'
        },
        {
            'name': 'Eco-Friendly Pet Leash',
            'description': 'Durable hemp-fiber pet leash with comfortable grip handle. Available in multiple colors and sizes.',
            'price': 399.0,
            'category': 'pets',
            'supplier': 'Green Pet Products',
            'image_url': 'https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=400'
        }
    ]
    
    for product_data in sample_products:
        existing = Product.query.filter_by(name=product_data['name']).first()
        if not existing:
            product = Product()
            product.name = product_data['name']
            product.description = product_data['description']
            product.price = product_data['price']
            product.category = product_data['category']
            product.supplier = product_data['supplier']
            product.image_url = product_data['image_url']
            db.session.add(product)
    
    db.session.commit()
    
    # Create sample coupons
    sample_coupons = [
        {'code': 'WELCOME10', 'discount_percent': 10.0, 'max_uses': 500},
        {'code': 'BEAUTY20', 'discount_percent': 20.0, 'max_uses': 100},
        {'code': 'WELLNESS15', 'discount_percent': 15.0, 'max_uses': 200},
        {'code': 'TRENDVIBE5', 'discount_percent': 5.0, 'max_uses': 1000},
    ]
    for coupon_data in sample_coupons:
        existing = Coupon.query.filter_by(code=coupon_data['code']).first()
        if not existing:
            coupon = Coupon(**coupon_data)
            db.session.add(coupon)
    
    db.session.commit()

def migrate_db():
    """Add new columns to existing DB tables without dropping data."""
    migrations = [
        "ALTER TABLE user ADD COLUMN referral_code VARCHAR(20)",
        "ALTER TABLE user ADD COLUMN referred_by_id INTEGER",
    ]
    with db.engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(db.text(sql))
                conn.commit()
            except Exception:
                pass

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        migrate_db()
        create_sample_data()
        recommender.train()
    
    # Run on all interfaces and port 5000 for local development and generic hosts
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)

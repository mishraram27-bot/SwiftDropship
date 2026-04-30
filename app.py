import os

from dotenv import load_dotenv
from flask import Flask, request

from extensions import csrf, db
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.legal import legal_bp
from routes.shop import shop_bp
from services.recommender import ProductRecommender
from services.sample_data import create_sample_data
from utils.helpers import configure_template_helpers

try:
    import stripe
except ModuleNotFoundError:
    stripe = None


load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "trendvibe-dev-key-2025-replace-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///dropship.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Security configurations
app.config["SESSION_COOKIE_SECURE"] = False  # Set to True in production with HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db.init_app(app)
csrf.init_app(app)
configure_template_helpers(app)

recommender = ProductRecommender()
app.extensions["recommender"] = recommender

if stripe is not None:
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
app.extensions["stripe_client"] = stripe

app.register_blueprint(shop_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(legal_bp)


@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://js.stripe.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://images.unsplash.com https://via.placeholder.com https://cdn.jsdelivr.net; "
        "connect-src 'self' https://api.stripe.com; "
        "frame-src https://checkout.stripe.com https://js.stripe.com; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    if app.config.get("SESSION_COOKIE_SECURE"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    if request.endpoint in ["login", "register", "admin_dashboard", "checkout"]:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_sample_data()
        recommender.train()

    app.run(host="0.0.0.0", port=5000, debug=True)

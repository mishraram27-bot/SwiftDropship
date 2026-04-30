import re
import secrets
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


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

    def set_password(self, password):
        if not self.validate_password_strength(password):
            raise ValueError("Password does not meet security requirements")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def validate_password_strength(password):
        if len(password) < 8:
            return False
        if not re.search(r"[A-Z]", password):
            return False
        if not re.search(r"[a-z]", password):
            return False
        if not re.search(r"\d", password):
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
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="pending")
    shipping_address = db.Column(db.Text, nullable=False)
    payment_status = db.Column(db.String(50), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("orders", lazy=True))


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    order = db.relationship("Order", backref=db.backref("items", lazy=True))
    product = db.relationship("Product", backref=db.backref("order_items", lazy=True))


class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "product_id", name="unique_user_product_wishlist"),)

    user = db.relationship("User", backref=db.backref("wishlist_items", lazy=True))
    product = db.relationship("Product", backref=db.backref("wishlist_items", lazy=True))


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
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "product_id", name="unique_user_product_review"),)

    user = db.relationship("User", backref=db.backref("reviews", lazy=True))
    product = db.relationship("Product", backref=db.backref("reviews", lazy=True))

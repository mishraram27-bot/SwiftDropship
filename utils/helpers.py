from functools import wraps

from flask import flash, redirect, session, url_for

from models import Product, User, Wishlist


def get_cart_items():
    """Get cart items from session."""
    cart = session.get("cart", {})
    items = []
    total = 0

    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.price * quantity
            items.append({"product": product, "quantity": quantity, "total": item_total})
            total += item_total

    return items, total


def is_admin():
    """Check if current user is admin."""
    if "user_id" not in session:
        return False
    user = User.query.get(session["user_id"])
    return bool(user and user.is_admin)


def get_wishlist_count():
    """Get wishlist count for current user."""
    if "user_id" not in session:
        return 0
    return Wishlist.query.filter_by(user_id=session["user_id"]).count()


def is_in_wishlist(product_id):
    """Check if product is in user's wishlist."""
    if "user_id" not in session:
        return False
    return (
        Wishlist.query.filter_by(user_id=session["user_id"], product_id=product_id).first()
        is not None
    )


def admin_required(f):
    """Decorator to require admin access."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def configure_template_helpers(app):
    app.jinja_env.globals.update(
        is_admin=is_admin,
        get_wishlist_count=get_wishlist_count,
        is_in_wishlist=is_in_wishlist,
    )

    @app.context_processor
    def inject_user():
        return dict(is_admin=is_admin)

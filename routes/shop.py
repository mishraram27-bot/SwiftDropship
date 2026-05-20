from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for

from extensions import db
from models import Coupon, Order, OrderItem, Product, Review, Wishlist
from utils.helpers import get_cart_items
from utils.security import sanitize_input

shop_bp = Blueprint("shop", __name__)


@shop_bp.route("/", endpoint="index")
def index():
    search_query = request.args.get("search", "")
    category_filter = request.args.get("category", "")
    sort_by = request.args.get("sort", "")
    min_price = request.args.get("min_price", "")
    max_price = request.args.get("max_price", "")

    query = Product.query

    if search_query:
        query = query.filter(
            db.or_(Product.name.ilike(f"%{search_query}%"), Product.description.ilike(f"%{search_query}%"))
        )

    if category_filter:
        query = query.filter(Product.category == category_filter)

    if min_price:
        try:
            query = query.filter(Product.price >= float(min_price))
        except (ValueError, TypeError):
            pass

    if max_price:
        try:
            query = query.filter(Product.price <= float(max_price))
        except (ValueError, TypeError):
            pass

    if sort_by == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort_by == "newest":
        query = query.order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.id.asc())

    products = query.all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [cat[0] for cat in categories]

    return render_template(
        "index.html",
        products=products,
        categories=categories,
        search_query=search_query,
        category_filter=category_filter,
        sort_by=sort_by,
        min_price=min_price,
        max_price=max_price,
    )


@shop_bp.route("/product/<int:product_id>", endpoint="product_detail")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    recommender = current_app.extensions["recommender"]
    recommendations = recommender.get_recommendations(product_id)
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).all()
    user_review = None
    if "user_id" in session:
        user_review = Review.query.filter_by(user_id=session["user_id"], product_id=product_id).first()
    avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0
    return render_template(
        "product_detail.html",
        product=product,
        recommendations=recommendations,
        reviews=reviews,
        user_review=user_review,
        avg_rating=avg_rating,
    )


@shop_bp.route("/add_to_cart/<int:product_id>", methods=["POST"], endpoint="add_to_cart")
def add_to_cart(product_id):
    quantity = int(request.form.get("quantity", 1))

    if "cart" not in session:
        session["cart"] = {}

    cart = session["cart"]
    product_id_str = str(product_id)

    if product_id_str in cart:
        cart[product_id_str] += quantity
    else:
        cart[product_id_str] = quantity

    session["cart"] = cart
    flash("Product added to cart!", "success")
    return redirect(url_for("product_detail", product_id=product_id))


@shop_bp.route("/cart", endpoint="cart")
def cart():
    items, total = get_cart_items()
    return render_template("cart.html", items=items, total=total)


@shop_bp.route("/update_cart", methods=["POST"], endpoint="update_cart")
def update_cart():
    product_id = request.form.get("product_id")
    action = request.form.get("action")

    if "cart" in session and product_id in session["cart"]:
        if action == "increase":
            session["cart"][product_id] += 1
        elif action == "decrease":
            if session["cart"][product_id] > 1:
                session["cart"][product_id] -= 1
            else:
                del session["cart"][product_id]
        elif action == "remove":
            del session["cart"][product_id]

        session.modified = True

    return redirect(url_for("cart"))


@shop_bp.route("/checkout", endpoint="checkout")
def checkout():
    if "user_id" not in session:
        flash("Please log in to checkout", "error")
        return redirect(url_for("login"))

    items, total = get_cart_items()
    if not items:
        flash("Your cart is empty", "error")
        return redirect(url_for("cart"))

    return render_template("checkout.html", items=items, total=total)


@shop_bp.route("/create-checkout-session", methods=["POST"], endpoint="create_checkout_session")
def create_checkout_session():
    if "user_id" not in session:
        return redirect(url_for("login"))

    items, _ = get_cart_items()
    if not items:
        flash("Your cart is empty", "error")
        return redirect(url_for("cart"))

    stripe_client = current_app.extensions.get("stripe_client")
    if stripe_client is None:
        flash("Online payment is currently unavailable. Please use the demo order flow.", "info")
        return redirect(url_for("checkout"))

    base_url = request.url_root.rstrip("/")

    try:
        line_items = []
        for item in items:
            line_items.append(
                {
                    "price_data": {
                        "currency": "inr",
                        "product_data": {
                            "name": item["product"].name,
                            "description": item["product"].description[:100],
                        },
                        "unit_amount": int(item["product"].price * 100),
                    },
                    "quantity": item["quantity"],
                }
            )

        checkout_session = stripe_client.checkout.Session.create(
            line_items=line_items,
            mode="payment",
            success_url=f"{base_url}/order-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/cart",
            metadata={"user_id": session["user_id"], "cart_items": str(len(items))},
        )
        return redirect(checkout_session.url or url_for("cart"), code=303)
    except Exception as exc:
        flash(f"Payment initialization failed: {str(exc)}", "error")
        return redirect(url_for("cart"))


@shop_bp.route("/process_order", methods=["POST"], endpoint="process_order")
def process_order():
    if "user_id" not in session:
        return redirect(url_for("login"))

    items, total = get_cart_items()
    if not items:
        flash("Your cart is empty", "error")
        return redirect(url_for("cart"))

    address = sanitize_input(request.form.get("address", "").strip())
    city = sanitize_input(request.form.get("city", "").strip())
    state = sanitize_input(request.form.get("state", "").strip())
    postal_code = request.form.get("postal_code", "").strip()
    phone = request.form.get("phone", "").strip()

    shipping_address = f"{address}, {city}, {state} - {postal_code}, Phone: +91{phone}"

    discount_percent = session.pop("coupon_discount", 0)
    coupon_code = session.pop("coupon_code", None)
    discount_amount = total * (discount_percent / 100)
    final_total = total - discount_amount

    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code).first()
        if coupon and coupon.is_valid():
            coupon.uses_count += 1
            db.session.add(coupon)

    order = Order()
    order.user_id = session["user_id"]
    order.total_amount = final_total
    order.shipping_address = shipping_address
    order.status = "confirmed"
    order.payment_status = "completed"
    db.session.add(order)
    db.session.flush()

    for item in items:
        order_item = OrderItem()
        order_item.order_id = order.id
        order_item.product_id = item["product"].id
        order_item.quantity = item["quantity"]
        order_item.price = item["product"].price
        db.session.add(order_item)

    db.session.commit()
    session.pop("cart", None)

    flash("Order placed successfully!", "success")
    return redirect(url_for("order_confirmation", order_id=order.id))


@shop_bp.route("/order_confirmation/<int:order_id>", endpoint="order_confirmation")
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != session.get("user_id"):
        flash("Access denied", "error")
        return redirect(url_for("index"))

    return render_template("order_confirmation.html", order=order)


@shop_bp.route("/wishlist", endpoint="wishlist")
def wishlist():
    if "user_id" not in session:
        flash("Please log in to view your wishlist.", "info")
        return redirect(url_for("login"))

    user_wishlist = Wishlist.query.filter_by(user_id=session["user_id"]).all()
    wishlist_products = [item.product for item in user_wishlist]

    return render_template("wishlist.html", products=wishlist_products)


@shop_bp.route("/add_to_wishlist/<int:product_id>", methods=["POST"], endpoint="add_to_wishlist")
def add_to_wishlist(product_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please log in to add items to your wishlist."})

    existing = Wishlist.query.filter_by(user_id=session["user_id"], product_id=product_id).first()
    if existing:
        return jsonify({"success": False, "message": "Item already in your wishlist!"})

    try:
        wishlist_item = Wishlist(user_id=session["user_id"], product_id=product_id)
        db.session.add(wishlist_item)
        db.session.commit()

        wishlist_count = Wishlist.query.filter_by(user_id=session["user_id"]).count()

        return jsonify(
            {"success": True, "message": "Added to wishlist!", "wishlist_count": wishlist_count}
        )
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "message": "Failed to add to wishlist."})


@shop_bp.route("/remove_from_wishlist/<int:product_id>", methods=["POST"], endpoint="remove_from_wishlist")
def remove_from_wishlist(product_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please log in."})

    try:
        wishlist_item = Wishlist.query.filter_by(user_id=session["user_id"], product_id=product_id).first()
        if wishlist_item:
            db.session.delete(wishlist_item)
            db.session.commit()

            wishlist_count = Wishlist.query.filter_by(user_id=session["user_id"]).count()

            return jsonify(
                {"success": True, "message": "Removed from wishlist!", "wishlist_count": wishlist_count}
            )
        return jsonify({"success": False, "message": "Item not found in wishlist."})
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "message": "Failed to remove from wishlist."})


@shop_bp.route("/apply_coupon", methods=["POST"], endpoint="apply_coupon")
def apply_coupon():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please log in to apply a coupon."})

    code = request.form.get("coupon_code", "").strip().upper()
    if not code:
        return jsonify({"success": False, "message": "Please enter a coupon code."})

    coupon = Coupon.query.filter_by(code=code).first()
    if not coupon or not coupon.is_valid():
        return jsonify({"success": False, "message": "Invalid or expired coupon code."})

    session["coupon_code"] = code
    session["coupon_discount"] = coupon.discount_percent
    return jsonify(
        {
            "success": True,
            "message": f"Coupon applied! {int(coupon.discount_percent)}% discount.",
            "discount_percent": coupon.discount_percent,
        }
    )


@shop_bp.route("/remove_coupon", methods=["POST"], endpoint="remove_coupon")
def remove_coupon():
    session.pop("coupon_code", None)
    session.pop("coupon_discount", None)
    return jsonify({"success": True, "message": "Coupon removed."})


@shop_bp.route("/add_review/<int:product_id>", methods=["POST"], endpoint="add_review")
def add_review(product_id):
    if "user_id" not in session:
        flash("Please log in to write a review.", "info")
        return redirect(url_for("login"))

    try:
        rating = int(request.form.get("rating", 5))
        comment = sanitize_input(request.form.get("comment", "").strip())

        if rating < 1 or rating > 5:
            flash("Please select a valid rating between 1 and 5.", "error")
            return redirect(url_for("product_detail", product_id=product_id))

        existing = Review.query.filter_by(user_id=session["user_id"], product_id=product_id).first()
        if existing:
            existing.rating = rating
            existing.comment = comment
            flash("Your review has been updated!", "success")
        else:
            review = Review(user_id=session["user_id"], product_id=product_id, rating=rating, comment=comment)
            db.session.add(review)
            flash("Thank you for your review!", "success")

        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to submit review. Please try again.", "error")

    return redirect(url_for("product_detail", product_id=product_id))


@shop_bp.route("/my-orders", endpoint="my_orders")
def my_orders():
    if "user_id" not in session:
        flash("Please log in to view your orders.", "info")
        return redirect(url_for("login"))

    orders = Order.query.filter_by(user_id=session["user_id"]).order_by(Order.created_at.desc()).all()
    return render_template("my_orders.html", orders=orders)


@shop_bp.route("/order-success", endpoint="order_success")
def order_success():
    session_id = request.args.get("session_id")
    if session_id and "user_id" in session:
        session.pop("cart", None)
        flash("Payment successful! Your order has been confirmed.", "success")
    return redirect(url_for("index"))


@shop_bp.route("/api/recommend/<int:product_id>", endpoint="api_recommendations")
def api_recommendations(product_id):
    recommender = current_app.extensions["recommender"]
    recommendations = recommender.get_recommendations(product_id)
    return jsonify(
        [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "image_url": p.image_url or "/static/images/placeholder.jpg",
            }
            for p in recommendations
        ]
    )

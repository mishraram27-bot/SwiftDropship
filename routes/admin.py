from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from extensions import db
from models import Order, Product
from utils.helpers import admin_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin", endpoint="admin_dashboard")
@admin_required
def admin_dashboard():
    products = Product.query.all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/dashboard.html", products=products, orders=orders)


@admin_bp.route("/admin/add_product", methods=["GET", "POST"], endpoint="add_product")
@admin_required
def add_product():
    if request.method == "POST":
        product = Product()
        product.name = request.form.get("name")
        product.description = request.form.get("description")
        product.price = float(request.form.get("price") or 0)
        product.category = request.form.get("category")
        product.image_url = request.form.get("image_url")
        product.supplier = request.form.get("supplier")
        product.stock = int(request.form.get("stock") or 999)
        db.session.add(product)
        db.session.commit()

        current_app.extensions["recommender"].train()

        flash("Product added successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/add_product.html")

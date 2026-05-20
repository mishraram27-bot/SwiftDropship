from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from extensions import db
from models import User
from utils.security import sanitize_input, validate_email_format

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"], endpoint="register")
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        username = sanitize_input(username.strip()) if username else ""
        email = sanitize_input(email.strip()) if email else ""

        if not username or len(username) < 3:
            flash("Username must be at least 3 characters long", "error")
            return render_template("register.html")

        if not validate_email_format(email):
            flash("Please provide a valid email address", "error")
            return render_template("register.html")

        if not User.validate_password_strength(password):
            flash(
                "Password must be at least 8 characters with uppercase, lowercase, number, and special character",
                "error",
            )
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "error")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("Email already registered", "error")
            return render_template("register.html")

        try:
            user = User()
            user.username = username
            user.email = email
            user.set_password(password)
            user.generate_email_verification_token()

            db.session.add(user)
            db.session.commit()

            user.is_email_verified = True
            db.session.commit()

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))

        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("register.html")
        except Exception:
            flash("Registration failed. Please try again.", "error")
            return render_template("register.html")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Login successful!", "success")
            return redirect(url_for("index"))
        flash("Invalid username or password", "error")

    return render_template("login.html")


@auth_bp.route("/logout", endpoint="logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

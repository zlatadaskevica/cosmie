"""
Main Flask application.

Responsible for:
- app configuration
- routes
- coordination between services and templates
"""

import os
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

# Import methods from services
from user_service import (
    validate_password,
    authenticate_user,
    create_user,
    get_enabled_api_codes,
)

from nasa_service import (
    fetch_apod_data,
    fetch_mars_data,
    fetch_neo_data,
    fetch_donki_data,
    fetch_image_library_data,
)

# ================= ENVIRONMENT =================

# Load variables from .env if present
load_dotenv()

# ================= FLASK CONFIG =================

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///cosmie.db",
    )
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db = SQLAlchemy(app)

# NASA API key from environment
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")

# Available dashboard sectors
API_OPTIONS = [
    ("apod", "Astronomy Picture of the Day"),
    ("mars", "Mars Weather"),
    ("neo", "Near Earth Objects"),
    ("donki", "DONKI Coronal Mass Ejections"),
    ("images", "NASA Image Library"),
]

# ================= DATABASE MODELS =================

class User(db.Model):
    # Stores user credentials and has a relationship to preferences
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # One-to-many relationship with preferences
    preferences = db.relationship(
        "Preference",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Preference(db.Model):
    # Stores which API sectors are enabled for each user

    __tablename__ = "preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    api_code = db.Column(db.String(20), nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)

    # Prevent duplicate preference rows
    __table_args__ = (
        UniqueConstraint("user_id", "api_code", name="unique_user_api_preference"),
    )

# ================= AUTHENTICATION DECORATOR =================

def login_required(view_func):
    # Protect routes so only logged-in users can access them

    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    wrapped_view.__name__ = view_func.__name__
    return wrapped_view

# ================= ROUTES =================

@app.route("/")
def landing_page():
    # Public landing page
    return render_template("landing.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    # User registration

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Basic validation
        if not username:
            flash("Username is required.", "error")
            return render_template("signup.html")

        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists.", "error")
            return render_template("signup.html")

        # Validate password strength
        password_error = validate_password(password)
        if password_error:
            flash(password_error, "error")
            return render_template("signup.html")

        # Create user via service layer
        create_user(db, User, Preference, username, password, API_OPTIONS)

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # User login

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Authenticate via service
        user = authenticate_user(User, username, password)
        if not user:
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        # Store minimal identity in session
        session["user_id"] = user.id
        session["username"] = user.username

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    # Log out current user
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("landing_page"))


@app.route("/dashboard")
@login_required
def dashboard():
    # Personalized dashboard based on user preferences

    enabled_codes = get_enabled_api_codes(Preference, session["user_id"])
    sectors = []

    # Each block adds a sector only if enabled
    if "apod" in enabled_codes:
        sectors.append({
            "code": "apod",
            "title": "Astronomy Picture of the Day",
            "description": "Daily highlighted astronomy image with explanation.",
            "data": fetch_apod_data(NASA_API_KEY),
        })

    if "mars" in enabled_codes:
        sectors.append({
            "code": "mars",
            "title": "Mars Weather",
            "description": "Latest available Mars weather data from the InSight mission.",
            "data": fetch_mars_data(NASA_API_KEY),
        })

    if "neo" in enabled_codes:
        sectors.append({
            "code": "neo",
            "title": "Near Earth Objects",
            "description": "Asteroid pass data (data for a one-day window).",
            "data": fetch_neo_data(NASA_API_KEY),
        })

    if "donki" in enabled_codes:
        sectors.append({
            "code": "donki",
            "title": "DONKI CME",
            "description": "Recent Coronal Mass Ejection events (last 30 days).",
            "data": fetch_donki_data(NASA_API_KEY),
        })

    if "images" in enabled_codes:
        sectors.append({
            "code": "images",
            "title": "NASA Image Library",
            "description": "Moon related image discoveries.",
            "data": fetch_image_library_data(),
        })

    return render_template("dashboard.html", sectors=sectors)


@app.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    # Allow user to enable/disable API sectors

    user_id = session["user_id"]

    if request.method == "POST":
        selected_codes = set(request.form.getlist("apis"))
        prefs = Preference.query.filter_by(user_id=user_id).all()

        # Update each preference
        for pref in prefs:
            pref.enabled = pref.api_code in selected_codes

        db.session.commit()
        flash("Preferences updated successfully.", "success")
        return redirect(url_for("dashboard"))

    stored = Preference.query.filter_by(user_id=user_id).all()
    enabled_codes = {p.api_code for p in stored if p.enabled}

    return render_template(
        "preferences.html",
        api_options=API_OPTIONS,
        enabled_codes=enabled_codes,
    )

# ================= APPLICATION ENTRY POINT =================

# Ensure tables exist
with app.app_context():
    db.create_all()

# Run dev server
if __name__ == "__main__":
    app.run(debug=True)

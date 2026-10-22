"""
routes/dashboard.py
-------------------
The main dashboard page and JSON API endpoints for charts.
"""

from datetime import datetime, timezone
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user

from models.transaction import (
    get_summary, get_monthly_totals, get_category_totals, get_recent_transactions
)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    """Render the dashboard page."""
    now = datetime.now(timezone.utc)
    db = current_app.db

    # Summary for current month
    summary = get_summary(db, current_user.id, year=now.year, month=now.month)
    recent  = get_recent_transactions(db, current_user.id, limit=5)

    return render_template(
        "dashboard/index.html",
        summary=summary,
        recent=recent,
        current_month=now.strftime("%B %Y"),
        now=now,
    )


# ---------------------------------------------------------------------------
# JSON API — used by JavaScript charts (Chart.js fetches these)
# ---------------------------------------------------------------------------

@dashboard_bp.route("/api/summary")
@login_required
def api_summary():
    """Return income/expenses/balance totals as JSON."""
    now = datetime.now(timezone.utc)
    db = current_app.db
    year  = request.args.get("year",  now.year,  type=int)
    month = request.args.get("month", now.month, type=int)
    data  = get_summary(db, current_user.id, year=year, month=month)
    return jsonify(data)


@dashboard_bp.route("/api/monthly-chart")
@login_required
def api_monthly_chart():
    """Return 12-month income vs expense totals for the bar chart."""
    now  = datetime.now(timezone.utc)
    year = request.args.get("year", now.year, type=int)
    db   = current_app.db
    data = get_monthly_totals(db, current_user.id, year=year)
    return jsonify(data)


@dashboard_bp.route("/api/category-chart")
@login_required
def api_category_chart():
    """Return per-category expense totals for the doughnut chart."""
    now   = datetime.now(timezone.utc)
    db    = current_app.db
    year  = request.args.get("year",  now.year,  type=int)
    month = request.args.get("month", now.month, type=int)
    data  = get_category_totals(db, current_user.id, year=year, month=month)
    return jsonify(data)

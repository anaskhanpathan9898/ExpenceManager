"""
routes/budget.py
----------------
Routes for setting, viewing, and deleting monthly budgets.
Also provides a JSON endpoint for budget-status (used by the progress bars).
"""

from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, current_app, jsonify,
)
from flask_login import login_required, current_user

from models.budget import (
    BUDGET_CATEGORIES, set_budget, get_budgets,
    get_budget_by_id, delete_budget,
)
from models.transaction import get_category_totals, get_summary

budget_bp = Blueprint("budget", __name__, url_prefix="/budget")


def _current_month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


# ---------------------------------------------------------------------------
# Budget overview page
# ---------------------------------------------------------------------------

@budget_bp.route("/")
@login_required
def index():
    db    = current_app.db
    month = request.args.get("month", _current_month())

    budgets = get_budgets(db, current_user.id, month)

    # Get actual spending per category for this month so we can show progress
    year_int, month_int = map(int, month.split("-"))
    cat_totals = {
        r["_id"]: r["total"]
        for r in get_category_totals(db, current_user.id, year=year_int, month=month_int)
    }
    total_summary = get_summary(db, current_user.id, year=year_int, month=month_int)

    # Attach spent amount and percentage to each budget doc
    for b in budgets:
        if b["category"] == "Total":
            spent = total_summary["expenses"]
        else:
            spent = cat_totals.get(b["category"], 0.0)
        b["spent"]      = spent
        b["percent"]    = round((spent / b["limit_amount"]) * 100, 1) if b["limit_amount"] else 0
        b["status"]     = (
            "danger"  if b["percent"] >= 100 else
            "warning" if b["percent"] >= 80  else
            "good"
        )

    return render_template(
        "budget/index.html",
        budgets=budgets,
        categories=BUDGET_CATEGORIES,
        selected_month=month,
    )


# ---------------------------------------------------------------------------
# Set (create or update) a budget
# ---------------------------------------------------------------------------

@budget_bp.route("/set", methods=["POST"])
@login_required
def set_budget_route():
    db           = current_app.db
    month        = request.form.get("month", _current_month())
    category     = request.form.get("category", "")
    limit_str    = request.form.get("limit_amount", "0")

    errors = []
    if category not in BUDGET_CATEGORIES:
        errors.append("Invalid category.")
    try:
        limit = float(limit_str)
        if limit <= 0:
            raise ValueError
    except ValueError:
        errors.append("Budget limit must be a positive number.")

    if errors:
        for err in errors:
            flash(err, "danger")
    else:
        set_budget(db, current_user.id, month, category, limit)
        flash(f"Budget for '{category}' in {month} saved.", "success")

    return redirect(url_for("budget.index", month=month))


# ---------------------------------------------------------------------------
# Delete a budget
# ---------------------------------------------------------------------------

@budget_bp.route("/delete/<budget_id>", methods=["POST"])
@login_required
def delete_budget_route(budget_id):
    db     = current_app.db
    budget = get_budget_by_id(db, budget_id, current_user.id)
    month  = request.form.get("month", _current_month())

    if not budget:
        flash("Budget not found.", "danger")
    else:
        delete_budget(db, budget_id, current_user.id)
        flash("Budget removed.", "success")

    return redirect(url_for("budget.index", month=month))


# ---------------------------------------------------------------------------
# JSON API for budget status (used by JS for real-time progress bars)
# ---------------------------------------------------------------------------

@budget_bp.route("/api/budget-status")
@login_required
def api_budget_status():
    db    = current_app.db
    month = request.args.get("month", _current_month())

    budgets = get_budgets(db, current_user.id, month)
    year_int, month_int = map(int, month.split("-"))
    cat_totals = {
        r["_id"]: r["total"]
        for r in get_category_totals(db, current_user.id, year=year_int, month=month_int)
    }
    total_summary = get_summary(db, current_user.id, year=year_int, month=month_int)

    result = []
    for b in budgets:
        spent   = total_summary["expenses"] if b["category"] == "Total" else cat_totals.get(b["category"], 0.0)
        percent = round((spent / b["limit_amount"]) * 100, 1) if b["limit_amount"] else 0
        result.append({
            "category":     b["category"],
            "limit_amount": b["limit_amount"],
            "spent":        spent,
            "percent":      percent,
        })

    return jsonify(result)

"""
routes/transactions.py
----------------------
CRUD routes for income and expense transactions.
"""

from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, current_app,
)
from flask_login import login_required, current_user
from bson import ObjectId

from models.transaction import (
    CATEGORIES, TRANSACTION_TYPES,
    create_transaction, get_transactions, get_transaction_by_id,
    update_transaction, delete_transaction,
)

transactions_bp = Blueprint("transactions", __name__, url_prefix="/transactions")


def _parse_date(date_str):
    """Convert a date string (YYYY-MM-DD) to a UTC datetime object."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# List / Search / Filter
# ---------------------------------------------------------------------------

@transactions_bp.route("/")
@login_required
def list_transactions():
    db   = current_app.db
    page = request.args.get("page", 1, type=int)

    filters = {
        "type":      request.args.get("type", ""),
        "category":  request.args.get("category", ""),
        "search":    request.args.get("search", ""),
        "date_from": _parse_date(request.args.get("date_from", "")) if request.args.get("date_from") else None,
        "date_to":   _parse_date(request.args.get("date_to", ""))   if request.args.get("date_to")   else None,
    }

    transactions, total = get_transactions(db, current_user.id, filters=filters, page=page)
    total_pages = max(1, -(-total // 10))  # ceiling division

    return render_template(
        "transactions/list.html",
        transactions=transactions,
        filters=filters,
        categories=CATEGORIES,
        page=page,
        total_pages=total_pages,
        total_count=total,
    )


# ---------------------------------------------------------------------------
# Add
# ---------------------------------------------------------------------------

@transactions_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    db = current_app.db

    if request.method == "POST":
        type_       = request.form.get("type", "")
        amount_str  = request.form.get("amount", "0")
        category    = request.form.get("category", "")
        description = request.form.get("description", "")
        date_str    = request.form.get("date", "")

        errors = []
        if type_ not in TRANSACTION_TYPES:
            errors.append("Please select a valid transaction type.")
        if category not in CATEGORIES:
            errors.append("Please select a valid category.")
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            errors.append("Amount must be a positive number.")
            amount = 0

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("transactions/form.html",
                                   categories=CATEGORIES,
                                   form_data=request.form,
                                   action="Add")

        create_transaction(
            db, current_user.id, type_, amount, category, description,
            _parse_date(date_str)
        )
        flash("Transaction added successfully.", "success")
        return redirect(url_for("transactions.list_transactions"))

    return render_template("transactions/form.html",
                           categories=CATEGORIES,
                           form_data={},
                           action="Add")


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------

@transactions_bp.route("/edit/<transaction_id>", methods=["GET", "POST"])
@login_required
def edit(transaction_id):
    db  = current_app.db
    txn = get_transaction_by_id(db, transaction_id, current_user.id)

    if not txn:
        flash("Transaction not found.", "danger")
        return redirect(url_for("transactions.list_transactions"))

    if request.method == "POST":
        type_       = request.form.get("type", "")
        amount_str  = request.form.get("amount", "0")
        category    = request.form.get("category", "")
        description = request.form.get("description", "")
        date_str    = request.form.get("date", "")

        errors = []
        if type_ not in TRANSACTION_TYPES:
            errors.append("Please select a valid transaction type.")
        if category not in CATEGORIES:
            errors.append("Please select a valid category.")
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            errors.append("Amount must be a positive number.")
            amount = 0

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("transactions/form.html",
                                   categories=CATEGORIES,
                                   form_data=request.form,
                                   action="Edit")

        update_transaction(db, transaction_id, current_user.id, {
            "type":        type_,
            "amount":      float(amount_str),
            "category":    category,
            "description": description.strip(),
            "date":        _parse_date(date_str),
        })
        flash("Transaction updated successfully.", "success")
        return redirect(url_for("transactions.list_transactions"))

    # Pre-fill the form with existing values
    form_data = {
        "type":        txn["type"],
        "amount":      txn["amount"],
        "category":    txn["category"],
        "description": txn["description"],
        "date":        txn["date"].strftime("%Y-%m-%d"),
    }
    return render_template("transactions/form.html",
                           categories=CATEGORIES,
                           form_data=form_data,
                           action="Edit",
                           transaction_id=transaction_id)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@transactions_bp.route("/delete/<transaction_id>", methods=["POST"])
@login_required
def delete(transaction_id):
    db  = current_app.db
    txn = get_transaction_by_id(db, transaction_id, current_user.id)

    if not txn:
        flash("Transaction not found.", "danger")
    else:
        delete_transaction(db, transaction_id, current_user.id)
        flash("Transaction deleted.", "success")

    return redirect(url_for("transactions.list_transactions"))

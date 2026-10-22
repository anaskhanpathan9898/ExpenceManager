"""
models/budget.py
----------------
Helper functions for the 'budgets' collection.

Each budget document:
{
    "_id":          ObjectId,
    "user_id":      ObjectId,
    "month":        "YYYY-MM",    ← e.g. "2026-10"
    "category":     str,          ← category name OR "Total" for an overall limit
    "limit_amount": float,
}
"""

from bson import ObjectId
from models.transaction import CATEGORIES

BUDGET_CATEGORIES = ["Total"] + CATEGORIES


def set_budget(db, user_id, month, category, limit_amount):
    """
    Create or update a budget for a user/month/category combination.
    Uses upsert so calling it twice just updates the limit.
    """
    db.budgets.update_one(
        {
            "user_id": ObjectId(user_id),
            "month": month,
            "category": category,
        },
        {
            "$set": {
                "user_id": ObjectId(user_id),
                "month": month,
                "category": category,
                "limit_amount": float(limit_amount),
            }
        },
        upsert=True,
    )


def get_budgets(db, user_id, month):
    """Return all budget documents for a user in a given month."""
    return list(db.budgets.find({"user_id": ObjectId(user_id), "month": month}))


def get_budget_by_id(db, budget_id, user_id):
    """Return a single budget, only if it belongs to user_id."""
    return db.budgets.find_one({
        "_id": ObjectId(budget_id),
        "user_id": ObjectId(user_id),
    })


def delete_budget(db, budget_id, user_id):
    """Delete a budget only if it belongs to user_id."""
    db.budgets.delete_one({
        "_id": ObjectId(budget_id),
        "user_id": ObjectId(user_id),
    })


def ensure_indexes(db):
    """Create compound index for fast budget lookups."""
    db.budgets.create_index([("user_id", 1), ("month", 1), ("category", 1)], unique=True)

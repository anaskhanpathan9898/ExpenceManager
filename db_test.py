"""
db_test.py — Step 2: Verify MongoDB connection, database name, collections, and indexes.
Run with: python3 db_test.py
This script does NOT modify any data.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

MONGO_URI  = os.environ.get("MONGO_URI", "mongodb://localhost:27017/expense_tracker")
DB_NAME    = MONGO_URI.split("/")[-1].split("?")[0]

print("=" * 55)
print("  Expense Tracker — MongoDB Connection Test")
print("=" * 55)
print(f"  URI (host only): mongodb://127.0.0.1:27017")
print(f"  Database name  : {DB_NAME}")
print()

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Force a real network round-trip
    client.admin.command("ping")
    print("  [OK] Connected to MongoDB successfully.")
except (ConnectionFailure, ServerSelectionTimeoutError) as e:
    print(f"  [FAIL] Cannot connect: {e}")
    sys.exit(1)

db = client[DB_NAME]

# --- Collections ---
existing_cols = db.list_collection_names()
print(f"\n  Collections in '{DB_NAME}': {existing_cols if existing_cols else '(none yet — will be created on first use)'}")

# --- Indexes ---
for col_name in ["users", "transactions", "budgets"]:
    if col_name in existing_cols:
        idxs = list(db[col_name].list_indexes())
        idx_names = [i["name"] for i in idxs]
        print(f"  Indexes on {col_name}: {idx_names}")
    else:
        print(f"  Collection '{col_name}' does not exist yet (normal on first run).")

# --- Document counts (read-only) ---
print()
for col_name in existing_cols:
    count = db[col_name].count_documents({})
    print(f"  {col_name}: {count} document(s)")

print()
print("  [DONE] All checks passed. No data was modified.")
print("=" * 55)

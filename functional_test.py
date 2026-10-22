"""
functional_test.py
------------------
Automated functional tests for the Expense Tracker application.
Uses only Python's standard library (urllib / http.client).
Tests run against the live Flask server at http://127.0.0.1:5000.

Test account used: testuser_auto / test@auto.dev / AutoTest@123
No real user data is touched.
"""

import io
import sys
import os

# Ensure UTF-8 output on Windows consoles
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import json
import re

BASE = "http://127.0.0.1:5000"

# Test account credentials — dedicated test user
TEST_EMAIL    = "test@auto.dev"
TEST_PASSWORD = "AutoTest@123"
TEST_USERNAME = "testuser_auto"

# Second test account — for cross-user isolation test
TEST2_EMAIL    = "test2@auto.dev"
TEST2_PASSWORD = "AutoTest@456"
TEST2_USERNAME = "testuser_auto2"

results = []

def make_opener():
    """Create a urllib opener that handles cookies (session)."""
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def post(opener, path, data):
    """Send a POST with form-encoded data. Returns (status_code, response_body, final_url)."""
    url     = BASE + path
    payload = urllib.parse.urlencode(data).encode("utf-8")
    req     = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        resp = opener.open(req)
        return resp.status, resp.read().decode("utf-8", errors="replace"), resp.url
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace"), url

def get(opener, path):
    """Send a GET. Returns (status_code, body, final_url)."""
    url = BASE + path
    req = urllib.request.Request(url)
    try:
        resp = opener.open(req)
        return resp.status, resp.read().decode("utf-8", errors="replace"), resp.url
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace"), url

def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}]  {name}")
    if detail and not condition:
        print(f"         Detail: {detail}")
    results.append((name, status, detail if not condition else ""))
    return condition

# ============================================================================
print("\n" + "=" * 60)
print("  Expense Tracker -- Functional Test Suite")
print("=" * 60)

# ============================================================================
print("\n[1] Flask server reachability")
try:
    r = urllib.request.urlopen(BASE + "/login", timeout=5)
    check("Server responds on http://127.0.0.1:5000", r.status == 200)
except Exception as e:
    check("Server responds on http://127.0.0.1:5000", False, str(e))
    print("\n  Server unreachable -- aborting tests.")
    sys.exit(1)

# ============================================================================
print("\n[2] Redirect unauthenticated user from / and /dashboard to /login")
op0 = make_opener()
s, body, url = get(op0, "/")
check("GET / redirects (ends up at login)", "/login" in url, f"final URL: {url}")
s, body, url = get(op0, "/dashboard")
check("GET /dashboard redirects to login when not logged in", "/login" in url, f"final URL: {url}")
s, body, url = get(op0, "/transactions/")
check("GET /transactions/ redirects to login when not logged in", "/login" in url, f"final URL: {url}")

# ============================================================================
print("\n[3] User Registration")
op1 = make_opener()

# Register first test user
s, body, url = post(op1, "/register", {
    "username": TEST_USERNAME,
    "email":    TEST_EMAIL,
    "password": TEST_PASSWORD,
    "confirm_password": TEST_PASSWORD,
})
# After registration, either redirected to /login or already exists (if rerun)
registered_or_exists = ("/login" in url) or ("already exists" in body)
check("Register new user -> redirected to /login (or already registered)",
      registered_or_exists,
      f"final URL={url}, status={s}")

# Register with duplicate email
s, body, url = post(op1, "/register", {
    "username": "dup_user",
    "email":    TEST_EMAIL,
    "password": TEST_PASSWORD,
    "confirm_password": TEST_PASSWORD,
})
check("Duplicate email rejected -> stays on /register",
      "/register" in url,
      f"final URL={url}")

# Register with short password
s, body, url = post(op1, "/register", {
    "username": "badpass_user",
    "email":    "badpass@test.dev",
    "password": "123",
    "confirm_password": "123",
})
check("Short password rejected -> stays on /register",
      "/register" in url,
      f"final URL={url}")

# Register second user for cross-user isolation test
op2 = make_opener()
s, body, url = post(op2, "/register", {
    "username": TEST2_USERNAME,
    "email":    TEST2_EMAIL,
    "password": TEST2_PASSWORD,
    "confirm_password": TEST2_PASSWORD,
})
registered_or_exists2 = ("/login" in url) or ("already exists" in body)
check("Register second test user (isolation test)",
      registered_or_exists2,
      f"final URL={url}")

# ============================================================================
print("\n[4] Login / Logout")
op1 = make_opener()  # Fresh session for user 1

# Wrong password
s, body, url = post(op1, "/login", {"email": TEST_EMAIL, "password": "WrongPass"})
check("Wrong password rejected -> stays on /login",
      "/login" in url and "Invalid" in body,
      f"final URL={url}")

# Correct login
s, body, url = post(op1, "/login", {"email": TEST_EMAIL, "password": TEST_PASSWORD})
check("Correct login -> redirected to /dashboard",
      "/dashboard" in url,
      f"final URL={url}, status={s}")

# Check dashboard loads
s, body, url = get(op1, "/dashboard")
check("Dashboard page loads (HTTP 200)",
      s == 200,
      f"status={s}, URL={url}")

check("Dashboard contains username",
      TEST_USERNAME in body,
      "Username not found in dashboard HTML")

# Logout
s, body, url = get(op1, "/logout")
check("Logout redirects to /login",
      "/login" in url,
      f"final URL={url}")

# After logout, dashboard should redirect to login
s, body, url = get(op1, "/dashboard")
check("After logout, /dashboard redirects to /login",
      "/login" in url,
      f"final URL={url}")

# ============================================================================
print("\n[5] Transactions -- Add / Edit / Delete")
op1 = make_opener()
post(op1, "/login", {"email": TEST_EMAIL, "password": TEST_PASSWORD})

# Add income with unique timestamp in description
import time
unique_tag = str(int(time.time()))
income_desc = f"Test salary income {unique_tag}"
expense_desc = f"Test lunch expense {unique_tag}"

# Add income
s, body, url = post(op1, "/transactions/add", {
    "type":        "income",
    "amount":      "50000",
    "category":    "Salary",
    "description": income_desc,
    "date":        "2026-10-31",
})
check("Add income transaction -> redirects to list",
      "/transactions" in url,
      f"final URL={url}, status={s}")

# Add expense
s, body, url = post(op1, "/transactions/add", {
    "type":        "expense",
    "amount":      "1500",
    "category":    "Food",
    "description": expense_desc,
    "date":        "2026-10-31",
})
check("Add expense transaction -> redirects to list",
      "/transactions" in url,
      f"final URL={url}, status={s}")

# Add second expense
post(op1, "/transactions/add", {
    "type":        "expense",
    "amount":      "2000",
    "category":    "Bills",
    "description": "Test electricity bill",
    "date":        "2026-10-31",
})

# View list
s, body, url = get(op1, "/transactions/")
check("Transaction list loads (HTTP 200)", s == 200, f"status={s}")
check("Income transaction visible in list", income_desc in body, "")
check("Expense transaction visible in list", expense_desc in body, "")
check("Category badges visible", "Salary" in body and "Food" in body, "")

# Reject invalid amount
s, body, url = post(op1, "/transactions/add", {
    "type": "expense", "amount": "-50",
    "category": "Food", "description": "neg", "date": "2026-10-10",
})
check("Negative amount rejected -> stays on form",
      "/add" in url or "form" in body.lower() or "Amount must" in body,
      f"final URL={url}")

# Find transaction id of the income to edit it
s, body, url = get(op1, "/transactions/")
edit_links = re.findall(r'/transactions/edit/([a-f0-9]{24})', body)
if edit_links:
    txn_id = edit_links[0]
    edited_desc = f"Test salary income EDITED {unique_tag}"
    # Edit transaction
    s, body, url = post(op1, f"/transactions/edit/{txn_id}", {
        "type":        "income",
        "amount":      "52000",
        "category":    "Salary",
        "description": edited_desc,
        "date":        "2026-10-31",
    })
    check("Edit transaction -> redirects to list",
          "/transactions" in url, f"final URL={url}")

    # Verify edit
    s, body, url = get(op1, "/transactions/")
    check("Edited description visible in list",
          edited_desc in body, "")
    check("Edited amount (52000) visible in list",
          "52000" in body or "52,000" in body, "")

    # Delete transaction
    s, body, url = post(op1, f"/transactions/delete/{txn_id}", {})
    check("Delete transaction -> redirects to list",
          "/transactions" in url, f"final URL={url}")

    # Confirm deleted
    s, body, url = get(op1, "/transactions/")
    check("Deleted transaction no longer in list",
          edited_desc not in body, "")
else:
    check("Edit transaction (no edit links found in page)", False, "No transaction IDs found in HTML")
    check("Delete transaction", False, "Skipped -- no ID found")
    check("Deleted transaction no longer in list", False, "Skipped")
    check("Edited description visible", False, "Skipped")
    check("Edited amount visible", False, "Skipped")

# ============================================================================
print("\n[6] Dashboard totals (income, expenses, balance)")
op1_fresh = make_opener()
post(op1_fresh, "/login", {"email": TEST_EMAIL, "password": TEST_PASSWORD})

# Add known amounts for calculation test
post(op1_fresh, "/transactions/add", {
    "type": "income", "amount": "10000",
    "category": "Salary", "description": "Calc test income",
    "date": "2026-10-15",
})
post(op1_fresh, "/transactions/add", {
    "type": "expense", "amount": "3000",
    "category": "Bills", "description": "Calc test expense",
    "date": "2026-10-15",
})

# Check API summary endpoint directly
s, body, url = get(op1_fresh, "/api/summary?year=2026&month=10")
check("API /api/summary returns HTTP 200", s == 200, f"status={s}")
if s == 200:
    data = json.loads(body)
    income   = data.get("income", 0)
    expenses = data.get("expenses", 0)
    balance  = data.get("balance", 0)
    check("Income field present in summary JSON", "income"   in data, "")
    check("Expenses field present in summary JSON", "expenses" in data, "")
    check("Balance = income - expenses (math correct)",
          abs(balance - (income - expenses)) < 0.01,
          f"income={income}, expenses={expenses}, balance={balance}")
    check("Income > 0 after adding test income",
          income > 0, f"income was {income}")

# Chart endpoints
s, body, url = get(op1_fresh, "/api/monthly-chart?year=2026")
check("API /api/monthly-chart returns HTTP 200", s == 200, f"status={s}")
if s == 200:
    chart_data = json.loads(body)
    check("Monthly chart returns 12 months", len(chart_data) == 12, f"got {len(chart_data)}")

s, body, url = get(op1_fresh, "/api/category-chart?year=2026&month=10")
check("API /api/category-chart returns HTTP 200", s == 200, f"status={s}")

# ============================================================================
print("\n[7] Budget -- Create and Retrieve")
s, body, url = post(op1_fresh, "/budget/set", {
    "month":        "2026-10",
    "category":     "Food",
    "limit_amount": "5000",
})
check("Set budget -> redirects to /budget/",
      "/budget" in url, f"final URL={url}")

s, body, url = get(op1_fresh, "/budget/?month=2026-10")
check("Budget page loads (HTTP 200)", s == 200, f"status={s}")
check("Budget category 'Food' visible", "Food" in body, "")
check("Budget limit 5000 visible", "5000" in body or "5,000" in body, "")

# Budget API
s, body, url = get(op1_fresh, "/budget/api/budget-status?month=2026-10")
check("API /budget/api/budget-status returns HTTP 200", s == 200, f"status={s}")
if s == 200:
    bdata = json.loads(body)
    check("Budget status returns list", isinstance(bdata, list), "")
    if bdata:
        b = bdata[0]
        check("Budget has 'category' field",      "category"     in b, "")
        check("Budget has 'limit_amount' field",  "limit_amount" in b, "")
        check("Budget has 'spent' field",         "spent"        in b, "")
        check("Budget has 'percent' field",       "percent"      in b, "")

# ============================================================================
print("\n[8] Cross-user isolation")
op2 = make_opener()
post(op2, "/login", {"email": TEST2_EMAIL, "password": TEST2_PASSWORD})

# User 2 adds their own transaction
post(op2, "/transactions/add", {
    "type": "income", "amount": "9999",
    "category": "Other", "description": "User2 private data",
    "date": "2026-10-01",
})

# User 1 should NOT see User 2's transaction
s, body1, url = get(op1_fresh, "/transactions/")
check("User 1 cannot see User 2's transactions",
      "User2 private data" not in body1,
      "SECURITY: cross-user data leak detected!")

# User 2 should NOT see User 1's transactions
s, body2, url = get(op2, "/transactions/")
check("User 2 cannot see User 1's transactions",
      "Test lunch expense" not in body2 and "Test electricity" not in body2,
      "SECURITY: cross-user data leak detected!")

# ============================================================================
print("\n[9] Search and filter")
s, body, url = get(op1_fresh, "/transactions/?search=lunch")
check("Search by keyword 'lunch' returns HTTP 200", s == 200, f"status={s}")
check("Search results contain matching transaction",
      "lunch" in body.lower(), "")

s, body, url = get(op1_fresh, "/transactions/?type=expense")
check("Filter by type=expense returns HTTP 200", s == 200, f"status={s}")

s, body, url = get(op1_fresh, "/transactions/?category=Food")
check("Filter by category=Food returns HTTP 200", s == 200, f"status={s}")

s, body, url = get(op1_fresh, "/transactions/?date_from=2026-10-01&date_to=2026-10-31")
check("Filter by date range returns HTTP 200", s == 200, f"status={s}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 60)
print("  TEST RESULTS SUMMARY")
print("=" * 60)
passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
total  = len(results)

print(f"\n  Total: {total}  |  Passed: {passed}  |  Failed: {failed}\n")
for name, status, detail in results:
    flag = "[PASS]" if status == "PASS" else "[FAIL]"
    print(f"  {flag} {name}")
    if detail:
        print(f"         └─ {detail}")

print()
if failed == 0:
    print("  ALL TESTS PASSED")
else:
    print(f"  {failed} TEST(S) FAILED")
print("=" * 60 + "\n")

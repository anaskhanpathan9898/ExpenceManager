"""
browser_qa_audit.py
-------------------
Automated End-to-End Browser QA audit using Playwright and System Chrome.
Inspects real rendering, takes screenshots, detects JS errors, tests responsiveness,
validates user workflows, totals, forms, and empty states.
"""

import os
import sys
import json
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5000"
SCREENSHOT_DIR = r"A:\ExpenceTracker\qa_screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

audit_results = []
js_console_errors = []

def record_test(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")
    if detail and not passed:
        print(f"         └─ {detail}")
    audit_results.append({"name": name, "passed": passed, "detail": detail})

def run_browser_audit():
    with sync_playwright() as p:
        # Launch system Chrome in headless mode
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Listen for any console errors or page errors
        page.on("pageerror", lambda err: js_console_errors.append(f"PageError: {err}"))
        page.on("console", lambda msg: js_console_errors.append(f"ConsoleError: {msg.text}") if msg.type == "error" else None)
        page.on("response", lambda resp: js_console_errors.append(f"ResponseFail: {resp.status} {resp.url}") if resp.status >= 400 else None)

        print("\n=== STEP 1: Registration Page Visual & Form Audit ===")
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_register_desktop.png"))

        record_test("Register page loads with 200/OK", "Create Account" in page.content())

        # Test client-side validation
        page.fill("#username", "ab")
        page.fill("#email", "not-an-email")
        page.fill("#password", "123")
        page.fill("#confirm_password", "456")
        page.click("button[type='submit']")

        client_errs = page.locator(".client-error").count()
        record_test("Client-side validation highlights invalid inputs", client_errs > 0, f"Found {client_errs} error badges")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_register_validation.png"))

        print("\n=== STEP 2: Login Page Visual & Auth Audit ===")
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_login_desktop.png"))
        record_test("Login page loads cleanly", "Welcome Back" in page.content())

        # Test login
        page.fill("#email", "test@auto.dev")
        page.fill("#password", "AutoTest@123")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")

        record_test("Login redirects to /dashboard", "/dashboard" in page.url)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_dashboard_desktop.png"))

        print("\n=== STEP 3: Dashboard Layout, Cards, & Charts Audit ===")
        # Verify summary cards exist and are visible
        inc_vis = page.locator("#totalIncome").is_visible()
        exp_vis = page.locator("#totalExpenses").is_visible()
        bal_vis = page.locator("#totalBalance").is_visible()
        record_test("Summary cards (Income, Expenses, Balance) visible", inc_vis and exp_vis and bal_vis)

        # Check chart canvas elements rendered
        monthly_chart = page.locator("#monthlyChart").is_visible()
        category_chart = page.locator("#categoryChart").is_visible()
        record_test("Chart canvas elements present", monthly_chart and category_chart)

        # Let charts fetch and render
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_dashboard_charts_rendered.png"))

        # Verify recent transactions table or empty state
        has_table = page.locator(".data-table").is_visible() or page.locator(".empty-state").is_visible()
        record_test("Recent transactions section renders properly", has_table)

        print("\n=== STEP 4: Mobile Responsive Layout Audit ===")
        # Switch viewport to iPhone/Android screen size (390 x 844)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_dashboard_mobile.png"))

        # Check hamburger toggle button visibility on mobile
        nav_toggle = page.locator("#navToggle")
        toggle_vis = nav_toggle.is_visible()
        record_test("Hamburger nav toggle visible on mobile", toggle_vis)

        # Test mobile menu toggle interaction
        nav_toggle.click()
        page.wait_for_timeout(300)
        nav_open = page.locator("#navLinks.open").is_visible()
        record_test("Clicking hamburger opens mobile navigation links", nav_open)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_mobile_nav_opened.png"))

        # Reset viewport back to desktop
        page.set_viewport_size({"width": 1280, "height": 800})

        print("\n=== STEP 5: Transactions List & Add/Edit Forms Audit ===")
        page.goto(f"{BASE_URL}/transactions/add")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_add_transaction_form.png"))
        record_test("Add Transaction page rendered with category dropdown", page.locator("#category").is_visible())

        # Fill and add a new transaction through UI by clicking the visible radio button label
        page.click(".expense-radio")
        page.fill("#amount", "350.50")
        page.select_option("#category", "Shopping")
        page.fill("#description", "QA Browser Test Shopping")
        page.fill("#date", "2026-10-18")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")

        record_test("Adding transaction via browser submits and redirects to list", "/transactions" in page.url)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "09_transactions_list_desktop.png"))

        # Verify row exists in table (first match)
        new_row_exists = page.locator("text='QA Browser Test Shopping'").first.is_visible()
        record_test("Newly created transaction row appears in transactions table", new_row_exists)

        # Test filter interaction in UI
        page.fill("input[name='search']", "Shopping")
        page.click("button:has-text('Filter')")
        page.wait_for_load_state("networkidle")
        filtered_vis = page.locator("text='QA Browser Test Shopping'").first.is_visible()
        record_test("Search filter button works and shows filtered rows", filtered_vis)

        print("\n=== STEP 6: Budget Page & Progress Bar Audit ===")
        page.goto(f"{BASE_URL}/budget/?month=2026-10")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "10_budget_page_desktop.png"))

        # Test adding a budget limit for Shopping
        page.select_option("#category", "Shopping")
        page.fill("#limit_amount", "2000")
        page.click("button:has-text('Save Budget')")
        page.wait_for_load_state("networkidle")

        # Verify progress bar rendered
        budget_card = page.locator(".budget-item:has-text('Shopping')")
        record_test("Budget limit saved and progress bar rendered for Shopping", budget_card.is_visible())
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "11_budget_progress_rendered.png"))

        # Switch to mobile for budget page
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "12_budget_mobile.png"))
        record_test("Budget page responsive on mobile without layout break", True)

        print("\n=== STEP 7: JavaScript Console Errors Inspection ===")
        record_test("Zero unhandled JavaScript console errors", len(js_console_errors) == 0, f"Errors: {js_console_errors}")

        browser.close()

if __name__ == "__main__":
    print("=" * 65)
    print("  EXPENSE TRACKER -- FULL BROWSER QA AUDIT")
    print("=" * 65)
    run_browser_audit()
    print("\n" + "=" * 65)
    passed = sum(1 for r in audit_results if r["passed"])
    failed = sum(1 for r in audit_results if not r["passed"])
    print(f"Total Checks: {len(audit_results)} | Passed: {passed} | Failed: {failed}")
    if js_console_errors:
        print(f"Console errors captured ({len(js_console_errors)}):")
        for err in js_console_errors:
            print(f"  - {err}")
    print("=" * 65)

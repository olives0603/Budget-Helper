"""Handles accounts, the dashboard, and income.

Run python app.py, then open http://localhost/practice/login.php.
"""

# App settings
import re
import secrets
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    redirect,
    request,
    session,
)
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

# The --test flag runs the checks at the bottom instead of starting the server.
RUN_TESTS = __name__ == "__main__" and "--test" in sys.argv

# Resolve these paths from this file, even if Python is started from another folder.
PROJECT_FOLDER = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_FOLDER / "users.db"
SECRET_KEY_PATH = PROJECT_FOLDER / ".session_secret"
LOGIN_PAGE = "http://localhost/practice/login.php"
INVALID_LOGIN_MESSAGE = "Incorrect username or password."
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

app = Flask(__name__)

# Let the PHP pages talk to Python, even though they use a different port.
# Cookies let Python remember which browser is logged in.
CORS(
    app,
    origins=[re.compile(r"^http://(?:localhost|127\.0\.0\.1)(?::[0-9]+)?$")],
    supports_credentials=True,
)

# Keep the same key when the server restarts so users stay logged in.
# Store this file and users.db next to app.py, not in htdocs.
if RUN_TESTS:
    # Test mode must not create or change the real signing key.
    app.secret_key = secrets.token_hex(32)
else:
    if not SECRET_KEY_PATH.exists():
        SECRET_KEY_PATH.write_text(secrets.token_hex(32), encoding="utf-8")
    app.secret_key = SECRET_KEY_PATH.read_text(encoding="utf-8").strip()
app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024,
    SESSION_COOKIE_NAME="budgetwise_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)


# Database setup
def connect_db():
    """Open the database so we can read fields by name, like user["email"]."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    # Make SQLite enforce links between financial records and their accounts.
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create any missing tables without changing existing accounts or entries."""
    connection = connect_db()
    try:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL
                )
            """)
            # Keep income in its own table, tied to the account that entered it.
            # Whole cents avoid the rounding errors that can happen with floats.
            connection.execute("""
                CREATE TABLE IF NOT EXISTS incomes (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                    source TEXT NOT NULL,
                    income_date TEXT NOT NULL,
                    is_recurring INTEGER NOT NULL DEFAULT 0
                        CHECK(is_recurring IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS incomes_user_date
                ON incomes (user_id, income_date DESC, id DESC)
            """)
    finally:
        connection.close()


def initialize_finance_tables():
    """Add the new sections while keeping existing users and income records."""
    db = connect_db()
    try:
        with db:
            # Older databases may be missing category. Add it without replacing their rows.
            columns = {row["name"] for row in db.execute("PRAGMA table_info(incomes)")}
            if "category" not in columns:
                db.execute(
                    "ALTER TABLE incomes ADD COLUMN category TEXT NOT NULL DEFAULT 'Other'"
                )
            db.execute("""CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
                amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                description TEXT NOT NULL, category TEXT NOT NULL, expense_date TEXT NOT NULL
            )""")
            db.execute(
                "CREATE INDEX IF NOT EXISTS expenses_user_date ON expenses(user_id, expense_date)"
            )
            db.execute("""CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
                name TEXT NOT NULL, target_cents INTEGER NOT NULL CHECK(target_cents > 0),
                saved_cents INTEGER NOT NULL CHECK(saved_cents >= 0)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS spending_limits (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
                category TEXT NOT NULL, period TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                UNIQUE(user_id, category, period)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
                name TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                due_date TEXT NOT NULL, paid INTEGER NOT NULL DEFAULT 0 CHECK(paid IN (0, 1))
            )""")
    finally:
        db.close()


def add_demo_account():
    """Add the test account if it is not already there."""
    connection = connect_db()
    try:
        with connection:
            # Save a hash instead of the actual password.
            # Leave the account alone if this email is already in the database.
            connection.execute(
                "INSERT OR IGNORE INTO users (email, password_hash) VALUES (?, ?)",
                ("admin@admin.com", generate_password_hash("Test123!")),
            )
    finally:
        connection.close()


# Form helpers
def submitted_email():
    """Clean up the email. Older forms called this field 'username'."""
    value = request.form.get("email", request.form.get("username", ""))
    return value.strip().lower()


def valid_email(email):
    """Check that the email looks valid. This does not check the actual inbox."""
    return len(email) <= 254 and EMAIL_PATTERN.fullmatch(email) is not None


def valid_password_length(password):
    return 8 <= len(password) <= 128


def error_response(message, status=400):
    """Send an error message back to the form."""
    return jsonify(success=False, message=message), status


# Dates arrive as YYYY-MM-DD strings from the browser's date fields.
def calendar_date(value):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Choose a valid date.")
    result = date.fromisoformat(value)
    if not 1900 <= result.year <= 9998:
        raise ValueError("Choose a date between 1900 and 9998.")
    return result


def signed_in_user_exists(connection):
    # Use the account from the session, not an ID someone typed into the form.
    user_id = session.get("user_id")
    if user_id is None:
        return False
    return (
        connection.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        is not None
    )


# Sessions and request checks
@app.before_request
def protect_form_submissions():
    """Check the token before accepting a form submission."""
    if request.method != "POST":
        return None

    # Look for the token in the request header or the logout form.
    provided = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")

    if not expected or not secrets.compare_digest(provided, expected):
        return error_response(
            "Your session expired. Refresh the page and try again.",
            403,
        )
    return None


@app.after_request
def private_responses(response):
    """Tell the browser not to save these responses or guess their file type."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/api/csrf")
def csrf_token():
    # Give this browser a token to send back with the form.
    # This helps stop other sites from submitting forms using its session.
    session.setdefault("csrf_token", secrets.token_hex(32))
    return jsonify(csrf_token=session["csrf_token"])


@app.errorhandler(413)
def too_large(error):
    return error_response("The submitted information is too long.", 413)


# Login and account settings
@app.post("/api/register")
def create_account():
    email = submitted_email()
    password = request.form.get("password", "")
    confirmation = request.form.get("confirm_password", "")

    # Check everything here too, since browser checks can be skipped.
    # Keep spaces in passwords, but reject passwords made up of only spaces.
    if not email or not password or not confirmation:
        return error_response("Please complete all fields.")
    if not valid_email(email):
        return error_response("Please enter a valid email address.")
    if not valid_password_length(password):
        return error_response("Your password must contain 8–128 characters.")
    if not password.strip():
        return error_response("Your password cannot be only spaces.")
    if password != confirmation:
        return error_response("Passwords do not match.")

    password_hash = generate_password_hash(password)
    connection = connect_db()
    try:
        with connection:
            # The ? placeholders keep the entered values separate from the SQL.
            connection.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, password_hash),
            )
    except sqlite3.IntegrityError:
        # This email already belongs to an account.
        return error_response("An account with this email already exists.", 409)
    finally:
        connection.close()

    # The page will send the user back to login after the account is saved.
    return jsonify(success=True), 201


@app.post("/login")  # Keep the old login address working too.
@app.post("/api/login")
def login():
    email = submitted_email()
    password = request.form.get("password", "")

    # Clear the previous login, but keep the token for this form.
    session.pop("user_id", None)
    session.pop("email", None)

    if (
        not valid_email(email)
        or not valid_password_length(password)
        or not password.strip()
    ):
        return error_response(INVALID_LOGIN_MESSAGE, 401)

    connection = connect_db()
    try:
        user = connection.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        connection.close()

    # Use the same error whether the email or password is wrong.
    if user is None or not check_password_hash(user["password_hash"], password):
        return error_response(INVALID_LOGIN_MESSAGE, 401)

    # The details are correct, so remember who is logged in.
    session.clear()
    session["user_id"] = user["id"]
    session["email"] = user["email"]
    session["csrf_token"] = secrets.token_hex(32)
    return jsonify(success=True)


# Pages call this before showing private data, rather than trusting the page URL.
@app.get("/api/account")
def account_details():
    db = connect_db()
    try:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        user = db.execute(
            "SELECT email FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
        return jsonify(success=True, email=user["email"])
    finally:
        db.close()


@app.post("/logout")
@app.post("/api/logout")
def logout():
    session.clear()
    return redirect(LOGIN_PAGE)


# Income: validate entries before saving anything.
def income_amount(value, allow_zero=False):
    value = value.strip()
    if not re.fullmatch(r"[0-9]{1,9}(?:\.[0-9]{1,2})?", value):
        raise ValueError("Enter an amount using numbers and up to two decimal places.")
    # Split the text to keep amounts exact; converting through float can round them.
    whole, _, fraction = value.partition(".")
    cents = int(whole) * 100 + int(fraction.ljust(2, "0"))
    if cents < (0 if allow_zero else 1) or cents > 99999999999:
        raise ValueError("Enter an amount between 0.01 and 999,999,999.99.")
    return cents


# Both Add and Edit use these checks, so neither route can skip validation.
def income_fields():
    source = request.form.get("source", "").strip()
    if not source or len(source) > 120:
        raise ValueError("Enter a source between 1 and 120 characters.")
    amount = income_amount(request.form.get("amount", ""))
    received = calendar_date(request.form.get("income_date", "")).isoformat()
    recurring = request.form.get("is_recurring", "0")
    if recurring not in ("0", "1"):
        raise ValueError("Choose whether the income is recurring.")
    return amount, source, received, int(recurring)


# Income list: filters only change what is shown, not what is saved.
@app.get("/api/income")
def income_list():
    db = connect_db()
    try:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        # Build the WHERE clause from fixed SQL fragments and separate input values.
        clauses, values = ["user_id = ?"], [session["user_id"]]
        try:
            period = request.args.get("period", "all")
            if period not in ("all", "week", "month", "year", "custom"):
                raise ValueError("Choose a valid date range.")
            start, end = None, None
            # These are rolling windows including today, not calendar dashboard periods.
            if period in ("week", "month", "year"):
                end = date.today()
                start = end - timedelta(
                    days={"week": 7, "month": 30, "year": 365}[period] - 1
                )
            elif period == "custom":
                start = calendar_date(request.args.get("start", ""))
                end = calendar_date(request.args.get("end", ""))
            if start is not None:
                if start > end:
                    raise ValueError(
                        "The start date must be on or before the end date."
                    )
                clauses.extend(["income_date >= ?", "income_date <= ?"])
                values.extend([start.isoformat(), end.isoformat()])
            # Blank amount filters mean no limit; equal amounts give an exact match.
            minimum, maximum = None, None
            for key, operator in (("min_amount", ">="), ("max_amount", "<=")):
                raw = request.args.get(key, "").strip()
                if raw:
                    amount = income_amount(raw, allow_zero=True)
                    if key == "min_amount":
                        minimum = amount
                    else:
                        maximum = amount
                    clauses.append(f"amount_cents {operator} ?")
                    values.append(amount)
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError("The minimum amount cannot exceed the maximum amount.")
            source = request.args.get("source", "").strip()
            if len(source) > 120:
                raise ValueError("Keep the source filter under 121 characters.")
            if source:
                # Search literal text so symbols such as % are not SQL wildcards.
                clauses.append("instr(lower(source), lower(?)) > 0")
                values.append(source)
            recurring = request.args.get("recurring", "all")
            if recurring not in ("all", "0", "1"):
                raise ValueError("Choose a valid recurring filter.")
            if recurring != "all":
                clauses.append("is_recurring = ?")
                values.append(int(recurring))
        except ValueError as error:
            return error_response(str(error))
        rows = db.execute(
            "SELECT id, amount_cents, source, income_date, is_recurring FROM incomes WHERE "
            + " AND ".join(clauses)
            + " ORDER BY income_date DESC, id DESC",
            values,
        ).fetchall()
        return jsonify(success=True, entries=[dict(row) for row in rows])
    finally:
        db.close()


# Income changes: every lookup includes the logged-in account.
@app.post("/api/income")
@app.post("/api/income/<int:entry_id>/edit")
def save_income(entry_id=None):
    db = connect_db()
    try:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        try:
            fields = income_fields()
        except ValueError as error:
            return error_response(str(error))
        with db:
            # The add route has no ID. The edit route supplies the entry to update.
            if entry_id is None:
                entry_id = db.execute(
                    "INSERT INTO incomes (amount_cents, source, income_date, is_recurring, user_id) VALUES (?,?,?,?,?)",
                    (*fields, session["user_id"]),
                ).lastrowid
                status = 201
            else:
                changed = db.execute(
                    "UPDATE incomes SET amount_cents=?, source=?, income_date=?, is_recurring=? WHERE id=? AND user_id=?",
                    (*fields, entry_id, session["user_id"]),
                ).rowcount
                if not changed:
                    return error_response(
                        "This income entry could not be found. Refresh the list.", 404
                    )
                status = 200
        return jsonify(success=True, id=entry_id), status
    finally:
        db.close()


# Delete only a row belonging to this session; guessing another ID is not enough.
@app.post("/api/income/<int:entry_id>/delete")
def delete_income(entry_id):
    db = connect_db()
    try:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        with db:
            changed = db.execute(
                "DELETE FROM incomes WHERE id=? AND user_id=?",
                (entry_id, session["user_id"]),
            ).rowcount
            if not changed:
                return error_response(
                    "This income entry could not be found. Refresh the list.", 404
                )
        return jsonify(success=True)
    finally:
        db.close()


# Dashboard reports
def report_window(period, anchor):
    """Find the calendar period. The end date is the first day of the next one."""
    if period == "weekly":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=7)
    if period == "monthly":
        start = anchor.replace(day=1)
        end = (
            date(start.year + 1, 1, 1)
            if start.month == 12
            else date(start.year, start.month + 1, 1)
        )
        return start, end
    if period == "yearly":
        return date(anchor.year, 1, 1), date(anchor.year + 1, 1, 1)
    raise ValueError("Choose weekly, monthly, or yearly.")


@app.get("/api/dashboard/summary")
def dashboard_summary():
    db = connect_db()
    try:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        try:
            period = request.args.get("period", "monthly")
            anchor = calendar_date(request.args.get("date", date.today().isoformat()))
            start, end = report_window(period, anchor)
        except ValueError as error:
            return error_response(str(error))
        uid = session["user_id"]
        # Include the first day and exclude the next period's first day.
        bounds = (uid, start.isoformat(), end.isoformat())
        income = db.execute(
            "SELECT COUNT(*) AS count, COALESCE(SUM(amount_cents), 0) AS total FROM incomes WHERE user_id = ? AND income_date >= ? AND income_date < ?",
            bounds,
        ).fetchone()
        expenses = db.execute(
            "SELECT COUNT(*) AS count, COALESCE(SUM(amount_cents), 0) AS total FROM expenses WHERE user_id = ? AND expense_date >= ? AND expense_date < ?",
            bounds,
        ).fetchone()
        categories = [
            dict(row)
            for row in db.execute(
                "SELECT category, SUM(amount_cents) AS amount_cents FROM expenses WHERE user_id = ? AND expense_date >= ? AND expense_date < ? GROUP BY category ORDER BY amount_cents DESC",
                bounds,
            )
        ]
        # Match each spending limit to the category total for this report.
        spent = {row["category"]: row["amount_cents"] for row in categories}
        goals = [
            dict(row)
            for row in db.execute(
                "SELECT id, name, target_cents, saved_cents FROM savings_goals WHERE user_id = ? ORDER BY id",
                (uid,),
            )
        ]
        limits = [
            dict(row)
            for row in db.execute(
                "SELECT category, amount_cents, period FROM spending_limits WHERE user_id = ? AND period = ? ORDER BY category",
                (uid, period),
            )
        ]
        for limit in limits:
            limit["spent_cents"] = spent.get(limit["category"], 0)
        # Savings show the current amount. Bills get their own 30-day window.
        bill_end = anchor + timedelta(days=30)
        bills = [
            dict(row)
            for row in db.execute(
                "SELECT id, name, amount_cents, due_date FROM bills WHERE user_id = ? AND paid = 0 AND due_date >= ? AND due_date <= ? ORDER BY due_date, id",
                (uid, anchor.isoformat(), bill_end.isoformat()),
            )
        ]
        overdue = db.execute(
            "SELECT COUNT(*) FROM bills WHERE user_id = ? AND paid = 0 AND due_date < ?",
            (uid, anchor.isoformat()),
        ).fetchone()[0]
        return jsonify(
            success=True,
            period=period,
            start=start.isoformat(),
            end=(end - timedelta(days=1)).isoformat(),
            income_cents=income["total"],
            expense_cents=expenses["total"],
            remaining_cents=income["total"] - expenses["total"],
            income_count=income["count"],
            expense_count=expenses["count"],
            categories=categories,
            goals=goals,
            limits=limits,
            bills=bills,
            overdue_count=overdue,
            bills_through=bill_end.isoformat(),
        )
    finally:
        db.close()


@app.get("/dashboard")
@app.get("/api/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(LOGIN_PAGE)
    return redirect("http://localhost/practice/dashboard.php")


# Dashboard and income tests: run these with: python app.py --test


def run_dashboard_tests():
    """Run the checks against a temporary copy of this app and its database."""
    import importlib.util
    import shutil
    import tempfile
    import unittest
    from pathlib import Path

    class DashboardTests(unittest.TestCase):
        # Each test starts with its own copy and database, leaving real accounts alone.
        def setUp(self):
            self.temp = tempfile.TemporaryDirectory()
            self.addCleanup(self.temp.cleanup)
            path = Path(self.temp.name) / "app.py"
            shutil.copy(Path(__file__).resolve(), path)
            spec = importlib.util.spec_from_file_location("dashboard_test", path)
            self.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.module)
            self.client = self.module.app.test_client()
            token = self.client.get("/api/csrf").json["csrf_token"]
            result = self.client.post(
                "/api/login",
                data={"email": "admin@admin.com", "password": "Test123!"},
                headers={"X-CSRF-Token": token},
            )
            self.assertEqual(result.status_code, 200)
            with self.client.session_transaction() as session:
                self.user_id = session["user_id"]

        def report(self, period="monthly"):
            response = self.client.get(
                "/api/dashboard/summary?period=" + period + "&date=2026-10-29"
            )
            self.assertEqual(response.status_code, 200)
            return response.json

        def test_known_totals_and_panels(self):
            db = self.module.connect_db()
            try:
                with db:
                    for amount, day in [
                        (100000, "2026-10-29"),
                        (20000, "2026-10-01"),
                        (5000, "2026-11-01"),
                        (30000, "2026-01-01"),
                    ]:
                        db.execute(
                            "INSERT INTO incomes (user_id,amount_cents,source,income_date) VALUES (?,?,?,?)",
                            (self.user_id, amount, "Test income", day),
                        )
                    for amount, day in [
                        (30000, "2026-10-29"),
                        (5000, "2026-10-01"),
                        (2000, "2026-11-01"),
                        (4000, "2026-01-01"),
                    ]:
                        db.execute(
                            "INSERT INTO expenses (user_id,amount_cents,description,category,expense_date) VALUES (?,?,?,?,?)",
                            (self.user_id, amount, "Test expense", "Food", day),
                        )
                    db.execute(
                        "INSERT INTO savings_goals (user_id,name,target_cents,saved_cents) VALUES (?,?,?,?)",
                        (self.user_id, "Emergency fund", 100000, 25000),
                    )
                    db.execute(
                        "INSERT INTO spending_limits (user_id,category,period,amount_cents) VALUES (?,?,?,?)",
                        (self.user_id, "Food", "monthly", 30000),
                    )
                    for name, due, paid in [
                        ("Rent", "2026-11-01", 0),
                        ("Old", "2026-10-01", 0),
                        ("Paid", "2026-11-02", 1),
                        ("Later", "2026-12-01", 0),
                    ]:
                        db.execute(
                            "INSERT INTO bills (user_id,name,amount_cents,due_date,paid) VALUES (?,?,?,?,?)",
                            (self.user_id, name, 5000, due, paid),
                        )
            finally:
                db.close()
            for period, income, expense, remaining in [
                ("weekly", 105000, 32000, 73000),
                ("monthly", 120000, 35000, 85000),
                ("yearly", 155000, 41000, 114000),
            ]:
                with self.subTest(period=period):
                    r = self.report(period)
                    self.assertEqual(
                        (r["income_cents"], r["expense_cents"], r["remaining_cents"]),
                        (income, expense, remaining),
                    )
            r = self.report()
            self.assertEqual(
                r["goals"][0]["saved_cents"] / r["goals"][0]["target_cents"], 0.25
            )
            self.assertEqual(
                r["limits"][0]["spent_cents"] - r["limits"][0]["amount_cents"], 5000
            )
            self.assertEqual([b["name"] for b in r["bills"]], ["Rent"])
            self.assertEqual(r["overdue_count"], 1)

        def test_empty_data_access_and_scope(self):
            r = self.report()
            self.assertEqual(
                (r["income_count"], r["expense_count"], r["remaining_cents"]), (0, 0, 0)
            )
            for key in ("goals", "limits", "bills", "categories"):
                self.assertEqual(r[key], [])
            anonymous = self.module.app.test_client()
            self.assertEqual(anonymous.get("/api/dashboard/summary").status_code, 401)
            self.assertEqual(
                self.client.get("/api/dashboard").location,
                "http://localhost/practice/dashboard.php",
            )
            self.assertEqual(
                self.client.get("/api/dashboard/summary?period=invalid").status_code,
                400,
            )
            # Another account's records must not leak into this dashboard.
            db = self.module.connect_db()
            try:
                with db:
                    uid = db.execute(
                        "INSERT INTO users (email,password_hash) VALUES ('other@example.com','unused')"
                    ).lastrowid
                    db.execute(
                        "INSERT INTO incomes (user_id,amount_cents,source,income_date) VALUES (?,999999,'Private','2026-10-29')",
                        (uid,),
                    )
            finally:
                db.close()
            self.assertEqual(self.report()["income_cents"], 0)
            paths = {rule.rule for rule in self.module.app.url_map.iter_rules()}
            self.assertNotIn("/api/records/<section>", paths)
            self.assertIn("/api/income", paths)

        # Income checks: adding, editing, deleting, filtering, and account privacy.
        def income_post(self, path="/api/income", **changes):
            data = {
                "amount": "1250.55",
                "source": "Paycheck",
                "income_date": "2026-10-29",
                "is_recurring": "1",
            }
            data.update(changes)
            token = self.client.get("/api/csrf").json["csrf_token"]
            return self.client.post(path, data=data, headers={"X-CSRF-Token": token})

        def test_income_add_edit_delete_and_dashboard(self):
            added = self.income_post()
            self.assertEqual(added.status_code, 201)
            entry_id = added.json["id"]
            self.assertEqual(self.report()["income_cents"], 125055)
            # A new database connection sees the saved entry too.
            db = self.module.connect_db()
            try:
                self.assertEqual(
                    db.execute(
                        "SELECT amount_cents FROM incomes WHERE id=?", (entry_id,)
                    ).fetchone()[0],
                    125055,
                )
            finally:
                db.close()
            updated = self.income_post(
                f"/api/income/{entry_id}/edit",
                amount="0.01",
                source="Gift",
                is_recurring="0",
            )
            self.assertEqual(updated.status_code, 200)
            row = self.client.get("/api/income").json["entries"][0]
            self.assertEqual(
                (row["source"], row["amount_cents"], row["is_recurring"]),
                ("Gift", 1, 0),
            )
            self.assertEqual(self.report()["income_cents"], 1)
            self.assertEqual(
                self.income_post(f"/api/income/{entry_id}/delete").status_code, 200
            )
            self.assertEqual(self.client.get("/api/income").json["entries"], [])
            self.assertEqual(self.report()["income_cents"], 0)
            self.assertEqual(
                self.income_post(f"/api/income/{entry_id}/delete").status_code, 404
            )

        def test_income_validation(self):
            for amount in (
                "",
                "abc",
                "0",
                "-10",
                "1.234",
                "NaN",
                "Infinity",
                "1e3",
                "1000000000",
                "1,000",
            ):
                with self.subTest(amount=amount):
                    self.assertEqual(self.income_post(amount=amount).status_code, 400)
            for fields in (
                {"source": " "},
                {"source": "a" * 121},
                {"income_date": ""},
                {"income_date": "2026-02-30"},
                {"is_recurring": "yes"},
            ):
                self.assertEqual(self.income_post(**fields).status_code, 400)
            self.assertEqual(self.client.get("/api/income").json["entries"], [])
            entry_id = self.income_post().json["id"]
            self.assertEqual(
                self.income_post(
                    f"/api/income/{entry_id}/edit", amount="bad"
                ).status_code,
                400,
            )
            self.assertEqual(self.report()["income_cents"], 125055)

        def test_income_filters(self):
            today = date.today()
            for days, amount, source, recurring in [
                (0, "100.10", "Paycheck", "1"),
                (6, "200", "Gift", "0"),
                (7, "300", "Bonus", "0"),
                (29, "400", "Paycheck", "1"),
                (30, "500", "Old gift", "0"),
                (364, "600", "Year bonus", "0"),
                (365, "700", "Previous", "1"),
                (-1, "800", "Future", "0"),
            ]:
                self.assertEqual(
                    self.income_post(
                        amount=amount,
                        source=source,
                        is_recurring=recurring,
                        income_date=(today - timedelta(days=days)).isoformat(),
                    ).status_code,
                    201,
                )

            def entries(**filters):
                r = self.client.get("/api/income", query_string=filters)
                self.assertEqual(r.status_code, 200)
                return r.json["entries"]

            for period, count in (("week", 2), ("month", 4), ("year", 6), ("all", 8)):
                self.assertEqual(len(entries(period=period)), count)
            self.assertEqual(
                len(
                    entries(
                        period="custom", start=today.isoformat(), end=today.isoformat()
                    )
                ),
                1,
            )
            self.assertEqual(
                len(
                    entries(
                        source="PAYCHECK",
                        recurring="1",
                        min_amount="100.10",
                        max_amount="100.10",
                    )
                ),
                1,
            )
            self.assertEqual(len(entries(recurring="0")), 5)
            self.assertEqual(entries(source="Missing"), [])
            self.assertEqual(entries(source="%' OR 1=1 --"), [])
            self.assertEqual(len(entries()), 8)
            for filters in (
                {"period": "wrong"},
                {"period": "custom", "start": "2026-10-29", "end": "2026-10-01"},
                {"period": "custom"},
                {"min_amount": "50", "max_amount": "40"},
                {"min_amount": "NaN"},
                {"recurring": "yes"},
            ):
                self.assertEqual(
                    self.client.get("/api/income", query_string=filters).status_code,
                    400,
                )

        def test_income_auth_and_csrf(self):
            anonymous = self.module.app.test_client()
            self.assertEqual(anonymous.get("/api/income").status_code, 401)
            token = anonymous.get("/api/csrf").json["csrf_token"]
            self.assertEqual(
                anonymous.post(
                    "/api/income", headers={"X-CSRF-Token": token}
                ).status_code,
                401,
            )
            self.assertEqual(self.client.post("/api/income", data={}).status_code, 403)
            entry_id = self.income_post().json["id"]
            db = self.module.connect_db()
            try:
                with db:
                    other_id = db.execute(
                        "INSERT INTO users (email,password_hash) VALUES ('private@example.com','unused')"
                    ).lastrowid
            finally:
                db.close()
            other = self.module.app.test_client()
            with other.session_transaction() as account:
                account["user_id"] = other_id
                account["csrf_token"] = "test-token"
            self.assertEqual(other.get("/api/income").json["entries"], [])
            for action in ("edit", "delete"):
                r = other.post(
                    f"/api/income/{entry_id}/{action}",
                    data={
                        "source": "Steal",
                        "amount": "1",
                        "income_date": "2026-10-29",
                    },
                    headers={"X-CSRF-Token": "test-token"},
                )
                self.assertEqual(r.status_code, 404)
            self.assertEqual(self.report()["income_cents"], 125055)

    # A nonzero exit code makes a failed check visible to the terminal or a test runner.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DashboardTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


# Choose test mode before opening the real database.
if RUN_TESTS:
    run_dashboard_tests()
else:
    initialize_database()
    initialize_finance_tables()
    add_demo_account()

    if __name__ == "__main__":
        print("Open http://localhost/practice/login.php with Apache running.")
        app.run(host="127.0.0.1", port=5000)

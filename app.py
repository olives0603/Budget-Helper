"""Handles accounts, dashboard reports, income, expenses, bills, and spending limits.

Run python app.py, then open http://localhost/practice/login.php.
"""

# Page guide: search for a PHP filename below to find its Python routes.
# account_creation.php and login.php handle sign-up and sign-in.
# income.php and expenses.php save entries, dashboard.php reads their totals.
# statistics.php groups saved expenses into category totals for its three views.
# subscriptions.php manages the expense rows marked as Subscriptions.
# account.php manages profile changes and the local Premium demo.
# goals.php stores savings targets and the amounts users have set aside.

# App settings
import re
import csv
import io
from contextlib import closing
import secrets
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

from flask import (
    Flask,
    Response,
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
    # Create missing tables when the app starts. Existing rows stay in place.
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
            # Account settings: Add membership fields without touching saved finances.
            # The expiry date is the first day without access after cancellation.
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
            for name, definition in {
                "premium_until": "TEXT",
                "premium_cancelled": "INTEGER NOT NULL DEFAULT 0",
            }.items():
                if name not in columns:
                    connection.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")
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
    # Older copies of users.db may not have the newer columns yet. Add only what is missing.
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
            # Older goals did not have a target date. Leave their date blank on upgrade.
            if "target_date" not in {
                row["name"] for row in db.execute("PRAGMA table_info(savings_goals)")
            }:
                db.execute("ALTER TABLE savings_goals ADD COLUMN target_date TEXT")
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
            # Old expenses start as one-time payments. Existing bills can stay unlinked.
            if "is_recurring" not in {
                r["name"] for r in db.execute("PRAGMA table_info(expenses)")
            }:
                db.execute(
                    "ALTER TABLE expenses ADD COLUMN is_recurring INTEGER NOT NULL DEFAULT 0 CHECK(is_recurring IN (0,1))"
                )
            if "expense_id" not in {
                r["name"] for r in db.execute("PRAGMA table_info(bills)")
            }:
                db.execute(
                    "ALTER TABLE bills ADD COLUMN expense_id INTEGER REFERENCES expenses(id) ON DELETE CASCADE"
                )
            db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS bills_one_per_expense ON bills(expense_id)"
            )
    finally:
        db.close()


def add_demo_account():
    """Add the test account if it is not already there."""
    connection = connect_db()
    try:
        with connection:
            # Seed only a fresh database. Renaming the demo account must not recreate it.
            if connection.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                return
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
    # Use the same length rule during registration and login.
    return 8 <= len(password) <= 128


def error_response(message, status=400):
    """Send an error message back to the form."""
    return jsonify(success=False, message=message), status


# Dates arrive as YYYY-MM-DD strings from the browser's date fields.
def calendar_date(value):
    # Check the format first, then let Python reject impossible dates such as February 30.
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Choose a valid date.")
    result = date.fromisoformat(value)
    if not 1900 <= result.year <= 9998:
        raise ValueError("Choose a date between 1900 and 9998.")
    return result


def signed_in_user_exists(connection):
    # Use the account from the session, not an ID someone typed into the form.
    # A session can outlive a deleted account, so check that the user still exists.
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
    # These replies contain account information, so ask the browser not to cache them.
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


# --------------------------------------------------------------------
# account_creation.php: Create an account
# The registration form posts here. On success, the page sends the user to login.php.
# --------------------------------------------------------------------
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


# --------------------------------------------------------------------
# login.php: Sign in
# A failed login returns a message for the form. A successful one starts the session.
# --------------------------------------------------------------------
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


# --------------------------------------------------------------------
# Shared account routes: Check the session and log out
# Dashboard, Income, and Expenses check the session before loading private records.
# --------------------------------------------------------------------
@app.get("/api/account")
def account_details():
    # Return the email and membership for the page header. Never expose the password hash.
    db = connect_db()
    try:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        user = db.execute(
            "SELECT * FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
        return jsonify(success=True, email=user["email"], membership=membership_status(db, user))
    finally:
        db.close()


# --------------------------------------------------------------------
# account.php: Update email and password
# Check the whole form first. A bad password or email must not save half an update.
# --------------------------------------------------------------------
@app.post("/api/account/update")
def update_account():
    email = submitted_email()
    current = request.form.get("current_password", "")
    password = request.form.get("new_password", "")
    confirmation = request.form.get("confirm_password", "")
    with closing(connect_db()) as db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        if not check_password_hash(user["password_hash"], current):
            return error_response("Your current password is incorrect.")
        if not valid_email(email):
            return error_response("Please enter a valid email address.")
        if password or confirmation:
            if not valid_password_length(password) or not password.strip():
                return error_response("Your new password must contain 8 to 128 characters and cannot be only spaces.")
            if password != confirmation:
                return error_response("The new passwords do not match.")
            # A new password should actually change the account's password.
            # Compare against the saved hash, never against plain text in the database.
            if check_password_hash(user["password_hash"], password):
                return error_response("Your new password must be different from your current password.")
        # Compare email addresses without case, including accounts from older databases.
        if db.execute("SELECT id FROM users WHERE lower(email)=? AND id<>?", (email, user["id"])).fetchone():
            return error_response("This email is already in use.", 409)
        password_hash = generate_password_hash(password) if password else user["password_hash"]
        try:
            with db:
                db.execute("UPDATE users SET email=?, password_hash=? WHERE id=?",
                           (email, password_hash, user["id"]))
        except sqlite3.IntegrityError:
            return error_response("This email is already in use.", 409)
    session["email"] = email
    return jsonify(success=True, email=email, message="Your account details have been saved.")


# --------------------------------------------------------------------
# account.php: Demo Premium membership
# There is no payment service here. Periods renew locally without charging anyone.
# Cancel stops the next renewal; access lasts through the current 30-day period.
# --------------------------------------------------------------------
def membership_status(db, user, today=None):
    today = today or date.today()
    until = date.fromisoformat(user["premium_until"]) if user["premium_until"] else None
    cancelled = bool(user["premium_cancelled"])
    if until and until <= today and not cancelled:
        # Catch up after time away without creating duplicate memberships.
        until += timedelta(days=((today - until).days // 30 + 1) * 30)
        with db:
            db.execute("UPDATE users SET premium_until=? WHERE id=?", (until.isoformat(), user["id"]))
    active = bool(until and until > today)
    return dict(is_premium=active, expires_on=until.isoformat() if until else None,
                cancel_at_period_end=cancelled, demo=True,
                status="Premium" if active else "Free")


@app.post("/api/account/premium/<action>")
def manage_premium(action):
    if action not in ("subscribe", "cancel", "enable", "disable"):
        return error_response("Choose a valid membership action.", 404)
    with closing(connect_db()) as db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        # Serialize repeated clicks so they cannot add extra months.
        with db:
            db.execute("BEGIN IMMEDIATE")
            user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
            until = date.fromisoformat(user["premium_until"]) if user["premium_until"] else None
            today = date.today()
            if until and until <= today and not user["premium_cancelled"]:
                until += timedelta(days=((today - until).days // 30 + 1) * 30)
            # Demo controls switch perks immediately. Cancel still waits until expiry.
            if action == "disable":
                until = today
                cancelled = 1
            elif action in ("subscribe", "enable"):
                if not until or until <= today:
                    until = today + timedelta(days=30)
                cancelled = 0
            else:
                if not until or until <= today:
                    return error_response("There is no active Premium membership to cancel.")
                cancelled = 1
            db.execute("UPDATE users SET premium_until=?, premium_cancelled=? WHERE id=?",
                       (until.isoformat(), cancelled, user["id"]))
        user = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return jsonify(success=True, membership=membership_status(db, user))


# Premium export | Check access in Python, even if someone opens the URL directly.
@app.get("/api/account/export")
def export_finances():
    with closing(connect_db()) as db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        if not membership_status(db, user)["is_premium"]:
            return error_response("CSV export is available with demo Premium.", 403)
        rows = db.execute("""
            SELECT 'Income' AS kind, income_date AS day, source AS description,
                   category, amount_cents, is_recurring FROM incomes WHERE user_id=?
            UNION ALL
            SELECT 'Expense', expense_date, description, category, amount_cents,
                   is_recurring FROM expenses WHERE user_id=? ORDER BY day
        """, (user["id"], user["id"])).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Type", "Date", "Description", "Category", "Amount", "Recurring"])
    for row in rows:
        # Spreadsheet programs can treat typed text as a formula. Keep it as text.
        def cell(value):
            value = str(value)
            return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value
        cents = row["amount_cents"]
        writer.writerow([row["kind"], row["day"], cell(row["description"]),
                         cell(row["category"]), f"{cents // 100}.{cents % 100:02d}",
                         "Yes" if row["is_recurring"] else "No"])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="budgetbuddy-finances.csv"'})


@app.post("/logout")
@app.post("/api/logout")
def logout():
    # Forget this browser's login, then send it back to the PHP login page.
    session.clear()
    return redirect(LOGIN_PAGE)


# Form helpers for income and expenses. The same money check also applies to bills and limits.
def money_cents(value, allow_zero=False):
    # Accept ordinary prices like 12 or 12.99. Zero is allowed only for amount filters.
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
    # Read all the fields together so Add and Edit follow the same rules.
    source = request.form.get("source", "").strip()
    if not source or len(source) > 120:
        raise ValueError("Enter a source between 1 and 120 characters.")
    amount = money_cents(request.form.get("amount", ""))
    received = calendar_date(request.form.get("income_date", "")).isoformat()
    recurring = request.form.get("is_recurring", "0")
    if recurring not in ("0", "1"):
        raise ValueError("Choose whether the income is recurring.")
    return amount, source, received, int(recurring)


# Income and expenses use the same date, amount, and recurring filters.
# Column names come from the two routes below, never from the form.
def record_filters(date_column, prefix=""):
    # Each filter adds a SQL condition and its value. The values fill the ? placeholders.
    clauses, values = [f"{prefix}user_id = ?"], [session["user_id"]]
    period = request.args.get("period", "all")
    if period not in ("all", "week", "month", "year", "custom"):
        raise ValueError("Choose a valid date range.")
    start, end = None, None
    # These are rolling windows including today, not calendar dashboard periods.
    if period in ("week", "month", "year"):
        end = date.today()
        start = end - timedelta(days={"week": 7, "month": 30, "year": 365}[period] - 1)
    elif period == "custom":
        start = calendar_date(request.args.get("start", ""))
        end = calendar_date(request.args.get("end", ""))
    if start is not None:
        if start > end:
            raise ValueError("The start date must be on or before the end date.")
        clauses.extend([f"{date_column} >= ?", f"{date_column} <= ?"])
        values.extend([start.isoformat(), end.isoformat()])
    # Blank amount filters mean no limit; equal amounts give an exact match.
    minimum, maximum = None, None
    for key, operator in (("min_amount", ">="), ("max_amount", "<=")):
        raw = request.args.get(key, "").strip()
        if raw:
            amount = money_cents(raw, allow_zero=True)
            if key == "min_amount":
                minimum = amount
            else:
                maximum = amount
            clauses.append(f"{prefix}amount_cents {operator} ?")
            values.append(amount)
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("The minimum amount cannot exceed the maximum amount.")
    recurring = request.args.get("recurring", "all")
    if recurring not in ("all", "0", "1"):
        raise ValueError("Choose a valid recurring filter.")
    if recurring != "all":
        clauses.append(f"{prefix}is_recurring = ?")
        values.append(int(recurring))
    return clauses, values


# --------------------------------------------------------------------
# income.php: List, add, edit, and delete income
# Filters choose which rows to show. Clearing a filter does not change any saved entry.
# --------------------------------------------------------------------
@app.get("/api/income")
def income_list():
    # Read this account's matching entries; a search does not change anything in the database.
    db = connect_db()
    try:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        # Build the WHERE clause from fixed SQL fragments and separate input values.
        try:
            clauses, values = record_filters("income_date")
            source = request.args.get("source", "").strip()
            if len(source) > 120:
                raise ValueError("Keep the source filter under 121 characters.")
            if source:
                # Search literal text so symbols such as % are not SQL wildcards.
                clauses.append("instr(lower(source), lower(?)) > 0")
                values.append(source)
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
    # One route adds an entry and the other supplies an ID to edit. Both use this function.
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
    # Deleting a row changes later dashboard totals because reports read the saved entries.
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


# --------------------------------------------------------------------
# expenses.php: Expenses, bill reminders, and spending limits
# The expense form records spending. An optional reminder tracks when a bill is due.
# --------------------------------------------------------------------
CATEGORIES = (
    "Food",
    "Gas",
    "Entertainment",
    "Subscriptions",
    "Bills",
    "Necessities",
    "Other",
)
PERIODS = ("weekly", "monthly", "yearly")


def form_text(key, label, maximum):
    # Trim accidental spaces, then reject blank or overly long names and descriptions.
    value = request.form.get(key, "").strip()
    if not value or len(value) > maximum:
        raise ValueError(f"Enter {label} (up to {maximum} characters).")
    return value


def category_value(value):
    # Accept only the categories offered by the form, even if someone submits a different value.
    if value not in CATEGORIES:
        raise ValueError("Choose a spending category.")
    return value


def checkbox(key):
    # The page sends checkboxes as 0 or 1. Reject other values instead of guessing.
    value = request.form.get(key, "0")
    if value not in ("0", "1"):
        raise ValueError("Choose yes or no.")
    return int(value)


# Expense list: include the reminder if one exists, and still show payments without one.
@app.get("/api/expenses")
def expense_list():
    # The left join keeps expenses in the list even when they do not have a bill reminder.
    with closing(connect_db()) as db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        try:
            clauses, values = record_filters("e.expense_date", "e.")
            category = request.args.get("category", "")
            if category:
                clauses.append("e.category = ?")
                values.append(category_value(category))
        except ValueError as error:
            return error_response(str(error))
        rows = db.execute(
            """SELECT e.id, e.description, e.expense_date, e.category, e.amount_cents, e.is_recurring,
                      b.name AS bill_name, b.due_date AS bill_due, b.amount_cents AS bill_cents
               FROM expenses e LEFT JOIN bills b ON b.expense_id=e.id AND b.user_id=e.user_id
               WHERE """
            + " AND ".join(clauses)
            + " ORDER BY e.expense_date DESC, e.id DESC",
            values,
        )
        return jsonify(
            success=True, entries=[dict(row) for row in rows], categories=CATEGORIES
        )


@app.post("/api/expenses")
@app.post("/api/expenses/<int:entry_id>/edit")
def save_expense(entry_id=None):
    # Keep the expense and optional reminder in one save so an error cannot leave half an update.
    with closing(connect_db()) as db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        uid = session["user_id"]
        try:
            fields = (
                money_cents(request.form.get("amount", "")),
                form_text("description", "a description", 200),
                calendar_date(request.form.get("expense_date", "")).isoformat(),
                category_value(request.form.get("category", "")),
                checkbox("is_recurring"),
            )
            # Check the bill fields before writing anything. A bad due date should leave
            # both the expense and its reminder exactly as they were.
            bill = None
            if checkbox("has_bill"):
                if not fields[-1]:
                    raise ValueError(
                        "Only recurring expenses can have a bill reminder."
                    )
                bill = (
                    form_text("bill_name", "a bill name", 120),
                    money_cents(request.form.get("bill_amount", "")),
                    calendar_date(request.form.get("bill_due", "")).isoformat(),
                )
        except ValueError as error:
            return error_response(str(error))
        # Save the expense and reminder in one transaction so they stay in sync.
        creating = entry_id is None
        with db:
            if creating:
                entry_id = db.execute(
                    "INSERT INTO expenses (amount_cents,description,expense_date,category,is_recurring,user_id) VALUES (?,?,?,?,?,?)",
                    (*fields, uid),
                ).lastrowid
            elif not db.execute(
                "UPDATE expenses SET amount_cents=?,description=?,expense_date=?,category=?,is_recurring=? WHERE user_id=? AND id=?",
                (*fields, uid, entry_id),
            ).rowcount:
                return error_response("Expense not found.", 404)
            # A reminder is not a second payment. Only the expense counts toward spending.
            if bill:
                db.execute(
                    """INSERT INTO bills (name,amount_cents,due_date,user_id,expense_id) VALUES (?,?,?,?,?)
                    ON CONFLICT(expense_id) DO UPDATE SET name=excluded.name, amount_cents=excluded.amount_cents,
                    due_date=excluded.due_date, paid=0""",
                    (*bill, uid, entry_id),
                )
            else:
                db.execute(
                    "DELETE FROM bills WHERE user_id=? AND expense_id=?",
                    (uid, entry_id),
                )
        return jsonify(success=True, id=entry_id), 201 if creating else 200


@app.post("/api/expenses/<int:entry_id>/delete")
def delete_expense(entry_id):
    with closing(connect_db()) as db, db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        # The foreign key also removes this expense's reminder.
        if not db.execute(
            "DELETE FROM expenses WHERE user_id=? AND id=?",
            (session["user_id"], entry_id),
        ).rowcount:
            return error_response("Expense not found.", 404)
        return jsonify(success=True)


# Spending limits (expenses.php): each category can have a separate weekly,
# monthly, and yearly limit. Editing a limit leaves past expenses alone.
@app.get("/api/limits")
def list_limits():
    # Show the limits this account has set, including ones for other report periods.
    with closing(connect_db()) as db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        rows = db.execute(
            "SELECT id,category,period,amount_cents FROM spending_limits WHERE user_id=? ORDER BY category,period",
            (session["user_id"],),
        )
        return jsonify(success=True, limits=[dict(row) for row in rows])


@app.post("/api/limits")
@app.post("/api/limits/<int:limit_id>/edit")
def save_limit(limit_id=None):
    # A category can have a weekly, monthly, and yearly limit, but not two for the same period.
    with closing(connect_db()) as db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        try:
            category = category_value(request.form.get("category", ""))
            period = request.form.get("period", "")
            if period not in PERIODS:
                raise ValueError("Choose a weekly, monthly, or yearly limit.")
            amount = money_cents(request.form.get("amount", ""))
            fields = (category, period, amount, session["user_id"])
            with db:
                if limit_id is None:
                    db.execute(
                        "INSERT INTO spending_limits (category,period,amount_cents,user_id) VALUES (?,?,?,?)",
                        fields,
                    )
                elif not db.execute(
                    "UPDATE spending_limits SET category=?,period=?,amount_cents=? WHERE user_id=? AND id=?",
                    (*fields, limit_id),
                ).rowcount:
                    return error_response("Limit not found.", 404)
        except ValueError as error:
            return error_response(str(error))
        except sqlite3.IntegrityError:
            return error_response(
                "There is already a limit for that category and period. Edit it instead.",
                409,
            )
        return jsonify(success=True), 201 if limit_id is None else 200


@app.post("/api/limits/<int:limit_id>/delete")
def delete_limit(limit_id):
    # Remove the limit only. The expenses it was compared with are still part of the account.
    with closing(connect_db()) as db, db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        if not db.execute(
            "DELETE FROM spending_limits WHERE user_id=? AND id=?",
            (session["user_id"], limit_id),
        ).rowcount:
            return error_response("Limit not found.", 404)
        return jsonify(success=True)


# --------------------------------------------------------------------
# dashboard.php: Financial overview
# The selected date and period determine which income and expenses count toward the totals.
# --------------------------------------------------------------------
def report_window(period, anchor):
    """Find the calendar period. The end date is the first day of the next one."""
    # Return the first day of this period and the first day of the next one.
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
    # Build the overview from saved records rather than keeping a separate copy of the totals.
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
        # Completed goals stay on Goals, but only unfinished ones appear on the dashboard.
        goals = [
            dict(row)
            for row in db.execute(
                "SELECT id, name, target_cents, saved_cents, target_date FROM savings_goals WHERE user_id = ? AND saved_cents < target_cents ORDER BY id",
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
            used, cap = limit["spent_cents"], limit["amount_cents"]
            limit["status"] = (
                "over"
                if used > cap
                else (
                    "reached"
                    if used == cap
                    else "near" if used * 100 >= cap * 80 else "within"
                )
            )
        # Savings show the current amount. Bills get their own 30-day window.
        bill_end = anchor + timedelta(days=30)
        bills = [
            dict(row)
            for row in db.execute(
                "SELECT id, name, amount_cents, due_date FROM bills WHERE user_id = ? AND paid = 0 AND due_date >= ? AND due_date <= ? ORDER BY due_date, id",
                (uid, anchor.isoformat(), bill_end.isoformat()),
            )
        ]
        overdue = [
            dict(row)
            for row in db.execute(
                "SELECT id,name,amount_cents,due_date FROM bills WHERE user_id=? AND paid=0 AND due_date<? ORDER BY due_date,id",
                (uid, anchor.isoformat()),
            )
        ]
        # Compare due dates with the date selected on the dashboard. The next
        # seven days count as due soon; earlier dates are already past due.
        for bill in bills + overdue:
            days = (date.fromisoformat(bill["due_date"]) - anchor).days
            bill["status"] = (
                "Past due"
                if days < 0
                else (
                    "Due today"
                    if days == 0
                    else "Due soon" if days <= 7 else "Upcoming"
                )
            )
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
            overdue_count=len(overdue),
            overdue_bills=overdue,
            bills_through=bill_end.isoformat(),
        )
    finally:
        db.close()


@app.get("/dashboard")
@app.get("/api/dashboard")
def dashboard():
    # Keep older dashboard links working by sending them to the current PHP page.
    if "user_id" not in session:
        return redirect(LOGIN_PAGE)
    return redirect("http://localhost/practice/dashboard.php")


# --------------------------------------------------------------------
# statistics.php: Spending totals and charts
# All three views use these same totals. Switching charts never changes saved data.
# --------------------------------------------------------------------
@app.get("/api/statistics")
def spending_statistics():
    # The PHP page draws the charts. Python only gathers the category amounts and counts.
    with closing(connect_db()) as db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        # Start with this account only, then add the chosen date range.
        clauses, values = ["user_id = ?"], [session["user_id"]]
        start = end = None
        try:
            period = request.args.get("period", "monthly")
            # Custom dates include both days. Calendar reports use the same
            # Monday-to-Sunday weeks and month/year boundaries as the dashboard.
            if period == "custom":
                start = calendar_date(request.args.get("start", ""))
                end = calendar_date(request.args.get("end", ""))
                if start > end:
                    raise ValueError(
                        "The start date must be on or before the end date."
                    )
                clauses.extend(["expense_date >= ?", "expense_date <= ?"])
                values.extend([start.isoformat(), end.isoformat()])
            elif period != "all":
                anchor = calendar_date(
                    request.args.get("date", date.today().isoformat())
                )
                start, next_start = report_window(period, anchor)
                end = next_start - timedelta(days=1)
                clauses.extend(["expense_date >= ?", "expense_date < ?"])
                values.extend([start.isoformat(), next_start.isoformat()])
        except ValueError as error:
            return error_response(str(error))
        # Read one grouped result so totals and chart slices always agree.
        rows = [
            dict(row)
            for row in db.execute(
                "SELECT category, COUNT(*) AS count, SUM(amount_cents) AS amount_cents FROM expenses WHERE "
                + " AND ".join(clauses)
                + " GROUP BY category ORDER BY amount_cents DESC, category",
                values,
            )
        ]
        # Add the category totals to get the overall spending and entry count.
        total = sum(row["amount_cents"] for row in rows)
        count = sum(row["count"] for row in rows)
        # The percentage is used for labels. Chart sizes use the exact cents.
        for row in rows:
            row["percentage"] = (
                round(row["amount_cents"] / total * 100, 2) if total else 0
            )
        # An empty result tells statistics.php to ask for more spending data.
        return jsonify(
            success=True,
            categories=rows,
            total_cents=total,
            count=count,
            start=start.isoformat() if start else None,
            end=end.isoformat() if end else None,
            period=period,
        )


# --------------------------------------------------------------------
# subscriptions.php: Manage expenses in the Subscriptions category
# Use the existing expense rows so changes appear on both pages.
# The billing date is the recorded expense date, not a generated future charge.
# --------------------------------------------------------------------
@app.get("/api/subscriptions")
def list_subscriptions():
    # Use category Subscriptions to find the rows, including ones entered on the Expenses page.
    with closing(connect_db()) as db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        rows = db.execute(
            """SELECT e.id, e.description AS name, e.amount_cents,
                      e.expense_date AS billing_date,
                      EXISTS(SELECT 1 FROM bills b WHERE b.expense_id=e.id AND b.user_id=e.user_id) AS has_bill
               FROM expenses e WHERE e.user_id=? AND e.category='Subscriptions'
               ORDER BY e.expense_date, e.id""",
            (session["user_id"],),
        )
        return jsonify(success=True, subscriptions=[dict(row) for row in rows])


@app.post("/api/subscriptions")
@app.post("/api/subscriptions/<int:subscription_id>/edit")
def save_subscription(subscription_id=None):
    # This updates an expense, not a second subscription table, so the two pages stay in sync.
    with closing(connect_db()) as db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        # Check all three fields before inserting or changing a saved entry.
        try:
            name = form_text("name", "a subscription name", 200)
            amount = money_cents(request.form.get("amount", ""))
            billed = calendar_date(request.form.get("billing_date", "")).isoformat()
        except ValueError as error:
            return error_response(str(error))
        uid = session["user_id"]
        creating = subscription_id is None
        with db:
            if creating:
                # Entries added here also appear as recurring subscription expenses.
                subscription_id = db.execute(
                    """INSERT INTO expenses (description,amount_cents,expense_date,category,is_recurring,user_id)
                       VALUES (?,?,?,'Subscriptions',1,?)""",
                    (name, amount, billed, uid),
                ).lastrowid
            else:
                # Check both owner and category. A different expense must not be editable here.
                changed = db.execute(
                    """UPDATE expenses SET description=?,amount_cents=?,expense_date=?
                       WHERE id=? AND user_id=? AND category='Subscriptions'""",
                    (name, amount, billed, subscription_id, uid),
                ).rowcount
                if not changed:
                    return error_response(
                        "Subscription not found. Refresh the list.", 404
                    )
                # Bill reminders have their own amounts and due dates; manage them in Expenses.
        return jsonify(success=True, id=subscription_id), 201 if creating else 200


@app.post("/api/subscriptions/<int:subscription_id>/delete")
def delete_subscription(subscription_id):
    # The page asks for confirmation before calling this route because the expense is removed too.
    with closing(connect_db()) as db, db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        # This removes the shared expense too. Its linked bill reminder is removed by the database.
        removed = db.execute(
            "DELETE FROM expenses WHERE id=? AND user_id=? AND category='Subscriptions'",
            (subscription_id, session["user_id"]),
        ).rowcount
        if not removed:
            return error_response("Subscription not found. Refresh the list.", 404)
        return jsonify(success=True)


# --------------------------------------------------------------------
# goals.php: Create goals and keep their progress up to date
# Amount saved is entered by the user. It does not move money or add an expense.
# Reaching the target completes the goal; completed goals remain editable here.
# --------------------------------------------------------------------
@app.get("/api/goals")
def list_goals():
    with closing(connect_db()) as db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        # Keep completed goals so users can still review, edit, or delete them.
        rows = db.execute(
            """SELECT id,name,target_cents,saved_cents,target_date FROM savings_goals
               WHERE user_id=? ORDER BY (saved_cents >= target_cents), id DESC""",
            (session["user_id"],),
        )
        return jsonify(success=True, goals=[dict(row) for row in rows])


@app.post("/api/goals")
@app.post("/api/goals/<int:goal_id>/edit")
def save_goal(goal_id=None):
    with closing(connect_db()) as db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        # Check every field first. An invalid target must not partially update a goal.
        try:
            name = form_text("name", "a goal name", 120)
            target = money_cents(request.form.get("target_amount", ""))
            saved = money_cents(request.form.get("saved_amount", "0"), allow_zero=True)
            raw_date = request.form.get("target_date", "").strip()
            target_date = calendar_date(raw_date).isoformat() if raw_date else None
        except ValueError as error:
            return error_response(str(error))
        fields = (name, target, saved, target_date, session["user_id"])
        creating = goal_id is None
        with db:
            if creating:
                goal_id = db.execute(
                    "INSERT INTO savings_goals(name,target_cents,saved_cents,target_date,user_id) VALUES(?,?,?,?,?)",
                    fields,
                ).lastrowid
            else:
                # Include the account ID so guessing another goal's ID cannot change it.
                changed = db.execute(
                    "UPDATE savings_goals SET name=?,target_cents=?,saved_cents=?,target_date=? WHERE user_id=? AND id=?",
                    (*fields, goal_id),
                ).rowcount
                if not changed:
                    return error_response("Goal not found. Refresh the list.", 404)
        return jsonify(success=True, id=goal_id), 201 if creating else 200


@app.post("/api/goals/<int:goal_id>/delete")
def delete_goal(goal_id):
    with closing(connect_db()) as db, db:
        if not signed_in_user_exists(db):
            return error_response("Please log in.", 401)
        # Removing a goal does not remove any income or expense records.
        changed = db.execute(
            "DELETE FROM savings_goals WHERE user_id=? AND id=?",
            (session["user_id"], goal_id),
        ).rowcount
        if not changed:
            return error_response("Goal not found. Refresh the list.", 404)
        return jsonify(success=True)


# --------------------------------------------------------------------
# Tests: Run with python app.py --test
# These checks cover dashboard totals, income, expenses, reminders, spending limits,
# statistics, and subscriptions. They run against temporary data.
# --------------------------------------------------------------------


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
        # Expense tests use the same form fields as expenses.php.
        def expense(self, path="/api/expenses", **changes):
            fields = dict(
                amount="26.50",
                description="Groceries",
                category="Food",
                expense_date="2026-10-29",
                is_recurring="1",
                has_bill="0",
            )
            fields.update(changes)
            token = self.client.get("/api/csrf").json["csrf_token"]
            return self.client.post(path, data=fields, headers={"X-CSRF-Token": token})

        def test_expense_validation_and_filters(self):
            today = date.today()
            for days, category, amount, recurring in [
                (0, "Food", "26.50", "1"),
                (6, "Food", "50", "0"),
                (7, "Food", "50", "1"),
                (0, "Gas", "50", "1"),
            ]:
                self.assertEqual(
                    self.expense(
                        expense_date=(today - timedelta(days=days)).isoformat(),
                        category=category,
                        amount=amount,
                        is_recurring=recurring,
                    ).status_code,
                    201,
                )

            def results(**filters):
                return self.client.get("/api/expenses", query_string=filters).json[
                    "entries"
                ]

            self.assertEqual(len(results()), 4)
            self.assertEqual(len(results(period="week", category="Food")), 2)
            self.assertEqual(
                len(
                    results(
                        period="week",
                        category="Food",
                        min_amount="26.50",
                        max_amount="26.50",
                        recurring="1",
                    )
                ),
                1,
            )
            self.assertEqual(
                len(
                    results(
                        period="custom", start=today.isoformat(), end=today.isoformat()
                    )
                ),
                2,
            )
            self.assertFalse(results(category="Entertainment"))
            for change in [
                dict(amount=""),
                dict(amount="bad"),
                dict(amount="0"),
                dict(amount="-1"),
                dict(amount="1.011"),
                dict(description="  "),
                dict(category=""),
                dict(expense_date="2026-02-30"),
            ]:
                self.assertEqual(self.expense(**change).status_code, 400)
            self.assertEqual(len(results()), 4)

        def test_bill_dates_edits_and_removal(self):
            settings = dict(
                has_bill="1", bill_name="Rent", bill_amount="70", bill_due="2026-10-30"
            )
            for change in [
                dict(is_recurring="0"),
                dict(bill_name=" "),
                dict(bill_amount="bad"),
                dict(bill_due=""),
            ]:
                self.assertEqual(self.expense(**(settings | change)).status_code, 400)
            self.assertEqual(self.report()["expense_count"], 0)
            eid = self.expense(**settings).json["id"]
            edit = f"/api/expenses/{eid}/edit"
            for due, status in [
                ("2026-10-28", "Past due"),
                ("2026-10-29", "Due today"),
                ("2026-11-05", "Due soon"),
                ("2026-11-06", "Upcoming"),
                ("2026-11-29", None),
            ]:
                settings["bill_due"] = due
                self.assertEqual(self.expense(edit, **settings).status_code, 200)
                r = self.report()
                rows = r["overdue_bills"] + r["bills"]
                self.assertEqual(
                    [row["status"] for row in rows], [status] if status else []
                )
                self.assertEqual(r["expense_cents"], 2650)
            self.assertEqual(self.expense(edit, amount="45").status_code, 200)
            self.assertIsNone(
                self.client.get("/api/expenses").json["entries"][0]["bill_name"]
            )
            self.assertEqual(self.report()["expense_cents"], 4500)
            self.expense(edit, **(settings | dict(bill_due="2026-10-29")))
            self.assertEqual(
                self.expense(f"/api/expenses/{eid}/delete").status_code, 200
            )
            self.assertEqual(self.report()["expense_cents"], 0)
            self.assertFalse(self.report()["bills"])

        def test_limit_levels_and_periods(self):
            self.assertEqual(
                self.expense("/api/limits", period="monthly", amount="100").status_code,
                201,
            )
            lid = self.client.get("/api/limits").json["limits"][0]["id"]
            eid = self.expense().json["id"]
            for amount, status in [
                ("79.99", "within"),
                ("80", "near"),
                ("100", "reached"),
                ("100.01", "over"),
            ]:
                self.expense(f"/api/expenses/{eid}/edit", amount=amount)
                self.assertEqual(self.report()["limits"][0]["status"], status)
            self.assertEqual(
                self.expense("/api/limits", period="monthly", amount="90").status_code,
                409,
            )
            self.assertEqual(
                self.expense(
                    f"/api/limits/{lid}/edit", period="weekly", amount="250"
                ).status_code,
                200,
            )
            self.assertFalse(self.report()["limits"])
            self.assertEqual(self.report("weekly")["limits"][0]["status"], "within")
            self.assertEqual(self.expense(f"/api/limits/{lid}/delete").status_code, 200)
            self.assertFalse(self.report("weekly")["limits"])

        def test_expense_and_limit_privacy(self):
            eid = self.expense(
                has_bill="1", bill_name="Phone", bill_amount="30", bill_due="2026-11-02"
            ).json["id"]
            self.expense("/api/limits", period="monthly")
            lid = self.client.get("/api/limits").json["limits"][0]["id"]
            other = self.module.app.test_client()
            token = other.get("/api/csrf").json["csrf_token"]
            headers = {"X-CSRF-Token": token}
            self.assertEqual(other.get("/api/expenses").status_code, 401)
            self.assertEqual(self.client.post("/api/expenses").status_code, 403)
            with closing(self.module.connect_db()) as db, db:
                uid = db.execute(
                    "INSERT INTO users (email,password_hash) VALUES ('private@site.com','unused')"
                ).lastrowid
            with other.session_transaction() as sess:
                sess["user_id"] = uid
            self.assertFalse(other.get("/api/expenses").json["entries"])
            self.assertFalse(other.get("/api/limits").json["limits"])
            data = dict(
                amount="1",
                description="other",
                category="Food",
                period="monthly",
                expense_date="2026-10-29",
            )
            for kind, item in [("expenses", eid), ("limits", lid)]:
                for action in ["edit", "delete"]:
                    self.assertEqual(
                        other.post(
                            f"/api/{kind}/{item}/{action}", data=data, headers=headers
                        ).status_code,
                        404,
                    )
            self.assertEqual(self.report()["expense_cents"], 2650)
            self.assertEqual(len(self.report()["bills"]), 1)

        # Statistics: check category totals, date ranges, and private account data.
        def test_statistics(self):
            self.assertEqual(
                self.client.get("/api/statistics?period=all").json["count"], 0
            )
            for amount, category, day in [
                ("20", "Food", "2026-10-01"),
                ("40", "Food", "2026-10-29"),
                ("40", "Gas", "2026-10-31"),
                ("999", "Gas", "2026-11-01"),
            ]:
                self.expense(amount=amount, category=category, expense_date=day)
            data = self.client.get(
                "/api/statistics?period=monthly&date=2026-10-29"
            ).json
            self.assertEqual((data["total_cents"], data["count"]), (10000, 3))
            self.assertEqual(
                [(x["category"], x["percentage"]) for x in data["categories"]],
                [("Food", 60.0), ("Gas", 40.0)],
            )
            self.assertEqual(
                self.client.get("/api/statistics?period=weekly&date=2026-10-01").json[
                    "total_cents"
                ],
                2000,
            )
            self.assertEqual(
                self.client.get("/api/statistics?period=yearly&date=2026-10-01").json[
                    "count"
                ],
                4,
            )
            self.assertEqual(
                self.client.get(
                    "/api/statistics?period=custom&start=2026-10-29&end=2026-10-29"
                ).json["total_cents"],
                4000,
            )
            for query in [
                "period=wrong",
                "period=custom&start=2026-11-01&end=2026-10-01",
                "date=bad",
                "period=custom",
            ]:
                self.assertEqual(
                    self.client.get("/api/statistics?" + query).status_code, 400
                )
            anonymous = self.module.app.test_client()
            self.assertEqual(anonymous.get("/api/statistics").status_code, 401)
            with closing(self.module.connect_db()) as db, db:
                uid = db.execute(
                    "INSERT INTO users(email,password_hash) VALUES('stat@example.com','unused')"
                ).lastrowid
            with anonymous.session_transaction() as sess:
                sess["user_id"] = uid
            self.assertEqual(
                anonymous.get("/api/statistics?period=all").json["total_cents"], 0
            )

        # Subscriptions share expense rows, so verify changes from both pages.
        def subscription_post(self, path="/api/subscriptions", **changes):
            fields = dict(
                name="Music service", amount="12.99", billing_date="2026-10-29"
            )
            fields.update(changes)
            token = self.client.get("/api/csrf").json["csrf_token"]
            return self.client.post(path, data=fields, headers={"X-CSRF-Token": token})

        def test_subscriptions_sync_and_dates(self):
            self.assertEqual(
                self.client.get("/api/subscriptions").json["subscriptions"], []
            )
            imported = self.expense(
                category="Subscriptions",
                description="Streaming",
                amount="20",
                expense_date="2026-10-01",
            ).json["id"]
            self.expense(category="Food")
            created = self.subscription_post()
            self.assertEqual(created.status_code, 201)
            sid = created.json["id"]
            rows = self.client.get("/api/subscriptions").json["subscriptions"]
            self.assertEqual(
                [r["billing_date"] for r in rows], ["2026-10-01", "2026-10-29"]
            )
            self.assertEqual(
                self.subscription_post(
                    f"/api/subscriptions/{sid}/edit",
                    amount="15",
                    name="Music Plus",
                    billing_date="2026-11-03",
                ).status_code,
                200,
            )
            expenses = self.client.get("/api/expenses?category=Subscriptions").json[
                "entries"
            ]
            changed = next(row for row in expenses if row["id"] == sid)
            self.assertEqual(
                (
                    changed["description"],
                    changed["amount_cents"],
                    changed["is_recurring"],
                ),
                ("Music Plus", 1500, 1),
            )
            self.expense(
                f"/api/expenses/{imported}/edit",
                category="Subscriptions",
                description="New name",
                amount="25",
                expense_date="2026-10-02",
                has_bill="1",
                bill_name="Next payment",
                bill_amount="25",
                bill_due="2026-11-02",
            )
            self.assertEqual(
                self.client.get("/api/subscriptions").json["subscriptions"][0]["name"],
                "New name",
            )
            self.subscription_post(f"/api/subscriptions/{imported}/edit")
            with closing(self.module.connect_db()) as db:
                self.assertEqual(
                    db.execute(
                        "SELECT due_date FROM bills WHERE expense_id=?", (imported,)
                    ).fetchone()[0],
                    "2026-11-02",
                )
            self.assertEqual(
                self.subscription_post(
                    f"/api/subscriptions/{imported}/delete"
                ).status_code,
                200,
            )
            with closing(self.module.connect_db()) as db:
                self.assertIsNone(
                    db.execute(
                        "SELECT id FROM bills WHERE expense_id=?", (imported,)
                    ).fetchone()
                )
            self.assertEqual(
                self.subscription_post(f"/api/subscriptions/{sid}/delete").status_code,
                200,
            )
            self.assertEqual(
                self.client.get("/api/subscriptions").json["subscriptions"], []
            )
            self.assertEqual(self.report()["expense_cents"], 2650)

        def test_subscription_validation_and_privacy(self):
            for change in [
                dict(name=" "),
                dict(name="x" * 201),
                dict(amount="abc"),
                dict(amount="0"),
                dict(amount="-1"),
                dict(amount="1.234"),
                dict(billing_date=""),
                dict(billing_date="2026-02-30"),
            ]:
                self.assertEqual(self.subscription_post(**change).status_code, 400)
            self.assertEqual(
                self.client.get("/api/subscriptions").json["subscriptions"], []
            )
            sid = self.subscription_post().json["id"]
            self.assertEqual(
                self.subscription_post(
                    f"/api/subscriptions/{sid}/edit", amount="bad"
                ).status_code,
                400,
            )
            self.assertEqual(
                self.client.get("/api/subscriptions").json["subscriptions"][0][
                    "amount_cents"
                ],
                1299,
            )
            food = self.expense(category="Food").json["id"]
            for action in ("edit", "delete"):
                self.assertEqual(
                    self.subscription_post(
                        f"/api/subscriptions/{food}/{action}"
                    ).status_code,
                    404,
                )
            guest = self.module.app.test_client()
            self.assertEqual(guest.get("/api/subscriptions").status_code, 401)
            token = guest.get("/api/csrf").json["csrf_token"]
            self.assertEqual(
                guest.post(
                    "/api/subscriptions", headers={"X-CSRF-Token": token}
                ).status_code,
                401,
            )
            self.assertEqual(self.client.post("/api/subscriptions").status_code, 403)
            with closing(self.module.connect_db()) as db, db:
                uid = db.execute(
                    "INSERT INTO users(email,password_hash) VALUES('sub@example.com','unused')"
                ).lastrowid
            with guest.session_transaction() as sess:
                sess["user_id"] = uid
            self.assertEqual(guest.get("/api/subscriptions").json["subscriptions"], [])
            fields = dict(name="Other", amount="1", billing_date="2026-10-29")
            for action in ("edit", "delete"):
                self.assertEqual(
                    guest.post(
                        f"/api/subscriptions/{sid}/{action}",
                        data=fields,
                        headers={"X-CSRF-Token": token},
                    ).status_code,
                    404,
                )

        # Goals: exercise both a dated goal and one with no deadline.
        def goal_post(self, path="/api/goals", **changes):
            data = dict(
                name="New car", target_amount="1000", saved_amount="250", target_date=""
            )
            data.update(changes)
            token = self.client.get("/api/csrf").json["csrf_token"]
            return self.client.post(path, data=data, headers={"X-CSRF-Token": token})

        def test_goals_progress_and_changes(self):
            self.assertEqual(self.client.get("/api/goals").json["goals"], [])
            added = self.goal_post()
            self.assertEqual(added.status_code, 201)
            gid = added.json["id"]
            self.assertIsNone(self.report()["goals"][0]["target_date"])
            self.assertEqual(self.report()["goals"][0]["saved_cents"], 25000)
            self.assertEqual(
                self.goal_post(
                    f"/api/goals/{gid}/edit",
                    name="Car fund",
                    saved_amount="500",
                    target_date="2027-06-01",
                ).status_code,
                200,
            )
            goal = self.report()["goals"][0]
            self.assertEqual(
                (goal["name"], goal["target_date"], goal["saved_cents"]),
                ("Car fund", "2027-06-01", 50000),
            )
            for amount in ("1000", "1200"):
                self.goal_post(f"/api/goals/{gid}/edit", saved_amount=amount)
                self.assertEqual(self.report()["goals"], [])
                self.assertEqual(len(self.client.get("/api/goals").json["goals"]), 1)
            self.goal_post(
                f"/api/goals/{gid}/edit", target_amount="2000", saved_amount="1200"
            )
            self.assertEqual(len(self.report()["goals"]), 1)
            # Tracking savings must not turn it into income or spending.
            self.assertEqual(
                (self.report()["income_cents"], self.report()["expense_cents"]), (0, 0)
            )
            self.assertEqual(
                self.goal_post(f"/api/goals/{gid}/delete").status_code, 200
            )
            self.assertEqual(self.client.get("/api/goals").json["goals"], [])

        def test_goals_validation_and_privacy(self):
            for fields in [
                dict(name=" "),
                dict(name="a" * 121),
                dict(target_amount=""),
                dict(target_amount="0"),
                dict(target_amount="-1"),
                dict(target_amount="abc"),
                dict(target_amount="1.234"),
                dict(saved_amount="-1"),
                dict(saved_amount="NaN"),
                dict(target_date="2027-02-30"),
            ]:
                self.assertEqual(self.goal_post(**fields).status_code, 400)
            self.assertEqual(self.client.get("/api/goals").json["goals"], [])
            gid = self.goal_post(saved_amount="0").json["id"]
            self.assertEqual(
                self.goal_post(
                    f"/api/goals/{gid}/edit", target_amount="bad"
                ).status_code,
                400,
            )
            self.assertEqual(self.report()["goals"][0]["saved_cents"], 0)
            guest = self.module.app.test_client()
            self.assertEqual(guest.get("/api/goals").status_code, 401)
            token = guest.get("/api/csrf").json["csrf_token"]
            self.assertEqual(
                guest.post("/api/goals", headers={"X-CSRF-Token": token}).status_code,
                401,
            )
            self.assertEqual(self.client.post("/api/goals").status_code, 403)
            with closing(self.module.connect_db()) as db, db:
                uid = db.execute(
                    "INSERT INTO users(email,password_hash) VALUES('goal@example.com','unused')"
                ).lastrowid
            with guest.session_transaction() as sess:
                sess["user_id"] = uid
            self.assertEqual(guest.get("/api/goals").json["goals"], [])
            for action in ("edit", "delete"):
                self.assertEqual(
                    guest.post(
                        f"/api/goals/{gid}/{action}",
                        data=dict(
                            name="Private", target_amount="100", saved_amount="0"
                        ),
                        headers={"X-CSRF-Token": token},
                    ).status_code,
                    404,
                )
            self.assertEqual(len(self.report()["goals"]), 1)

        # Account settings: Check failures leave the old email and password in place.
        def account_post(self, path, **data):
            token = self.client.get("/api/csrf").json["csrf_token"]
            return self.client.post(path, data=data, headers={"X-CSRF-Token": token})

        def test_account_updates(self):
            path = "/api/account/update"
            data = dict(email="new@example.com", current_password="Test123!",
                        new_password="Changed123!", confirm_password="different")
            self.assertEqual(self.account_post(path, **data).status_code, 400)
            self.assertEqual(self.client.get("/api/account").json["email"], "admin@admin.com")
            data.update(confirm_password="Changed123!", current_password="wrong")
            self.assertEqual(self.account_post(path, **data).status_code, 400)
            data.update(current_password="Test123!", email="invalid")
            self.assertEqual(self.account_post(path, **data).status_code, 400)
            with closing(self.module.connect_db()) as db, db:
                db.execute("INSERT INTO users(email,password_hash) VALUES('taken@example.com','unused')")
            data["email"] = "TAKEN@example.com"
            self.assertEqual(self.account_post(path, **data).status_code, 409)
            data["email"] = "new@example.com"
            self.assertEqual(self.account_post(path, **data).status_code, 200)
            self.assertEqual(self.client.get("/api/account").json["email"], "new@example.com")
            self.assertEqual(self.account_post("/api/login", email="new@example.com", password="Test123!").status_code, 401)
            self.assertEqual(self.account_post("/api/login", email="new@example.com", password="Changed123!").status_code, 200)
            self.assertEqual(self.account_post(path, email="next@example.com",
                             current_password="Changed123!").status_code, 200)

        def test_same_password_and_demo_toggle(self):
            response = self.account_post("/api/account/update", email="unchanged@example.com",
                current_password="Test123!", new_password="Test123!", confirm_password="Test123!")
            self.assertEqual(response.status_code, 400)
            self.assertIn("different", response.json["message"])
            self.assertEqual(self.client.get("/api/account").json["email"], "admin@admin.com")
            for action, active in (("enable", True), ("disable", False), ("disable", False), ("enable", True)):
                result = self.account_post("/api/account/premium/" + action)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json["membership"]["is_premium"], active)
                self.assertEqual(self.client.get("/api/account/export").status_code, 200 if active else 403)
            guest = self.module.app.test_client()
            token = guest.get("/api/csrf").json["csrf_token"]
            for action in ("enable", "disable"):
                path = "/api/account/premium/" + action
                self.assertEqual(guest.post(path, headers={"X-CSRF-Token":token}).status_code, 401)
                self.assertEqual(self.client.post(path).status_code, 403)

        # Premium: Cancellation keeps today's access, but expires at the period boundary.
        def test_membership_lifecycle_and_export(self):
            self.assertEqual(self.client.get("/api/account/export").status_code, 403)
            result = self.account_post("/api/account/premium/subscribe").json["membership"]
            self.assertTrue(result["is_premium"])
            expires = result["expires_on"]
            self.assertEqual(self.account_post("/api/account/premium/subscribe").json["membership"]["expires_on"], expires)
            self.assertEqual(self.client.get("/api/account/export").status_code, 200)
            result = self.account_post("/api/account/premium/cancel").json["membership"]
            self.assertTrue(result["is_premium"])
            self.assertTrue(result["cancel_at_period_end"])
            with closing(self.module.connect_db()) as db, db:
                db.execute("UPDATE users SET premium_until=? WHERE id=?",
                           (date.today().isoformat(), self.user_id))
            self.assertFalse(self.client.get("/api/account").json["membership"]["is_premium"])
            self.assertEqual(self.client.get("/api/account/export").status_code, 403)
            self.assertTrue(self.account_post("/api/account/premium/subscribe").json["membership"]["is_premium"])
            with closing(self.module.connect_db()) as db, db:
                db.execute("UPDATE users SET premium_until=? WHERE id=?",
                           ((date.today()-timedelta(days=65)).isoformat(), self.user_id))
            self.assertTrue(self.client.get("/api/account").json["membership"]["is_premium"])

        # Private account routes must still require a login and a valid form token.
        def test_account_access_and_export_scope(self):
            guest = self.module.app.test_client()
            self.assertEqual(guest.get("/api/account").status_code, 401)
            self.assertEqual(guest.get("/api/account/export").status_code, 401)
            token = guest.get("/api/csrf").json["csrf_token"]
            for path in ("/api/account/update", "/api/account/premium/subscribe", "/api/account/premium/cancel"):
                self.assertEqual(guest.post(path, headers={"X-CSRF-Token":token}).status_code, 401)
                self.assertEqual(self.client.post(path).status_code, 403)
            with closing(self.module.connect_db()) as db, db:
                other = db.execute("INSERT INTO users(email,password_hash) VALUES('private@example.com','unused')").lastrowid
                for uid, source in ((other, "Secret"), (self.user_id, "=FORMULA")):
                    db.execute("INSERT INTO incomes(user_id,amount_cents,source,income_date) VALUES(?,123,?,'2026-11-17')", (uid,source))
            self.account_post("/api/account/premium/subscribe")
            output = self.client.get("/api/account/export").text
            self.assertNotIn("Secret", output)
            self.assertIn("'=FORMULA", output)
            self.assertIn("1.23", output)

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

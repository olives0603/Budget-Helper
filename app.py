"""Handles login and sign-up for both PHP pages.

Run python app.py, then open http://localhost/practice/login.php.
"""

# App settings
import re
import secrets
import sqlite3
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template_string,
    request,
    session,
)
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

PROJECT_FOLDER = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_FOLDER / "users.db"
SECRET_KEY_PATH = PROJECT_FOLDER / ".session_secret"
LOGIN_PAGE = "http://localhost/practice/login.php"
INVALID_LOGIN_MESSAGE = "Incorrect username or password."
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

app = Flask(__name__)

# Cookies let Python remember which browser is logged in.
CORS(
    app,
    origins=[re.compile(r"^http://(?:localhost|127\.0\.0\.1)(?::[0-9]+)?$")],
    supports_credentials=True,
)

# Keep the same key when the server restarts so users stay logged in.
# Store this file and users.db next to app.py, not in htdocs.
if not SECRET_KEY_PATH.exists():
    SECRET_KEY_PATH.write_text(secrets.token_hex(32), encoding="utf-8")

app.secret_key = SECRET_KEY_PATH.read_text(encoding="utf-8").strip()
app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024,
    SESSION_COOKIE_NAME="budgetbuddy_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)


# Database
def connect_db():
    """Open the database so we can read fields by name, like user["email"]."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Set up the users table on the first run."""
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
    finally:
        connection.close()


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


# Helpers used by both forms
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


# Check form requests
@app.before_request
def protect_form_submissions():
    """Check the token before accepting a form submission."""
    if request.method != "POST":
        return None

    # Look for the token in the request header or the logout form.
    provided = (
        request.headers.get("X-CSRF-Token")
        or request.form.get("csrf_token", "")
    )
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


# Create an account
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


# Log in
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


# Dashboard and logout
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BudgetWise | Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f7f2;
            color: #203b30;
            padding: 24px;
        }

        main {
            max-width: 650px;
            margin: 60px auto;
            padding: 36px;
            background: white;
            border-radius: 20px;
        }

        button {
            padding: 12px 24px;
            background: #28734f;
            color: white;
            border: 0;
            border-radius: 8px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <main>
        <p>BudgetBuddy</p>
        <h1>Welcome to your account</h1>
        <p>You are logged in as {{ email }}.</p>
        <p>Main Dashboard.</p>

        <form action="/api/logout" method="POST">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            <button type="submit">Log Out</button>
        </form>
    </main>
</body>
</html>
"""


@app.get("/dashboard")
@app.get("/api/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(LOGIN_PAGE)

    # Displays the email as text, even if it contains HTML characters.
    return render_template_string(
        DASHBOARD_HTML,
        email=session["email"],
        csrf_token=session["csrf_token"],
    )


@app.post("/logout")
@app.post("/api/logout")
def logout():
    session.clear()
    return redirect(LOGIN_PAGE)


@app.errorhandler(413)
def too_large(error):
    return error_response("The submitted information is too long.", 413)


# Start the app
initialize_database()
add_demo_account()

if __name__ == "__main__":
    print("Open http://localhost/practice/login.php with Apache running.")
    app.run(host="127.0.0.1", port=5000)

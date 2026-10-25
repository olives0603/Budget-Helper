<?php
// PHP shows the page; Python checks the form when it is submitted.
$title = "BudgetBuddy | Create an Account";
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <!-- The title appears in the browser tab. -->
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo htmlspecialchars($title, ENT_QUOTES, "UTF-8"); ?></title>

    <style>
        /* Colors, spacing, and layout for this page. */
        * {
            box-sizing: border-box;
        }

        body {
            font-family: Arial, sans-serif;
            background: #f4f7f2;
            color: #203b30;
            min-height: 100vh;
            margin: 0;
            padding: 24px;
            display: grid;
            place-items: center;
        }

        main {
            width: 100%;
            max-width: 420px;
            padding: 36px;
            background: white;
            border: 1px solid #dce7dd;
            border-radius: 20px;
            box-shadow: 0 12px 36px rgba(32,59,48,.08);
        }

        .brand {
            color: #28734f;
            font-weight: bold;
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        h1 {
            font-size: 28px;
        }

        .subtitle, .hint {
            color: #607268;
            line-height: 1.6;
        }

        .hint {
            font-size: 13px;
        }

        label {
            display: block;
            font-weight: bold;
            margin-top: 18px;
        }

        input {
            width: 100%;
            padding: 13px;
            margin-top: 8px;
            border: 1px solid #b9cbbf;
            border-radius: 8px;
            background: #fafcf9;
            font: inherit;
        }

        input:focus {
            outline: 3px solid #cce7d7;
            border-color: #28734f;
        }

        button {
            width: 100%;
            padding: 14px;
            margin-top: 24px;
            background: #28734f;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }

        button:hover {
            background: #1d583c;
        }

        button:disabled {
            opacity: .65;
            cursor: wait;
        }

        button:focus-visible, a:focus-visible {
            outline: 3px solid #28734f;
            outline-offset: 3px;
        }

        .error {
            background: #fff1f0;
            color: #a32929;
            padding: 12px;
            border-radius: 8px;
        }

        .back-link {
            display: block;
            margin-top: 20px;
            color: #28734f;
            text-align: center;
        }

    </style>
</head>
<body>
    <main>
        <!-- Page heading. -->
        <p class="brand">BudgetBuddy</p>
        <h1>Create an account</h1>
        <p class="subtitle">
            Start Budgeting today!.
        </p>

        <!-- Show errors here without leaving the page. -->
        <p id="register-error" class="error" role="alert" hidden></p>

        <!-- Python uses the input names to read the submitted values.
             JavaScript sends the form to port 5000 without reloading the page. -->
        <form id="register-form" action="/api/register" method="POST">
            <label for="email">Email</label>
            <input
                type="email"
                id="email"
                name="email"
                autocomplete="username"
                maxlength="254"
                required
            >

            <label for="password">Password</label>
            <input
                type="password"
                id="password"
                name="password"
                autocomplete="new-password"
                minlength="8"
                maxlength="128"
                aria-describedby="password-hint"
                required
            >

            <p id="password-hint" class="hint">
                Use 8–128 characters. Your password cannot be only spaces.
            </p>

            <label for="confirm-password">Confirm Password</label>
            <input
                type="password"
                id="confirm-password"
                name="confirm_password"
                autocomplete="new-password"
                minlength="8"
                maxlength="128"
                required
            >

            <button type="submit">Create Account</button>
        </form>

        <!-- Link to the other form. -->
        <a class="back-link" href="/practice/login.php">
            Already have an account? Log in
        </a>
    </main>

    <script>
        "use strict";

        // Both forms use the Python server on port 5000.
        const isRegistration = true;
        const backend = new URL(window.location.href);
        backend.port = "5000";
        const apiOrigin = backend.origin;
        const endpoint = isRegistration ? "/api/register" : "/api/login";

        const form = document.getElementById("register-form");
        const errorMessage = document.getElementById("register-error");
        const submitButton = form.querySelector('button[type="submit"]');
        const originalLabel = submitButton.textContent;

        function showError(message) {
            // Show the message as text so it cannot insert HTML into the page.
            errorMessage.textContent = message;
            errorMessage.hidden = false;
        }

        // Keep the user on this page while Python checks the form.
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            errorMessage.hidden = true;
            errorMessage.textContent = "";
            const formData = new FormData(form);

            // Catch mismatched passwords before sending the form.
            // Python checks them again on the server.
            if (
                isRegistration &&
                formData.get("password") !== formData.get("confirm_password")
            ) {
                showError("Passwords do not match.");
                return;
            }

            submitButton.disabled = true;
            submitButton.textContent = isRegistration
                ? "Creating account..."
                : "Checking...";

            try {
                // Get the token Python expects with this form.
                // Include cookies so it recognizes the same browser session.
                const tokenResponse = await fetch(apiOrigin + "/api/csrf", {
                    credentials: "include",
                    cache: "no-store"
                });

                if (!tokenResponse.ok) {
                    throw new Error(
                        "The Python server returned HTTP " + tokenResponse.status +
                        ". Restart the updated app.py."
                    );
                }
                const tokenData = await tokenResponse.json();

                // Send the entered details and token to Python.
                const response = await fetch(apiOrigin + endpoint, {
                    method: "POST",
                    body: formData,
                    credentials: "include",
                    headers: {"X-CSRF-Token": tokenData.csrf_token}
                });

                const contentType = response.headers.get("content-type") || "";
                if (!contentType.includes("application/json")) {
                    throw new Error(
                        "The server returned an unexpected response. " +
                        "Restart the updated app.py."
                    );
                }
                const result = await response.json();

                // Move to the next page if it worked. Otherwise, show the error here.
                if (response.ok && result.success) {
                    window.location.href = isRegistration
                        ? "/practice/login.php"
                        : apiOrigin + "/api/dashboard";
                    return;
                }
                showError(result.message || "Unable to process your request.");
            } catch (error) {
                // Explain when the server cannot be reached.
                const message = error instanceof TypeError
                    ? "Cannot reach Python on port 5000. " +
                      "Start app.py and keep its terminal open."
                    : error.message;
                showError(message);
            } finally {
                // Turn the button back on so the user can try again.
                submitButton.disabled = false;
                submitButton.textContent = originalLabel;
            }
        });
    </script>
</body>
</html>

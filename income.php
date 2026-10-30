<?php
// Income page: PHP builds the page; JavaScript loads this account's entries.
$title = "Your income";
$subtitle = "Keep track of what comes in, one entry at a time.";
$page = "income";

// The dashboard menu keeps a place for the sections we will build later.
header("Cache-Control: no-store");

// Income is ready too. The remaining sections will be added later.
$navigation = [
    "dashboard" => ["Dashboard", "dashboard.php"],
    "income" => ["Income", "income.php"],
    "expenses" => ["Expenses", null],
    "statistics" => ["Statistics", null],
    "goals" => ["Savings goals", null],
    "account" => ["Account management", null],
];

// Escape text before placing it in HTML so it cannot become a tag or attribute.
function escape_html($value)
{
    return htmlspecialchars($value, ENT_QUOTES, "UTF-8");
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <!-- Let the layout use the actual screen width on phones and tablets. -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BudgetBuddy | <?php echo escape_html($title); ?></title>
    <!-- Page styling stays here so there is no separate CSS file to copy. -->
<style>
/* Shared colors and spacing keep every section close to the original login theme. */
:root {
  --bg: #f4f7f2;
  --paper: #fff;
  --ink: #203b30;
  --muted: #607268;
  --green: #28734f;
  --line: #dce7dd;
}
* {
  box-sizing: border-box;
}
[hidden] {
  display: none !important;
}
body {
  margin: 0;
  color: var(--ink);
  background: var(--bg);
  font:
    14px/1.55 Arial,
    sans-serif;
}
a {
  color: var(--green);
}
button,
input,
select {
  font: inherit;
}
button,
.button {
  cursor: pointer;
}
button:disabled {
  opacity: 0.55;
  cursor: wait;
}
a:focus-visible,
button:focus-visible {
  outline: 3px solid #81af94;
  outline-offset: 3px;
}
.sidebar {
  width: 236px;
  position: fixed;
  inset: 0 auto 0 0;
  background: #fff;
  border-right: 1px solid var(--line);
  padding: 34px 20px 22px;
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--ink);
  font-size: 21px;
  font-weight: bold;
  text-decoration: none;
}
.brand-mark {
  display: grid;
  place-items: center;
  border-radius: 10px;
  width: 36px;
  height: 36px;
  background: var(--green);
  color: white;
  font-size: 25px;
}
.nav-caption {
  color: var(--muted);
  font-size: 10px;
  letter-spacing: 1.5px;
  margin: 42px 12px 12px;
}
nav a {
  display: flex;
  gap: 14px;
  padding: 12px;
  margin: 4px 0;
  border-radius: 8px;
  color: var(--muted);
  text-decoration: none;
}
nav a:hover {
  background: #f4f7f2;
}
nav a[aria-current] {
  background: #e9f3eb;
  color: var(--green);
  font-weight: bold;
}
.nav-number {
  font-size: 11px;
  opacity: 0.6;
  padding-top: 3px;
}
.sidebar-bottom {
  margin-top: auto;
  border-top: 1px solid var(--line);
  padding: 16px 12px 0;
  color: var(--muted);
}
.text-button {
  background: none;
  border: 0;
  padding: 6px 0;
  color: var(--green);
}
.workspace {
  margin-left: 236px;
}
.topbar {
  height: 74px;
  padding: 0 40px;
  border-bottom: 1px solid var(--line);
  background: #ffffffb3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}
.topbar > span {
  letter-spacing: 1.5px;
  font-size: 10px;
  color: var(--muted);
}
#account-label {
  max-width: 50%;
  overflow-wrap: anywhere;
  text-decoration: none;
  font-size: 12px;
}
main {
  max-width: 1320px;
  margin: auto;
  padding: 36px 40px;
}
.eyebrow {
  font-size: 10px;
  letter-spacing: 1.6px;
  color: var(--green);
  margin: 0 0 10px;
}
h1 {
  font-size: 34px;
  letter-spacing: -1px;
  line-height: 1.2;
  margin: 0 0 10px;
}
h2 {
  font-size: 17px;
  margin: 0;
}
h3 {
  font-size: 14px;
  margin: 0;
}
p {
  margin: 0 0 10px;
}
.subtitle,
.muted,
.hint {
  color: var(--muted);
}
.hint {
  font-size: 12px;
}
.page-heading {
  margin-bottom: 26px;
}
.report-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.period-switch {
  padding: 4px;
  background: #e8eee7;
  border-radius: 9px;
  display: flex;
}
.period-switch button {
  background: none;
  border: none;
  padding: 8px 18px;
  color: var(--muted);
  border-radius: 6px;
  font-size: 12px;
}
.period-switch button[aria-pressed="true"] {
  background: #fff;
  color: var(--ink);
  box-shadow: 0 2px 5px #203b3010;
  font-weight: bold;
}
.date-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}
.date-controls input {
  width: auto;
  margin: 0;
  padding: 7px 10px;
  font-size: 12px;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin: 18px 0 22px;
}
.metric {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 22px;
  background: var(--paper);
}
.metric.accent {
  background: #245e42;
  color: #fff;
  border-color: #245e42;
}
.metric-label {
  font-size: 12px;
  color: var(--muted);
}
.accent .metric-label,
.accent .metric-note {
  color: #d3e6d9;
}
.metric-value {
  font-size: clamp(22px, 2.3vw, 34px);
  letter-spacing: -0.8px;
  margin: 12px 0 8px;
  overflow-wrap: anywhere;
  font-variant-numeric: tabular-nums;
}
.metric-note {
  font-size: 11px;
  color: var(--muted);
  margin: 0;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 22px;
}
.panel {
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--paper);
  margin-bottom: 22px;
  min-width: 0;
}
.dashboard-grid .panel {
  margin-bottom: 0;
}
.panel-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 4px;
}
.panel-heading a {
  font-size: 12px;
  white-space: nowrap;
  text-decoration: none;
}
.empty {
  padding: 30px 12px;
  text-align: center;
  color: var(--muted);
  background: #fafcf9;
  border: 1px dashed #dce7dd;
  border-radius: 8px;
  margin-top: 20px;
}
.empty strong {
  display: block;
  margin-bottom: 5px;
  color: var(--ink);
}
.empty a {
  display: inline-block;
  margin-top: 8px;
}
.data-row {
  border-bottom: 1px solid #edf1eb;
  padding: 17px 0;
}
.data-row:last-child {
  border-bottom: none;
}
.row-line {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}
.row-line span {
  overflow-wrap: anywhere;
}
.progress {
  width: 100%;
  height: 7px;
  accent-color: var(--green);
  margin: 10px 0 3px;
  display: block;
  border: 0;
  border-radius: 8px;
  overflow: hidden;
}
.progress::-webkit-progress-bar {
  background: #edf2eb;
}
.progress::-webkit-progress-value {
  background: #42815d;
}
.progress::-moz-progress-bar {
  background: #42815d;
}
.progress.over::-webkit-progress-value {
  background: #aa593e;
}
.danger {
  color: #a32929;
}
.notice {
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 18px;
  font-size: 13px;
}
.info {
  background: #edf3e9;
  color: #4b634e;
}
.error {
  background: #fff1f0;
  color: #a32929;
}
.success {
  background: #e8f3eb;
  color: #28734f;
}
.badge {
  border-radius: 20px;
  padding: 3px 9px;
  font-size: 11px;
  background: #edf3e9;
  color: var(--green);
  white-space: nowrap;
}
.quick-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 22px;
}
.button,
.primary,
.secondary {
  display: inline-block;
  text-decoration: none;
  border-radius: 8px;
  padding: 10px 16px;
  font-weight: bold;
  border: 0;
}
.primary,
.button {
  background: var(--green);
  color: white;
}
.secondary {
  background: #e9f1e9;
  color: var(--green);
}
.primary:hover,
.button:hover {
  background: #1d583c;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}
label {
  display: block;
  font-size: 13px;
  font-weight: bold;
}
input,
select {
  padding: 11px 12px;
  border: 1px solid #b9cbbf;
  background: #fafcf9;
  border-radius: 8px;
  width: 100%;
  margin-top: 7px;
  color: var(--ink);
}
input:focus,
select:focus {
  outline: 3px solid #cce7d7;
  border-color: var(--green);
}
input[type="checkbox"] {
  width: auto;
  margin: 0 8px 0 0;
  accent-color: var(--green);
}
fieldset {
  border: 0;
  padding: 0;
  margin: 18px 0 0;
  min-width: 0;
}
.form-actions {
  margin-top: 22px;
}
.table-wrap {
  overflow-x: auto;
}
table {
  border-collapse: collapse;
  width: 100%;
  text-align: left;
  font-size: 13px;
}
th {
  font-size: 11px;
  color: var(--muted);
  background: #f4f7f2;
}
th,
td {
  padding: 13px 12px;
  border-bottom: 1px solid #edf1eb;
}
td {
  overflow-wrap: anywhere;
  max-width: 260px;
}
.inline-form {
  display: flex;
  gap: 8px;
  align-items: center;
}
.inline-form input {
  max-width: 120px;
  margin: 0;
}
.page-footer {
  font-size: 11px;
  color: var(--muted);
  padding: 32px 0 0;
}
@media (max-width: 1050px) {
  .sidebar {
    width: 205px;
  }
  .workspace {
    margin-left: 205px;
  }
  main {
    padding: 28px 22px;
  }
  .topbar {
    padding: 0 22px;
  }
  .metric {
    padding: 18px;
  }
}
/* On smaller screens, move the navigation above the page and stack the panels. */
@media (max-width: 760px) {
  .sidebar {
    position: static;
    width: auto;
    padding: 18px 16px 10px;
  }
  .brand {
    font-size: 18px;
  }
  .nav-caption,
  .sidebar-bottom p,
  .nav-number {
    display: none;
  }
  nav {
    display: flex;
    overflow-x: auto;
    gap: 4px;
    margin-top: 12px;
  }
  nav a {
    white-space: nowrap;
    font-size: 12px;
    padding: 8px 10px;
  }
  .sidebar-bottom {
    border: 0;
    padding: 0;
    margin: 0;
    position: absolute;
    top: 22px;
    right: 20px;
  }
  .workspace {
    margin-left: 0;
  }
  .topbar {
    height: 48px;
  }
  main {
    padding: 26px 16px;
  }
  h1 {
    font-size: 29px;
  }
  .metrics {
    gap: 8px;
  }
  .metric {
    padding: 13px 10px;
  }
  .metric-label {
    font-size: 11px;
  }
  .metric-value {
    font-size: 20px;
  }
  .dashboard-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }
  .panel {
    padding: 20px 16px;
  }
  .date-controls {
    flex-wrap: wrap;
  }
}

/* Future sections are labels, not links to unfinished pages. */
.nav-placeholder {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 12px;
  margin: 4px 0;
  color: #7b877e;
}
.nav-placeholder small {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
@media (max-width: 760px) {
  .nav-placeholder {
    white-space: nowrap;
    font-size: 12px;
    padding: 8px 10px;
  }
}

/* Keep hidden forms hidden even when their layout uses a grid. */
[hidden] { display: none !important; }
</style>
    
    
</head>
<body data-page="<?php echo escape_html($page); ?>">
    <!-- Navigation stays available while the account data is loading. -->
    <aside class="sidebar">
        <a class="brand" href="/practice/dashboard.php"><span class="brand-mark">b.</span> BudgetBuddy</a>
        <p class="nav-caption">YOUR MONEY IN VIEW</p>
        <nav aria-label="Main navigation">
            <?php foreach ($navigation as $key => [$label, $file]): ?>
                <?php if ($file !== null): ?>
                    <a href="/practice/<?php echo escape_html(
                        $file,
                    ); ?>" <?php if (
    $key === $page
): ?>aria-current="page"<?php endif; ?>>
                        <?php echo escape_html($label); ?>
                    </a>
                <?php else: ?>
                    <span class="nav-placeholder" aria-disabled="true">
                        <?php echo escape_html($label); ?>
                        <small>Later</small>
                    </span>
                <?php endif; ?>
            <?php endforeach; ?>
        </nav>
        <div class="sidebar-bottom">
            <p><br></p>
            <button id="logout" class="text-button" type="button">Log out ↗</button>
        </div>
    </aside>
    <div class="workspace">
        <header class="topbar"><span>MY FINANCIAL SPACE</span><span id="account-label">Your account</span></header>
        <main>
            <div class="page-heading"><div><p class="eyebrow">BUDGETBUDDY / <?php echo escape_html(
                strtoupper($title),
            ); ?></p>
                <h1><?php echo escape_html(
                    $title,
                ); ?></h1><p class="subtitle"><?php echo escape_html(
    $subtitle,
); ?></p></div></div>
            <noscript><p class="notice error">Enable JavaScript to load your account and financial records.</p></noscript>
            <p id="page-error" class="notice error" role="alert" hidden></p>
            <p id="page-status" class="muted" role="status">Checking your account…</p>
            <!-- Show the account content once Python confirms the user is logged in. -->
            <div id="page-content" hidden>

<!-- Income form: the same fields are used when adding or editing an entry. -->
<section class="panel">
  <h2 id="form-heading">Add income</h2>
  <p class="hint">Record money you have received. All amounts are in USD.</p>
  <p id="save-message" class="notice success" role="status" hidden></p>
  <p id="form-error" class="notice error" role="alert" hidden></p>
  <form id="income-form">
    <fieldset id="entry-fields"><legend class="hint">Income details</legend>
      <div class="form-grid">
        <label>Amount ($)<input name="amount" type="number" min="0.01" max="999999999.99" step="0.01" required placeholder="0.00"></label>
        <label>Source<input name="source" maxlength="120" required placeholder="Paycheck, gift, bonus…"></label>
        <label>Date received<input name="income_date" type="date" min="1900-01-01" max="9998-12-31" required></label>
        <label style="align-self:center"><input name="is_recurring" type="checkbox">This income is recurring</label>
      </div>
      <p class="hint">Recurring is a label only. Add each payment when you receive it.</p>
      <div class="form-actions"><button id="save-entry" class="primary" type="submit">Add income</button> <button id="cancel-edit" class="secondary" type="button" hidden>Cancel edit</button></div>
    </fieldset>
  </form>
</section>
<!-- Filters are separate from the entry form and never change saved records. -->
<section class="panel" style="margin-top:24px">
  <h2>Your income</h2>
  <form id="filter-form">
    <fieldset><legend class="hint">Find an entry</legend>
      <div class="form-grid">
        <label>Date range<select name="period"><option value="all">All dates</option><option value="week">Past week (7 days)</option><option value="month">Past month (30 days)</option><option value="year">Past year (365 days)</option><option value="custom">Custom dates</option></select></label>
        <label>Source contains<input name="source" maxlength="120" placeholder="Any source"></label>
        <label>Minimum amount ($)<input name="min_amount" type="number" min="0" max="999999999.99" step="0.01"></label>
        <label>Maximum amount ($)<input name="max_amount" type="number" min="0" max="999999999.99" step="0.01"></label>
        <label>Recurring<select name="recurring"><option value="all">All entries</option><option value="1">Recurring</option><option value="0">Not recurring</option></select></label>
      </div>
      <div id="custom-dates" class="form-grid" hidden>
        <label>From<input name="start" type="date" min="1900-01-01" max="9998-12-31" disabled></label>
        <label>Through<input name="end" type="date" min="1900-01-01" max="9998-12-31" disabled></label>
      </div>
      <div class="form-actions"><button class="primary" type="submit">Apply filters</button> <button id="clear-filters" class="secondary" type="button">Clear filters</button></div>
    </fieldset>
  </form>
  <p id="filter-error" class="notice error" role="alert" hidden></p>
  <p id="list-status" class="hint" role="status">Loading income…</p>
  <p id="no-results" class="notice info" role="status" hidden></p>
  <!-- JavaScript fills the table after Python returns the saved entries. -->
  <div class="table-wrap"><table id="income-table" hidden><caption class="hint">Saved income, newest date first</caption><thead><tr><th scope="col">Date received</th><th scope="col">Source</th><th scope="col">Amount</th><th scope="col">Recurring</th><th scope="col">Actions</th></tr></thead><tbody id="income-rows"></tbody></table></div>
</section>

            </div>
            <footer class="page-footer"></footer>
        </main>
    </div>
<!-- Income controls run after the form and table are in place. -->
<script>
"use strict";
// All pages use the same server and session cookie.
const backend = new URL(window.location.href);
backend.port = "5000";
const API_ORIGIN = backend.origin;
// The database stores cents. Divide by 100 only when displaying dollars.
const money = (cents) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
    cents / 100,
  );
const calendarLabel = (value) => {
  const [year, month, day] = value.split("-");
  return `${month}/${day}/${year}`;
};
// Use the browser's local date so the default does not shift at midnight UTC.
function todayValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
// Create page elements safely; entered text is never interpreted as HTML.
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function showError(error) {
  const box = document.getElementById("page-error");
  box.textContent =
    error instanceof TypeError
      ? "Cannot reach the server. Keep app.py running and try again."
      : error.message;
  box.hidden = false;
}
// Send the session cookie with each request and handle expired logins in one place.
async function api(path, options = {}) {
  const response = await fetch(API_ORIGIN + path, {
    ...options,
    credentials: "include",
    cache: "no-store",
  });
  if (response.status === 401) {
    document.getElementById("page-content").hidden = true;
    window.location.replace("/practice/login.php");
    throw new Error("Please log in again.");
  }
  if (
    !(response.headers.get("content-type") || "").includes("application/json")
  ) {
    throw new Error(
      "The server returned an unexpected response. Run the updated app.py.",
    );
  }
  const result = await response.json();
  if (!response.ok) throw new Error(result.message || "The request failed.");
  return result;
}
// Changes need a CSRF token as well as the login cookie. Python checks both.
async function post(path, data) {
  const token = await api("/api/csrf");
  return api(path, {
    method: "POST",
    body: data,
    headers: { "X-CSRF-Token": token.csrf_token },
  });
}
// Check the login before loading this account’s information.
const sessionReady = api("/api/account").then((account) => {
  document.getElementById("account-label").textContent = account.email;
  document.getElementById("page-content").hidden = false;
  document.getElementById("page-status").hidden = true;
  return account;
});
sessionReady.catch((error) => {
  document.getElementById("page-status").textContent =
    "Refresh this page after the server is available.";
  showError(error);
});
document.getElementById("logout").addEventListener("click", async (event) => {
  event.currentTarget.disabled = true;
  try {
    const token = await api("/api/csrf");
    // Submit a normal form so Python can send the user back to login.
    const form = document.createElement("form");
    form.method = "POST";
    form.action = API_ORIGIN + "/api/logout";
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = "csrf_token";
    input.value = token.csrf_token;
    form.append(input);
    document.body.append(form);
    form.submit();
  } catch (error) {
    showError(error);
    event.currentTarget.disabled = false;
  }
});


// Income form and messages.
const entryForm = document.getElementById("income-form");
const filters = document.getElementById("filter-form");
// No ID means a new entry. Clicking Edit sets the ID of the saved entry.
let editingId = null;
let saving = false;
let deleting = false;
let requestNumber = 0;
// Keep the last applied filters while adding, changing, or deleting an entry.
let appliedFilters = new URLSearchParams();
entryForm.elements.income_date.value = todayValue();
function message(id, text) {
  const box = document.getElementById(id);
  box.textContent = text;
  box.hidden = !text;
}
function friendlyError(error) {
  return error instanceof TypeError ? "Cannot reach the server. Keep app.py running and try again." : error.message;
}
// Return to Add income after saving or cancelling; saved records stay untouched.
function resetEntry() {
  editingId = null;
  entryForm.reset();
  entryForm.elements.income_date.value = todayValue();
  document.getElementById("form-heading").textContent = "Add income";
  document.getElementById("save-entry").textContent = "Add income";
  document.getElementById("cancel-edit").hidden = true;
  message("form-error", "");
}
document.getElementById("cancel-edit").addEventListener("click", resetEntry);
entryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (saving || !entryForm.reportValidity()) return;
  message("form-error", "");
  message("save-message", "");
  if (!entryForm.elements.source.value.trim()) {
    message("form-error", "Enter where the money came from.");
    entryForm.elements.source.focus();
    return;
  }
  // Unchecked checkboxes are normally omitted, so send an explicit 0 or 1.
  const data = new FormData(entryForm);
  data.set("is_recurring", entryForm.elements.is_recurring.checked ? "1" : "0");
  const wasEditing = editingId !== null;
  saving = true;
  document.getElementById("entry-fields").disabled = true;
  try {
    await post(wasEditing ? `/api/income/${editingId}/edit` : "/api/income", data);
    // Clear the form only after a successful save so errors do not erase typed details.
    resetEntry();
    message("save-message", wasEditing ? "Income updated." : "Income added.");
    await loadIncome();
  } catch (error) {
    message("form-error", friendlyError(error));
  } finally {
    saving = false;
    document.getElementById("entry-fields").disabled = false;
  }
});

// Put saved values back in the form when the user chooses Edit.
function editEntry(entry) {
  if (saving) return;
  editingId = entry.id;
  entryForm.elements.amount.value = (entry.amount_cents / 100).toFixed(2);
  entryForm.elements.source.value = entry.source;
  entryForm.elements.income_date.value = entry.income_date;
  entryForm.elements.is_recurring.checked = Boolean(entry.is_recurring);
  document.getElementById("form-heading").textContent = "Edit income";
  document.getElementById("save-entry").textContent = "Save changes";
  document.getElementById("cancel-edit").hidden = false;
  message("form-error", "");
  message("save-message", "");
  entryForm.elements.amount.focus();
}
// Ask before deleting, then reload the list only after Python confirms the change.
async function removeEntry(entry, button) {
  if (saving || deleting) return;
  if (!window.confirm(`Delete ${money(entry.amount_cents)} from ${entry.source}?`)) return;
  deleting = true;
  button.disabled = true;
  message("save-message", "");
  message("form-error", "");
  try {
    await post(`/api/income/${entry.id}/delete`, new FormData());
    if (editingId === entry.id) resetEntry();
    message("save-message", "Income deleted.");
    await loadIncome();
  } catch (error) {
    message("form-error", friendlyError(error));
  } finally {
    deleting = false;
    button.disabled = false;
  }
}

// Build rows with textContent so a source is always treated as plain text.
function renderIncome(entries) {
  const rows = document.getElementById("income-rows");
  rows.replaceChildren();
  for (const entry of entries) {
    const row = element("tr");
    for (const value of [calendarLabel(entry.income_date), entry.source, money(entry.amount_cents), entry.is_recurring ? "Yes" : "No"]) row.append(element("td", value));
    const actions = element("td");
    const edit = element("button", "Edit", "secondary");
    const remove = element("button", "Delete", "secondary danger");
    edit.type = remove.type = "button";
    edit.setAttribute("aria-label", `Edit ${entry.source} on ${entry.income_date}`);
    remove.setAttribute("aria-label", `Delete ${entry.source} on ${entry.income_date}`);
    edit.addEventListener("click", () => editEntry(entry));
    remove.addEventListener("click", () => removeEntry(entry, remove));
    actions.append(edit, document.createTextNode(" "), remove);
    row.append(actions);
    rows.append(row);
  }
  document.getElementById("income-table").hidden = !entries.length;
  const filtered = [...appliedFilters.entries()].some(([key, value]) => value && value !== "all");
  message("no-results", entries.length ? "" : filtered ? "No results found. Change or clear your filters to see other entries." : "No income recorded yet. Add your first entry above.");
  message("list-status", `${entries.length} ${entries.length === 1 ? "entry" : "entries"} shown · Total ${money(entries.reduce((sum, entry) => sum + entry.amount_cents, 0))}`);
}
// Fetch this account's entries using the filters last submitted by the user.
async function loadIncome() {
  const current = ++requestNumber;
  message("filter-error", "");
  message("list-status", "Loading income…");
  document.getElementById("income-table").hidden = true;
  message("no-results", "");
  try {
    await sessionReady;
    const result = await api("/api/income?" + appliedFilters.toString());
    // A slower response must not replace a newer filter result.
    if (current === requestNumber) renderIncome(result.entries);
  } catch (error) {
    if (current === requestNumber) {
      message("filter-error", friendlyError(error));
      message("list-status", "Income could not be loaded. Apply filters or clear them to try again.");
    }
  }
}

// Apply filters together, or clear them to show everything again.
// Custom dates are required only when Custom dates is selected.
function toggleDates() {
  const custom = filters.elements.period.value === "custom";
  document.getElementById("custom-dates").hidden = !custom;
  for (const name of ["start", "end"]) {
    filters.elements[name].disabled = !custom;
    filters.elements[name].required = custom;
  }
}
filters.elements.period.addEventListener("change", toggleDates);
filters.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!filters.reportValidity()) return;
  appliedFilters = new URLSearchParams(new FormData(filters));
  loadIncome();
});
document.getElementById("clear-filters").addEventListener("click", () => {
  filters.reset();
  toggleDates();
  appliedFilters = new URLSearchParams();
  loadIncome();
});
window.addEventListener("pageshow", (event) => { if (event.persisted) loadIncome(); });
loadIncome();

</script>
</body>
</html>

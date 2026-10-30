<?php
// The dashboard layout is PHP; JavaScript loads this account's saved totals.
$title = "Your financial overview";
$subtitle = "See where you stand, and plan your next step.";
$page = "dashboard";

header("Cache-Control: no-store");

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

</style>
    
    
</head>
<body data-page="<?php echo escape_html($page); ?>">
    <!-- Navigation stays available while the account data is loading. -->
    <aside class="sidebar">
        <a class="brand" href="/practice/dashboard.php"><span class="brand-mark">b.</span> BudgetBuddy</a>
        <p class="nav-caption">YOUR MONEY IN VIEW</p>
        <!-- These pages live together in the practice folder. -->
        <nav aria-label="Main navigation">
            <a href="dashboard.php" aria-current="page">Dashboard</a>
            <a href="income.php">Income</a>
            <span class="nav-placeholder" aria-disabled="true">Expenses <small>Later</small></span>
            <span class="nav-placeholder" aria-disabled="true">Statistics <small>Later</small></span>
            <span class="nav-placeholder" aria-disabled="true">Savings goals <small>Later</small></span>
            <span class="nav-placeholder" aria-disabled="true">Account management <small>Later</small></span>
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

<!-- Open the income form without waiting for a report to load. -->
<p><a class="button" href="income.php">Manage income</a></p>

<!-- Pick a calendar week, month, or year using a date inside that period. -->
<div class="report-toolbar">
    <div class="period-switch" role="group" aria-label="Report period">
        <button type="button" data-period="weekly" aria-pressed="false">Weekly</button>
        <button type="button" data-period="monthly" aria-pressed="true">Monthly</button>
        <button type="button" data-period="yearly" aria-pressed="false">Yearly</button>
    </div>
    <div class="date-controls"><label for="report-date">Date in period</label><input id="report-date" type="date" min="1900-01-01" max="9998-12-31" required><button id="refresh" class="secondary" type="button">Refresh</button></div>
</div>
<p id="report-range" class="hint" role="status">Loading your report…</p>
<p id="data-notice" class="notice info" hidden></p>
<!-- Values start blank so an empty database is never mistaken for real results. -->
<section class="metrics" aria-label="Financial totals">
    <article class="metric"><p class="metric-label">Total income</p><h2 id="income-total" class="metric-value">—</h2><p id="income-note" class="metric-note">Recorded in this period</p></article>
    <article class="metric"><p class="metric-label">Total expenses</p><h2 id="expense-total" class="metric-value">—</h2><p id="expense-note" class="metric-note">Recorded in this period</p></article>
    <article class="metric accent"><p class="metric-label">Money remaining</p><h2 id="remaining-total" class="metric-value">—</h2><p class="metric-note">Recorded income minus expenses</p></article>
</section>
<div class="dashboard-grid">
    <section class="panel"><div class="panel-heading"><h2>Savings goals</h2></div><p class="hint">Current progress · independent of report period</p><div id="goals-list"></div></section>
    <section class="panel"><div class="panel-heading"><h2>Spending limits</h2></div><p class="hint">Category spending against your selected period’s limits</p><div id="limits-list"></div></section>
    <section class="panel"><div class="panel-heading"><h2>Upcoming bills</h2></div><p id="bills-window" class="hint">Unpaid bills due within 30 days of the selected date</p><p id="overdue-note" class="hint danger" hidden></p><div id="bills-list"></div></section>
    <section class="panel"><div class="panel-heading"><h2>Where your money goes</h2></div><p class="hint">Recorded expenses by category</p><div id="category-list"></div></section>
</div>

<p class="hint" style="margin-top:16px">Remaining money is based on entered records, not a bank balance. Savings and unpaid bills are shown separately and are not deducted twice.</p>

            </div>
            <footer class="page-footer"></footer>
        </main>
    </div>
<!-- Load the report after the page elements are in place. -->
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


// Dashboard controls and report panels.
"use strict";
let selectedPeriod = "monthly";
// Count requests so a late reply cannot overwrite the user's newest selection.
let loadNumber = 0;
const reportDate = document.getElementById("report-date");
reportDate.value = todayValue();
// Empty panels explain what is missing instead of showing made-up figures.
function emptyState(container, heading, text) {
  const box = element("div", undefined, "empty");
  box.append(element("strong", heading), element("p", text));
  container.append(box);
}
// Reuse the same row layout for savings, limits, and spending categories.
function progressRow(container, title, current, target, note, warning = false) {
  const row = element("div", undefined, "data-row");
  const line = element("div", undefined, "row-line");
  line.append(
    element("strong", title),
    element("span", `${money(current)} / ${money(target)}`, "hint"),
  );
  const bar = element(
    "progress",
    undefined,
    warning ? "progress over" : "progress",
  );
  bar.max = target;
  bar.value = Math.min(current, target);
  bar.setAttribute(
    "aria-label",
    `${title}: ${money(current)} of ${money(target)}`,
  );
  row.append(line, bar, element("p", note, warning ? "hint danger" : "hint"));
  container.append(row);
}
// Fill the cards and panels with the totals returned for the selected period.
function renderReport(data) {
  document.getElementById("report-range").textContent =
    `${calendarLabel(data.start)} – ${calendarLabel(data.end)} · ${data.period} report · USD`;
  document.getElementById("income-total").textContent = money(
    data.income_cents,
  );
  document.getElementById("expense-total").textContent = money(
    data.expense_cents,
  );
  document.getElementById("remaining-total").textContent = money(
    data.remaining_cents,
  );
  document.getElementById("income-note").textContent =
    `${data.income_count} recorded income ${data.income_count === 1 ? "entry" : "entries"}`;
  document.getElementById("expense-note").textContent =
    `${data.expense_count} recorded expense ${data.expense_count === 1 ? "entry" : "entries"}`;
  const notice = document.getElementById("data-notice");
  notice.hidden = data.income_count > 0 && data.expense_count > 0;
  notice.textContent =
    !data.income_count && !data.expense_count
      ? "There is not enough information for a financial overview yet. Income and expense records are needed for this period. The zeros below mean no entries have been recorded."
      : `No ${data.income_count ? "expenses" : "income"} have been recorded for this period. These totals show only what you have entered.`;

  const goals = document.getElementById("goals-list");
  goals.replaceChildren();
  for (const goal of data.goals) {
    const percent = Math.round((goal.saved_cents / goal.target_cents) * 100);
    progressRow(
      goals,
      goal.name,
      goal.saved_cents,
      goal.target_cents,
      `${percent}% saved${percent >= 100 ? " · Goal reached" : ""}`,
    );
  }
  if (!data.goals.length)
    emptyState(
      goals,
      "Give your savings a purpose",
      "Saved goals will appear here when the savings section is connected.",
    );

  const limits = document.getElementById("limits-list");
  limits.replaceChildren();
  for (const limit of data.limits) {
    const left = limit.amount_cents - limit.spent_cents;
    progressRow(
      limits,
      limit.category,
      limit.spent_cents,
      limit.amount_cents,
      left >= 0
        ? `${money(left)} left in this ${data.period} limit`
        : `${money(-left)} over this ${data.period} limit`,
      left < 0,
    );
  }
  if (!data.limits.length)
    emptyState(
      limits,
      `No ${data.period} limits set`,
      "Saved limits will appear here when the spending section is connected.",
    );

  const bills = document.getElementById("bills-list");
  bills.replaceChildren();
  document.getElementById("bills-window").textContent =
    `Unpaid bills · ${calendarLabel(reportDate.value)} through ${calendarLabel(data.bills_through)}`;
  const overdue = document.getElementById("overdue-note");
  overdue.hidden = !data.overdue_count;
  overdue.textContent = `${data.overdue_count} overdue ${data.overdue_count === 1 ? "bill" : "bills"}.`;
  for (const bill of data.bills) {
    const row = element("div", undefined, "data-row");
    const line = element("div", undefined, "row-line");
    line.append(
      element("strong", bill.name),
      element("span", money(bill.amount_cents)),
    );
    row.append(
      line,
      element("p", `Due ${calendarLabel(bill.due_date)}`, "hint"),
    );
    bills.append(row);
  }
  if (!data.bills.length)
    emptyState(
      bills,
      "No upcoming bills recorded",
      "Unpaid bills due in this window will appear here.",
    );

  const categories = document.getElementById("category-list");
  categories.replaceChildren();
  for (const category of data.categories) {
    progressRow(
      categories,
      category.category,
      category.amount_cents,
      data.expense_cents,
      `${Math.round((category.amount_cents / data.expense_cents) * 100)}% of recorded expenses`,
    );
  }
  if (!data.categories.length)
    emptyState(
      categories,
      "No spending to break down yet",
      "Saved expenses will appear here when the expenses section is connected.",
    );
}
// Fetch a fresh report whenever the date, period, or Refresh button changes it.
async function loadReport() {
  if (!reportDate.reportValidity()) return;
  const requestNumber = ++loadNumber;
  document.getElementById("page-error").hidden = true;
  document.getElementById("report-range").textContent = "Loading your report…";
  try {
    await sessionReady;
    const data = await api(
      `/api/dashboard/summary?period=${selectedPeriod}&date=${reportDate.value}`,
    );
    // Ignore this result if the user has already picked another period.
    if (requestNumber === loadNumber) renderReport(data);
  } catch (error) {
    if (requestNumber === loadNumber) {
      showError(error);
      document.getElementById("report-range").textContent =
        "Report could not be refreshed. Any values below are from the last successful load.";
    }
  }
}
document.querySelectorAll("[data-period]").forEach((button) =>
  button.addEventListener("click", () => {
    selectedPeriod = button.dataset.period;
    document
      .querySelectorAll("[data-period]")
      .forEach((item) =>
        item.setAttribute("aria-pressed", String(item === button)),
      );
    loadReport();
  }),
);
reportDate.addEventListener("change", loadReport);
document.getElementById("refresh").addEventListener("click", loadReport);
window.addEventListener("pageshow", (event) => {
  if (event.persisted) loadReport();
});
loadReport();

</script>
</body>
</html>

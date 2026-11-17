<?php
// Goals page: PHP builds the page; JavaScript loads this account's entries.
$title = "Your savings goals";
$subtitle = "Set a goal and keep track of what you have saved.";
$page = "goals";

// The dashboard menu keeps a place for the sections we will build later.
header("Cache-Control: no-store");

// Keep unfinished sections visible until their pages are ready.
$navigation = [
    "dashboard" => ["Dashboard", "dashboard.php"],
    "income" => ["Income", "income.php"],
    "expenses" => ["Expenses", "expenses.php"],
    "statistics" => ["Statistics", "statistics.php"],
    "subscriptions" => ["Subscriptions", "subscriptions.php"],
    "goals" => ["Goals", "goals.php"],
    "account" => ["Account management", "account.php"],
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

<!-- The saved amount gives the user a way to update progress without recording a payment. -->
<section class="panel">
<h2 id="goal-heading">Create a savings goal</h2>
<p class="hint">Tell us what you are saving for and how much you want to save. The target date is optional.</p>
<p id="goal-error" class="notice error" role="alert" hidden></p>
<p id="goal-message" class="notice success" role="status" hidden></p>
<form id="goal-form"><fieldset id="goal-fields"><legend class="hint">Goal details</legend>
<div class="form-grid">
<label>Goal name<input name="name" maxlength="120" required placeholder="New car"></label>
<label>Target amount ($)<input name="target_amount" type="number" min="0.01" max="999999999.99" step="0.01" required></label>
<label>Amount saved ($)<input name="saved_amount" type="number" min="0" max="999999999.99" step="0.01" value="0" required></label>
<label>Target date (optional)<input name="target_date" type="date" min="1900-01-01" max="9998-12-31"></label>
</div>
<p class="hint">Update Amount saved as you make progress. It tracks what you have set aside; it does not transfer money or change your recorded income and expenses.</p>
<p><button id="goal-save" class="primary">Create goal</button> <button id="goal-cancel" class="secondary" type="button" hidden>Cancel edit</button></p>
</fieldset></form>
</section>
<!-- Completed goals stay here even after they leave the dashboard's active list. -->
<section class="panel" style="margin-top:24px">
<div class="panel-heading"><h2>Your goals</h2><button id="goal-refresh" class="secondary" type="button">Refresh</button></div>
<p id="goal-status" class="hint" role="status">Loading goals…</p>
<p id="goal-empty" class="notice info" hidden>No savings goals yet. Create your first goal above.</p>
<div id="goal-list"></div>
</section>

            </div>
            <footer class="page-footer"></footer>
        </main>
    </div>
<!-- Goal controls run after the form and progress list are ready. -->
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
// Free accounts see a sample ad. No ad network or tracking scripts are loaded.
// Refreshing membership also updates this when another tab changes the plan.
function showMembershipAd(membership) {
  let ad = document.getElementById("membership-ad");
  if (!ad) {
    ad = document.createElement("aside");
    ad.id = "membership-ad";
    ad.className = "notice info";
    ad.setAttribute("aria-label", "Advertisement");
    ad.textContent = "Sample advertisement space · Demo sponsor placement. Premium removes advertisements.";
    ad.style.cssText = "margin:20px 0;padding:24px;border:2px dashed #94a3b8;border-radius:12px;text-align:center;background:#f8fafc;color:#334155";
    document.getElementById("page-content").prepend(ad);
  }
  ad.hidden = membership.is_premium;
}
const sessionReady = api("/api/account").then((account) => {
  showMembershipAd(account.membership);
  document.getElementById("account-label").textContent = account.email;
  document.getElementById("page-content").hidden = false;
  document.getElementById("page-status").hidden = true;
  return account;
});
// Recheck on return so cancellation or expiry in another tab is reflected here.
window.addEventListener("storage", event => {
  if (event.key === "budgetbuddy-membership-change") window.dispatchEvent(new Event("focus"));
});
window.addEventListener("focus", () => {
  api("/api/account").then(account => {
    document.getElementById("account-label").textContent = account.email;
    showMembershipAd(account.membership);
    if (typeof renderMembership === "function") renderMembership(account.membership);
  }).catch(showError);
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


// A missing ID means we are creating a goal. Edit sets the ID of the selected goal.
const goalForm = document.getElementById("goal-form");
const goalNode = id => document.getElementById(id);
let editingGoal = null;
let goalBusy = false;
let goalRequest = 0;
function goalMessage(id, text) {
  goalNode(id).textContent = text;
  goalNode(id).hidden = !text;
}
function goalError(error) {
  goalMessage("goal-error", error instanceof TypeError ? "Cannot reach Python. Keep app.py running and try again." : error.message);
}
function resetGoal() {
  editingGoal = null;
  goalForm.reset();
  goalNode("goal-heading").textContent = "Create a savings goal";
  goalNode("goal-save").textContent = "Create goal";
  goalNode("goal-cancel").hidden = true;
}
goalNode("goal-cancel").onclick = () => {
  if (!goalBusy) { resetGoal(); goalMessage("goal-error",""); }
};
// Python repeats these checks, so skipping the browser's checks cannot save invalid amounts.
goalForm.addEventListener("submit", async event => {
  event.preventDefault();
  if (goalBusy || !goalForm.reportValidity()) return;
  goalMessage("goal-error","");
  goalMessage("goal-message","");
  if (!goalForm.elements.name.value.trim()) {
    goalError(new Error("Enter a goal name."));
    goalForm.elements.name.focus();
    return;
  }
  const data = new FormData(goalForm);
  const editing = editingGoal !== null;
  goalBusy = true;
  goalNode("goal-fields").disabled = true;
  try {
    await post(editing ? "/api/goals/" + editingGoal + "/edit" : "/api/goals", data);
    resetGoal();
    goalMessage("goal-message", editing ? "Goal updated." : "Goal created.");
    await loadGoals();
  } catch (error) { goalError(error); }
  finally { goalBusy = false; goalNode("goal-fields").disabled = false; }
});
function editGoal(goal) {
  if (goalBusy) return;
  editingGoal = goal.id;
  goalForm.elements.name.value = goal.name;
  goalForm.elements.target_amount.value = (goal.target_cents / 100).toFixed(2);
  goalForm.elements.saved_amount.value = (goal.saved_cents / 100).toFixed(2);
  goalForm.elements.target_date.value = goal.target_date || "";
  goalNode("goal-heading").textContent = "Edit savings goal";
  goalNode("goal-save").textContent = "Save changes";
  goalNode("goal-cancel").hidden = false;
  goalMessage("goal-error",""); goalMessage("goal-message","");
  goalForm.elements.saved_amount.focus();
}
async function removeGoal(goal) {
  if (goalBusy || !window.confirm("Delete the goal " + goal.name + "? Your income and expenses will stay saved.")) return;
  goalBusy = true; goalNode("goal-fields").disabled = true;
  goalMessage("goal-error",""); goalMessage("goal-message","");
  try {
    await post("/api/goals/" + goal.id + "/delete", new FormData());
    if (editingGoal === goal.id) resetGoal();
    goalMessage("goal-message","Goal deleted.");
    await loadGoals();
  } catch (error) { goalError(error); }
  finally { goalBusy = false; goalNode("goal-fields").disabled = false; }
}
// The bar stops at 100%, while the text still shows any amount saved above the target.
function renderGoals(goals) {
  const list = goalNode("goal-list"); list.replaceChildren();
  for (const goal of goals) {
    const done = goal.saved_cents >= goal.target_cents;
    const percent = goal.saved_cents / goal.target_cents * 100;
    const row = element("article", undefined, "data-row");
    row.append(element("h3",goal.name),element("p",money(goal.saved_cents) + " saved of " + money(goal.target_cents)));
    const bar = element("progress",undefined,"progress");
    bar.max = goal.target_cents; bar.value = Math.min(goal.saved_cents,goal.target_cents);
    bar.setAttribute("aria-label",goal.name + ": " + percent.toFixed(1) + "% saved");
    row.append(bar,element("p",(done ? "Completed" : "Active") + " · " + percent.toFixed(1) + "% saved" + (done ? "" : " · " + money(goal.target_cents-goal.saved_cents) + " left"),"hint"));
    const overdue = !done && goal.target_date && goal.target_date < todayValue();
    row.append(element("p",goal.target_date ? "Target date: " + calendarLabel(goal.target_date) + (overdue ? " · Target date has passed" : "") : "No target date set",overdue ? "hint danger" : "hint"));
    const edit = element("button","Edit / update savings","secondary");
    const remove = element("button","Delete","secondary");
    edit.type = remove.type = "button";
    edit.setAttribute("aria-label","Edit " + goal.name);
    remove.setAttribute("aria-label","Delete " + goal.name);
    edit.onclick = () => editGoal(goal); remove.onclick = () => removeGoal(goal);
    row.append(edit,document.createTextNode(" "),remove);list.append(row);
  }
  goalNode("goal-empty").hidden = goals.length > 0;
  goalMessage("goal-status",goals.length + " saved " + (goals.length === 1 ? "goal" : "goals"));
}
// Ignore late replies if a newer refresh has already started.
async function loadGoals() {
  const number = ++goalRequest;
  goalMessage("goal-status","Loading goals…");
  goalNode("goal-list").replaceChildren(); goalNode("goal-empty").hidden = true;
  try {
    await sessionReady;
    const result = await api("/api/goals");
    if (number === goalRequest) renderGoals(result.goals);
  } catch (error) {
    if (number === goalRequest) { goalError(error); goalMessage("goal-status","Goals could not be loaded. Try Refresh."); }
  }
}
goalNode("goal-refresh").onclick = () => { goalMessage("goal-error",""); loadGoals(); };
window.addEventListener("pageshow",event => { if (event.persisted) loadGoals(); });
loadGoals();

</script>
</body>
</html>

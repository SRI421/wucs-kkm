"""Dependency-free SQLite administration panel for WUCSKKM.

The module intentionally uses only Flask, Werkzeug, and Python's standard
library.  Tables and columns are discovered from SQLite at request time, so
the panel remains useful as a small database management tool without relying
on Flask-Admin, Flask-Babel, WTForms, or SQLAlchemy.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    jsonify,
    render_template_string,
    request,
    session,
    url_for,
)
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash


DEFAULT_USERNAME = "ravikumar"
DEFAULT_PASSWORD = "ravi1972"
ADMIN_BUILD = "2026-08-02-custom-sqlite-v2"
DB_PATH = os.path.join(os.path.dirname(__file__), "wucskkm.db")

PAGE_SIZES = (25, 50, 100)
TABLE_LABELS = {
    "farmers_news": "News",
    "farmers_document": "Documents",
    "farmers_board": "Notice Board",
    "farmers_crops": "Crops",
    "farmers_gallery": "Gallery",
    "farmers_society": "Society Info",
    "farmers_videos": "Videos",
    "farmers_feedback": "Feedback",
    "farmers_map_data": "Map Data",
    "farmers_years": "Years",
    "farmers_year_data": "Year Pricing",
    "farmers_data": "Farmers Data",
    "users": "User Management",
}
TABLE_ORDER = tuple(TABLE_LABELS)


INITIAL_SCHEMA = r'''
CREATE TABLE IF NOT EXISTS farmers_news (
    id INTEGER PRIMARY KEY,
    headline TEXT,
    text1 TEXT,
    text2 TEXT,
    text3 TEXT
);
CREATE TABLE IF NOT EXISTS farmers_document (
    id INTEGER PRIMARY KEY,
    data TEXT,
    link TEXT,
    title TEXT,
    filename TEXT
);
CREATE TABLE IF NOT EXISTS farmers_board (
    id INTEGER PRIMARY KEY,
    data TEXT,
    content TEXT
);
CREATE TABLE IF NOT EXISTS farmers_crops (
    id INTEGER PRIMARY KEY,
    data TEXT,
    content TEXT
);
CREATE TABLE IF NOT EXISTS farmers_gallery (
    id INTEGER PRIMARY KEY,
    data TEXT,
    content TEXT
);
CREATE TABLE IF NOT EXISTS farmers_society (
    id INTEGER PRIMARY KEY,
    data TEXT
);
CREATE TABLE IF NOT EXISTS farmers_videos (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    embed_url TEXT NOT NULL,
    added_on TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS farmers_feedback (
    id INTEGER PRIMARY KEY,
    firstname TEXT,
    lastname TEXT,
    email TEXT,
    message TEXT,
    submitted TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS farmers_map_data (
    id INTEGER PRIMARY KEY,
    mapid INTEGER,
    name TEXT,
    "pass" INTEGER,
    sno TEXT,
    area REAL
);
CREATE TABLE IF NOT EXISTS farmers_years (
    id INTEGER PRIMARY KEY,
    years TEXT
);
CREATE TABLE IF NOT EXISTS farmers_year_data (
    id INTEGER PRIMARY KEY,
    y TEXT,
    batha REAL,
    kabbu REAL,
    tota REAL,
    mtax REAL
);
CREATE TABLE IF NOT EXISTS farmers_data (
    id INTEGER PRIMARY KEY,
    "pass" INTEGER,
    sno TEXT,
    area REAL,
    batha REAL,
    bkara REAL,
    kabu REAL,
    kkara REAL,
    thota REAL,
    tkara REAL,
    wtax REAL,
    mtax REAL,
    t1 REAL,
    bal REAL,
    t2 REAL,
    name TEXT,
    first INTEGER,
    share INTEGER,
    paid REAL,
    year TEXT,
    old REAL,
    rt REAL,
    total REAL,
    balance REAL,
    "count" INTEGER,
    village TEXT,
    crop1 TEXT,
    area1 REAL,
    kara1 REAL,
    crop2 TEXT,
    area2 REAL,
    kara2 REAL,
    pp TEXT,
    phone TEXT
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_super_user INTEGER NOT NULL DEFAULT 1,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
'''


BASE_TEMPLATE = r'''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }} · WUCSKKM Database Admin</title>
  <style>
    :root {
      --nav: #123c2f; --nav2: #0c2c22; --accent: #238b63;
      --accent2: #dff5eb; --bg: #f4f7f6; --card: #fff;
      --text: #17221e; --muted: #66736e; --line: #d8e1de;
      --danger: #b42318; --warning: #9a6700;
    }
    * { box-sizing: border-box; }
    body { margin: 0; color: var(--text); background: var(--bg); font: 14px/1.45 Arial, sans-serif; }
    a { color: #176b4d; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .topbar { height: 58px; background: var(--nav2); color: #fff; display: flex; align-items: center; justify-content: space-between; padding: 0 22px; position: sticky; top: 0; z-index: 5; }
    .brand { font-weight: 700; letter-spacing: .2px; font-size: 17px; }
    .top-actions { display: flex; align-items: center; gap: 16px; }
    .top-actions a { color: #fff; }
    .layout { display: grid; grid-template-columns: 245px minmax(0, 1fr); min-height: calc(100vh - 58px); }
    .sidebar { background: var(--nav); color: #e7f5f0; padding: 18px 12px; }
    .sidebar .section { color: #a7c8bc; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: .8px; padding: 12px 12px 7px; }
    .sidebar a { color: #eaf7f2; display: block; padding: 9px 12px; border-radius: 7px; margin: 2px 0; }
    .sidebar a:hover, .sidebar a.active { background: rgba(255,255,255,.13); text-decoration: none; }
    main { padding: 24px; min-width: 0; }
    .page-head { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 18px; flex-wrap: wrap; }
    h1 { font-size: 24px; margin: 0; }
    h2 { font-size: 18px; margin: 0 0 14px; }
    .muted { color: var(--muted); }
    .card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; box-shadow: 0 2px 8px rgba(23,34,30,.04); padding: 18px; margin-bottom: 18px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; }
    .table-card { display: block; color: var(--text); }
    .table-card:hover { border-color: #94c8b4; text-decoration: none; }
    .count { font-size: 27px; font-weight: 700; color: var(--accent); margin-top: 8px; }
    .toolbar { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; }
    .btn { display: inline-block; border: 1px solid #b7c6c0; border-radius: 7px; padding: 8px 12px; background: #fff; color: var(--text); cursor: pointer; font: inherit; }
    .btn:hover { background: #f0f5f3; text-decoration: none; }
    .btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
    .btn.danger { background: #fff; border-color: #e2aaa5; color: var(--danger); }
    .btn.small { padding: 5px 8px; font-size: 12px; }
    input, select, textarea { width: 100%; border: 1px solid #b9c6c1; border-radius: 7px; padding: 9px 10px; background: #fff; color: var(--text); font: inherit; }
    textarea { min-height: 105px; resize: vertical; font-family: Consolas, monospace; }
    input:focus, select:focus, textarea:focus { outline: 2px solid #b9e2d3; border-color: var(--accent); }
    input[readonly], textarea[readonly] { background: #eef2f0; color: #5f6965; }
    .search { display: grid; grid-template-columns: minmax(180px, 1fr) 150px 90px auto; gap: 8px; margin-bottom: 14px; }
    .table-wrap { overflow: auto; border: 1px solid var(--line); border-radius: 8px; }
    table { width: 100%; border-collapse: collapse; background: #fff; }
    th, td { text-align: left; padding: 9px 10px; border-bottom: 1px solid #e5ebe8; vertical-align: top; white-space: nowrap; }
    th { background: #edf4f1; position: sticky; top: 0; z-index: 1; }
    tr:last-child td { border-bottom: 0; }
    td.preview { max-width: 270px; overflow: hidden; text-overflow: ellipsis; }
    .actions { display: flex; gap: 5px; }
    .actions form { margin: 0; }
    .pager { display: flex; justify-content: space-between; align-items: center; margin-top: 13px; gap: 10px; flex-wrap: wrap; }
    .field { margin-bottom: 15px; }
    .field label.main-label { display: block; font-weight: 700; margin-bottom: 5px; }
    .field-meta { color: var(--muted); font-size: 12px; margin: 5px 0 0; }
    .inline-check { display: inline-flex; gap: 7px; align-items: center; margin-top: 7px; }
    .inline-check input { width: auto; }
    .form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 18px; }
    .form-grid .wide { grid-column: 1 / -1; }
    .flash { padding: 11px 13px; border-radius: 7px; margin-bottom: 13px; border: 1px solid; }
    .flash.success { background: #e9f8f1; color: #11623f; border-color: #a7d9c4; }
    .flash.error { background: #fff0ef; color: #8f1d15; border-color: #efb1ac; }
    .flash.warning { background: #fff8e7; color: #7a5200; border-color: #edd28d; }
    .detail-value { white-space: pre-wrap; overflow-wrap: anywhere; font-family: Consolas, monospace; margin: 0; max-height: 430px; overflow: auto; }
    .badge { display: inline-block; padding: 2px 7px; border-radius: 10px; background: var(--accent2); color: #126044; font-size: 12px; }
    .empty { text-align: center; color: var(--muted); padding: 32px; }
    @media (max-width: 850px) {
      .layout { display: block; }
      .sidebar { position: static; display: flex; overflow-x: auto; padding: 8px; }
      .sidebar .section { display: none; }
      .sidebar a { white-space: nowrap; }
      main { padding: 15px; }
      .form-grid { display: block; }
      .search { grid-template-columns: 1fr 100px; }
      .search .grow { grid-column: 1 / -1; }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand">WUCSKKM Database Admin</div>
    <div class="top-actions">
      <span>{{ session.get('user_name', 'Administrator') }}</span>
      {% if home_endpoint %}<a href="{{ url_for(home_endpoint) }}">Application</a>{% endif %}
      {% if logout_endpoint %}<a href="{{ url_for(logout_endpoint) }}">Logout</a>{% endif %}
    </div>
  </header>
  <div class="layout">
    <nav class="sidebar">
      <div class="section">Database</div>
      <a class="{{ 'active' if not current_table else '' }}" href="{{ url_for('wucskkm_admin.index') }}">Overview</a>
      {% for item in navigation_tables %}
        <a class="{{ 'active' if current_table == item.name else '' }}" href="{{ url_for('wucskkm_admin.table_list', table_name=item.name) }}">{{ item.label }}</a>
      {% endfor %}
    </nav>
    <main>
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
          <div class="flash {{ category if category in ('success','error','warning') else 'warning' }}">{{ message }}</div>
        {% endfor %}
      {% endwith %}
      __ADMIN_BODY__
    </main>
  </div>
</body>
</html>
'''


DASHBOARD_TEMPLATE = r'''
<div class="page-head">
  <div><h1>Database overview</h1><div class="muted">Live tables in wucskkm.db</div></div>
  <span class="badge">{{ build }}</span>
</div>
<div class="grid">
  {% for item in table_counts %}
    <a class="card table-card" href="{{ url_for('wucskkm_admin.table_list', table_name=item.name) }}">
      <strong>{{ item.label }}</strong>
      <div class="muted">{{ item.name }}</div>
      <div class="count">{{ item.count }}</div>
      <div class="muted">rows · {{ item.columns }} columns</div>
    </a>
  {% endfor %}
</div>
'''


LIST_TEMPLATE = r'''
<div class="page-head">
  <div><h1>{{ table_label }}</h1><div class="muted">Table: {{ table_name }} · {{ total }} matching rows</div></div>
  <div class="toolbar">
    <a class="btn primary" href="{{ url_for('wucskkm_admin.table_create', table_name=table_name, url=current_url) }}">+ Add row</a>
  </div>
</div>
<div class="card">
  <form class="search" method="get">
    <input class="grow" name="q" value="{{ q }}" placeholder="Search all fields">
    <select name="sort">
      {% for col in columns %}<option value="{{ col.name }}" {{ 'selected' if sort == col.name else '' }}>{{ col.name }}</option>{% endfor %}
    </select>
    <select name="order"><option value="asc" {{ 'selected' if order == 'asc' else '' }}>Ascending</option><option value="desc" {{ 'selected' if order == 'desc' else '' }}>Descending</option></select>
    <select name="page_size">{% for size in page_sizes %}<option value="{{ size }}" {{ 'selected' if page_size == size else '' }}>{{ size }} rows</option>{% endfor %}</select>
    <button class="btn" type="submit">Apply</button>
    {% if q %}<a class="btn" href="{{ url_for('wucskkm_admin.table_list', table_name=table_name, page_size=page_size) }}">Clear</a>{% endif %}
  </form>
  <div class="table-wrap">
    <table>
      <thead><tr>{% for col in columns %}<th>{{ col.name }}<div class="muted">{{ col.type or 'ANY' }}</div></th>{% endfor %}<th>Actions</th></tr></thead>
      <tbody>
      {% for item in rows %}
        <tr>
          {% for value in item['values'] %}<td class="preview" title="{{ value.full }}">{{ value.preview }}</td>{% endfor %}
          <td><div class="actions">
            <a class="btn small" href="{{ url_for('wucskkm_admin.table_details', table_name=table_name, **item.locator) }}">View</a>
            <a class="btn small" href="{{ url_for('wucskkm_admin.table_edit', table_name=table_name, url=current_url, **item.locator) }}">Edit</a>
            <form method="post" action="{{ url_for('wucskkm_admin.table_delete', table_name=table_name, url=current_url, **item.locator) }}" onsubmit="return confirm('Delete this row permanently?');">
              <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
              <button class="btn small danger" type="submit">Delete</button>
            </form>
          </div></td>
        </tr>
      {% else %}<tr><td class="empty" colspan="{{ columns|length + 1 }}">No rows found.</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
  <div class="pager">
    <span>Page {{ page }} of {{ pages }}</span>
    <div class="toolbar">
      {% if page > 1 %}<a class="btn" href="{{ page_url(page - 1) }}">Previous</a>{% endif %}
      {% if page < pages %}<a class="btn" href="{{ page_url(page + 1) }}">Next</a>{% endif %}
    </div>
  </div>
</div>
'''


FORM_TEMPLATE = r'''
<div class="page-head">
  <div><h1>{{ action }} · {{ table_label }}</h1><div class="muted">Every database field is shown below.</div></div>
  <a class="btn" href="{{ return_url }}">Back</a>
</div>
{% if protected_default %}<div class="flash warning">This is the protected default Super User. Only its password can be updated.</div>{% endif %}
<form class="card" method="post">
  <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
  <input type="hidden" name="url" value="{{ return_url }}">
  <div class="form-grid">
  {% for field in fields %}
    <div class="field {{ 'wide' if field.wide else '' }}">
      <label class="main-label" for="field_{{ loop.index }}">{{ field.name }}{% if field.required %} *{% endif %}</label>
      {% if field.input_type == 'checkbox' %}
        <label class="inline-check"><input id="field_{{ loop.index }}" type="checkbox" name="{{ field.name }}" value="1" {{ 'checked' if field.checked else '' }} {{ 'disabled' if field.readonly else '' }}> Enabled / True</label>
      {% elif field.input_type == 'textarea' %}
        <textarea id="field_{{ loop.index }}" name="{{ field.name }}" {{ 'readonly' if field.readonly else '' }}>{{ field.value }}</textarea>
      {% else %}
        <input id="field_{{ loop.index }}" type="{{ field.input_type }}" name="{{ field.name }}" value="{{ field.value }}" {{ 'readonly' if field.readonly else '' }} {{ 'required' if field.required else '' }} autocomplete="{{ 'new-password' if field.input_type == 'password' else 'off' }}">
      {% endif %}
      {% if field.nullable and not field.readonly and field.input_type != 'checkbox' %}
        <label class="inline-check"><input type="checkbox" name="__null__{{ field.name }}" value="1" {{ 'checked' if field.is_null else '' }}> Store SQL NULL</label>
      {% endif %}
      <div class="field-meta">{{ field.type or 'ANY' }}{% if field.pk %} · Primary key{% endif %}{% if field.default is not none %} · Default: {{ field.default }}{% endif %}{% if field.note %} · {{ field.note }}{% endif %}</div>
    </div>
  {% endfor %}
  </div>
  <div class="toolbar"><button class="btn primary" type="submit">{{ submit_label }}</button><a class="btn" href="{{ return_url }}">Cancel</a></div>
</form>
'''


DETAIL_TEMPLATE = r'''
<div class="page-head">
  <div><h1>Row details · {{ table_label }}</h1><div class="muted">Table: {{ table_name }}</div></div>
  <div class="toolbar"><a class="btn" href="{{ url_for('wucskkm_admin.table_list', table_name=table_name) }}">Back</a><a class="btn primary" href="{{ url_for('wucskkm_admin.table_edit', table_name=table_name, **locator) }}">Edit</a></div>
</div>
<div class="card table-wrap">
  <table><tbody>
  {% for field in fields %}<tr><th>{{ field.name }}<div class="muted">{{ field.type or 'ANY' }}</div></th><td><pre class="detail-value">{{ field.value }}</pre></td></tr>{% endfor %}
  </tbody></table>
</div>
'''


def _connect(path=None):
    database_path = path or current_app.config.get("WUCSKKM_DB_PATH", DB_PATH)
    connection = sqlite3.connect(database_path, timeout=30.0, cached_statements=256)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA temp_store = MEMORY")
    return connection


def _quote_identifier(name):
    return '"' + str(name).replace('"', '""') + '"'


def _initialize_database(path):
    connection = _connect(path)
    try:
        connection.executescript(INITIAL_SCHEMA)
        _migrate_users_table(connection)
        _seed_default_user(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _migrate_users_table(connection):
    existing = {
        row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }
    additions = {
        "id": "INTEGER",
        "name": "TEXT NOT NULL DEFAULT ''",
        "email": "TEXT NOT NULL DEFAULT ''",
        "username": "TEXT NOT NULL DEFAULT ''",
        "password": "TEXT NOT NULL DEFAULT ''",
        "is_active": "INTEGER NOT NULL DEFAULT 1",
        "is_super_user": "INTEGER NOT NULL DEFAULT 1",
        "updated_at": "DATETIME",
    }
    for name, declaration in additions.items():
        if name not in existing:
            connection.execute(
                f"ALTER TABLE users ADD COLUMN {_quote_identifier(name)} {declaration}"
            )
    connection.execute("UPDATE users SET id = rowid WHERE id IS NULL")
    connection.execute(
        "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"
    )
    for statement in (
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique ON users(username)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_id_unique ON users(id)",
    ):
        try:
            connection.execute(statement)
        except sqlite3.IntegrityError:
            current = statement.split(" ON ", 1)[0].replace(
                "CREATE UNIQUE INDEX IF NOT EXISTS ", ""
            )
            print(f"Warning: could not create {current}; duplicate legacy values exist")


def _seed_default_user(connection):
    row = connection.execute(
        "SELECT id FROM users WHERE username = ? LIMIT 1", (DEFAULT_USERNAME,)
    ).fetchone()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    if row:
        connection.execute(
            "UPDATE users SET is_super_user = 1 WHERE username = ?",
            (DEFAULT_USERNAME,),
        )
        return
    connection.execute(
        """
        INSERT INTO users
            (name, email, username, password, is_active, is_super_user, updated_at)
        VALUES (?, ?, ?, ?, 1, 1, ?)
        """,
        (
            "Ravi Kumar",
            "ravikumar@wucskkm.local",
            DEFAULT_USERNAME,
            generate_password_hash(DEFAULT_PASSWORD),
            now,
        ),
    )


def _table_names(connection):
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()
    names = {row["name"] for row in rows}
    order = {name: index for index, name in enumerate(TABLE_ORDER)}
    return sorted(names, key=lambda name: (order.get(name, len(order)), name.lower()))


def _columns(connection, table_name):
    rows = connection.execute(
        f"PRAGMA table_info({_quote_identifier(table_name)})"
    ).fetchall()
    return [dict(row) for row in rows]


def _table_label(table_name):
    return TABLE_LABELS.get(table_name, table_name.replace("_", " ").title())


def _navigation(connection):
    names = _table_names(connection)
    if not session.get("is_super_user", False):
        names = [name for name in names if name != "users"]
    return [{"name": name, "label": _table_label(name)} for name in names]


def _existing_endpoint(*names):
    for name in names:
        if name in current_app.view_functions:
            return name
    return None


def _render_page(body_template, title, current_table=None, **context):
    connection = _connect()
    try:
        navigation = _navigation(connection)
    finally:
        connection.close()
    template = BASE_TEMPLATE.replace("__ADMIN_BODY__", body_template)
    return render_template_string(
        template,
        title=title,
        current_table=current_table,
        navigation_tables=navigation,
        home_endpoint=_existing_endpoint("home"),
        logout_endpoint=_existing_endpoint("logout"),
        **context,
    )


def _safe_admin_error(message, status_code, reference):
    """Render an error response without opening the database again."""
    return render_template_string(
        """
        <!doctype html><html lang="en"><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>WUCSKKM Admin</title><style>
        body{margin:0;background:#f4f7f6;color:#17221e;font:15px Arial,sans-serif}
        main{max-width:680px;margin:10vh auto;background:#fff;border:1px solid #d8e1de;
        border-radius:12px;padding:28px;box-shadow:0 4px 18px #00000012}
        h1{margin-top:0;color:#123c2f}.ref{color:#66736e;font-family:monospace}
        a{display:inline-block;margin-top:12px;color:#176b4d}
        </style></head><body><main><h1>Admin temporarily unavailable</h1>
        <p>{{ message }}</p><p class="ref">Reference: {{ reference }}</p>
        <a href="{{ request.url }}">Try again</a></main></body></html>
        """,
        message=message,
        reference=reference,
    ), status_code


def _login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in", False):
            flash("Please log in to access the admin panel.", "error")
            home = _existing_endpoint("home")
            return redirect(url_for(home) if home else "/")
        try:
            return view(*args, **kwargs)
        except HTTPException:
            raise
        except sqlite3.Error:
            reference = secrets.token_hex(4)
            current_app.logger.exception(
                "WUCSKKM admin database failure; reference=%s", reference
            )
            return _safe_admin_error(
                "The database is busy or unavailable. Please wait a moment and retry.",
                503,
                reference,
            )
        except Exception:
            reference = secrets.token_hex(4)
            current_app.logger.exception(
                "WUCSKKM admin unexpected failure; reference=%s", reference
            )
            return _safe_admin_error(
                "The request could not be completed safely. No additional operation was attempted.",
                500,
                reference,
            )

    return wrapped


def _csrf_token():
    token = session.get("wucskkm_admin_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["wucskkm_admin_csrf"] = token
    return token


def _check_csrf():
    expected = session.get("wucskkm_admin_csrf", "")
    supplied = request.form.get("csrf_token", "")
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        abort(400, description="The form expired or its security token is invalid.")


def _open_table(table_name):
    connection = _connect()
    if table_name not in _table_names(connection):
        connection.close()
        abort(404, description="Database table not found.")
    if table_name == "users" and not session.get("is_super_user", False):
        connection.close()
        abort(403, description="Super User access is required for User Management.")
    columns = _columns(connection, table_name)
    if not columns:
        connection.close()
        abort(404, description="Database table has no columns.")
    return connection, columns


def _primary_columns(columns):
    return sorted((column for column in columns if column["pk"]), key=lambda c: c["pk"])


def _json_value(value):
    if isinstance(value, bytes):
        return {"__bytes__": base64.b64encode(value).decode("ascii")}
    return value


def _from_json_value(value):
    if isinstance(value, dict) and set(value) == {"__bytes__"}:
        return base64.b64decode(value["__bytes__"], validate=True)
    return value


def _encode_key(values):
    raw = json.dumps(values, default=_json_value, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_key(token):
    try:
        padding = "=" * (-len(token) % 4)
        values = json.loads(base64.urlsafe_b64decode(token + padding).decode("utf-8"))
        return {name: _from_json_value(value) for name, value in values.items()}
    except (ValueError, TypeError, json.JSONDecodeError):
        abort(400, description="Invalid row identifier.")


def _locator_for_row(columns, row):
    primary = _primary_columns(columns)
    if len(primary) == 1 and primary[0]["name"] == "id":
        return {"id": row["id"]}
    if primary:
        values = {column["name"]: row[column["name"]] for column in primary}
        return {"key": _encode_key(values)}
    return {"rowid": row["__admin_rowid__"]}


def _row_where(columns):
    primary = _primary_columns(columns)
    if len(primary) == 1 and primary[0]["name"] == "id" and request.args.get("id") is not None:
        return f'{_quote_identifier("id")} = ?', [request.args["id"]]
    if primary and request.args.get("key"):
        values = _decode_key(request.args["key"])
        expected = [column["name"] for column in primary]
        if set(values) != set(expected):
            abort(400, description="Row identifier does not match the table key.")
        return " AND ".join(
            f"{_quote_identifier(name)} IS ?" for name in expected
        ), [values[name] for name in expected]
    if not primary and request.args.get("rowid") is not None:
        return "rowid = ?", [request.args["rowid"]]
    abort(400, description="A row identifier is required.")


def _fetch_row(connection, table_name, columns):
    where_sql, parameters = _row_where(columns)
    prefix = "rowid AS __admin_rowid__, " if not _primary_columns(columns) else ""
    row = connection.execute(
        f"SELECT {prefix}* FROM {_quote_identifier(table_name)} WHERE {where_sql} LIMIT 1",
        parameters,
    ).fetchone()
    if row is None:
        abort(404, description="The selected row no longer exists.")
    return row, where_sql, parameters


def _display_value(table_name, column_name, value, maximum=80):
    if table_name == "users" and column_name == "password":
        return "[protected password hash]", "[protected password hash]"
    if value is None:
        return "NULL", "NULL"
    if isinstance(value, bytes):
        full = f"BLOB ({len(value)} bytes)"
        return full, full
    full = str(value)
    preview = full if len(full) <= maximum else full[: maximum - 1] + "…"
    return preview, full


def _detail_value(table_name, column_name, value):
    if table_name == "users" and column_name == "password":
        return "[protected password hash]"
    if value is None:
        return "NULL"
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    return str(value)


def _column_kind(column, table_name):
    name = column["name"]
    declared = (column["type"] or "").upper()
    if table_name == "users" and name == "password":
        return "password"
    if name in ("is_active", "is_super_user") or "BOOL" in declared:
        return "checkbox"
    if "BLOB" in declared or "TEXT" in declared or name in (
        "data", "content", "message", "text1", "text2", "text3"
    ):
        return "textarea"
    if any(token in declared for token in ("INT", "REAL", "FLOA", "DOUB", "NUM", "DEC")):
        return "number"
    return "text"


def _form_value(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    return str(value)


def _form_fields(table_name, columns, row=None, creating=False):
    protected_default = bool(
        table_name == "users" and row is not None and row["username"] == DEFAULT_USERNAME
    )
    fields = []
    for column in columns:
        name = column["name"]
        value = None if row is None else row[name]
        kind = _column_kind(column, table_name)
        readonly = bool(row is not None and column["pk"])
        note = ""
        if table_name == "users":
            if name == "password":
                value = ""
                note = "Required when creating; leave blank on other-user edits to keep the password"
            if name == "updated_at":
                readonly = True
                note = "Updated automatically"
            if protected_default and name != "password":
                readonly = True
            if creating and name in ("is_active", "is_super_user"):
                value = 1
        if creating and column["pk"] and "INT" in (column["type"] or "").upper():
            note = "Optional; blank uses the next automatic ID"
        required = bool(
            table_name == "users"
            and creating
            and name in ("name", "email", "username", "password")
        )
        fields.append(
            {
                "name": name,
                "type": column["type"],
                "pk": bool(column["pk"]),
                "default": column["dflt_value"],
                "required": required,
                "readonly": readonly,
                "nullable": not bool(column["notnull"]) and not bool(column["pk"]),
                "is_null": row is not None and value is None,
                "input_type": kind,
                "checked": bool(value),
                "value": _form_value(value),
                "wide": kind == "textarea",
                "note": note,
            }
        )
    return fields, protected_default


_OMIT = object()


def _coerce_value(column, creating=False):
    name = column["name"]
    declared = (column["type"] or "").upper()
    is_boolean = name in ("is_active", "is_super_user") or "BOOL" in declared
    if is_boolean:
        return 1 if request.form.get(name) else 0
    if request.form.get(f"__null__{name}"):
        if column["notnull"] or column["pk"]:
            raise ValueError(f"{name} cannot be NULL")
        return None
    raw = request.form.get(name, "")
    if creating and raw == "" and column["pk"] and "INT" in declared:
        return _OMIT
    if creating and raw == "" and column["dflt_value"] is not None:
        return _OMIT
    if "BLOB" in declared:
        try:
            return base64.b64decode(raw, validate=True) if raw else b""
        except ValueError as exc:
            raise ValueError(f"{name} must contain valid Base64 for a BLOB") from exc
    if "INT" in declared:
        if raw == "" and not column["notnull"]:
            return None
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError(f"{name} must be a whole number") from exc
    if any(token in declared for token in ("REAL", "FLOA", "DOUB", "NUM", "DEC")):
        if raw == "" and not column["notnull"]:
            return None
        try:
            return float(raw)
        except ValueError as exc:
            raise ValueError(f"{name} must be a number") from exc
    return raw


def _safe_return_url(default_url):
    candidate = request.form.get("url") or request.args.get("url") or ""
    script_root = request.script_root.rstrip("/")
    allowed_prefixes = ("/admin/", f"{script_root}/admin/")
    if candidate.startswith(allowed_prefixes) and not candidate.startswith("//"):
        return candidate
    return default_url


admin_blueprint = Blueprint("wucskkm_admin", __name__, url_prefix="/admin")


@admin_blueprint.route("/health/")
def health():
    """Public, data-free deployment and SQLite availability check."""
    connection = None
    try:
        connection = _connect()
        connection.execute("SELECT 1").fetchone()
        users_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone() is not None
        return jsonify(
            status="ok",
            build=ADMIN_BUILD,
            database="sqlite",
            users_table=users_table,
        )
    except sqlite3.Error:
        reference = secrets.token_hex(4)
        current_app.logger.exception(
            "WUCSKKM admin health-check failure; reference=%s", reference
        )
        return jsonify(
            status="unavailable",
            build=ADMIN_BUILD,
            reference=reference,
        ), 503
    finally:
        if connection is not None:
            connection.close()


@admin_blueprint.route("/")
@_login_required
def index():
    connection = _connect()
    try:
        navigation = _navigation(connection)
        table_counts = []
        for item in navigation:
            name = item["name"]
            count = connection.execute(
                f"SELECT COUNT(*) AS total FROM {_quote_identifier(name)}"
            ).fetchone()["total"]
            table_counts.append(
                {
                    **item,
                    "count": count,
                    "columns": len(_columns(connection, name)),
                }
            )
    finally:
        connection.close()
    return _render_page(
        DASHBOARD_TEMPLATE,
        "Database overview",
        table_counts=table_counts,
        build=ADMIN_BUILD,
    )


@admin_blueprint.route("/<table_name>/")
@_login_required
def table_list(table_name):
    connection, columns = _open_table(table_name)
    try:
        try:
            page = max(1, int(request.args.get("page", 1)))
        except ValueError:
            page = 1
        try:
            requested_size = int(request.args.get("page_size", 50))
        except ValueError:
            requested_size = 50
        page_size = requested_size if requested_size in PAGE_SIZES else 50
        q = request.args.get("q", "").strip()
        column_names = [column["name"] for column in columns]
        sort = request.args.get("sort", "")
        if sort not in column_names:
            primary = _primary_columns(columns)
            sort = primary[0]["name"] if primary else column_names[0]
        order = "desc" if request.args.get("order", "asc").lower() == "desc" else "asc"
        where_sql = ""
        parameters = []
        if q:
            where_sql = " WHERE " + " OR ".join(
                f"CAST({_quote_identifier(name)} AS TEXT) LIKE ?" for name in column_names
            )
            parameters = [f"%{q}%"] * len(column_names)
        total = connection.execute(
            f"SELECT COUNT(*) AS total FROM {_quote_identifier(table_name)}{where_sql}",
            parameters,
        ).fetchone()["total"]
        pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, pages)
        offset = (page - 1) * page_size
        prefix = "rowid AS __admin_rowid__, " if not _primary_columns(columns) else ""
        rows = connection.execute(
            f"SELECT {prefix}* FROM {_quote_identifier(table_name)}{where_sql} "
            f"ORDER BY {_quote_identifier(sort)} {order.upper()} LIMIT ? OFFSET ?",
            [*parameters, page_size, offset],
        ).fetchall()
        prepared_rows = []
        for row in rows:
            values = []
            for column in columns:
                preview, full = _display_value(table_name, column["name"], row[column["name"]])
                values.append({"preview": preview, "full": full})
            prepared_rows.append({"values": values, "locator": _locator_for_row(columns, row)})

        def page_url(page_number):
            return url_for(
                "wucskkm_admin.table_list",
                table_name=table_name,
                page=page_number,
                page_size=page_size,
                q=q,
                sort=sort,
                order=order,
            )

        column_views = [dict(column) for column in columns]
    finally:
        connection.close()
    return _render_page(
        LIST_TEMPLATE,
        _table_label(table_name),
        current_table=table_name,
        table_name=table_name,
        table_label=_table_label(table_name),
        columns=column_views,
        rows=prepared_rows,
        total=total,
        page=page,
        pages=pages,
        page_size=page_size,
        page_sizes=PAGE_SIZES,
        q=q,
        sort=sort,
        order=order,
        csrf_token=_csrf_token(),
        current_url=request.full_path.rstrip("?"),
        page_url=page_url,
    )


@admin_blueprint.route("/<table_name>/new/", methods=("GET", "POST"))
@_login_required
def table_create(table_name):
    connection, columns = _open_table(table_name)
    default_url = url_for("wucskkm_admin.table_list", table_name=table_name)
    return_url = _safe_return_url(default_url)
    try:
        if request.method == "POST":
            _check_csrf()
            values = {}
            for column in columns:
                value = _coerce_value(column, creating=True)
                if value is not _OMIT:
                    values[column["name"]] = value
            if table_name == "users":
                for required in ("name", "email", "username", "password"):
                    if not str(request.form.get(required, "")).strip():
                        raise ValueError(f"{required} is required")
                values["name"] = request.form["name"].strip()
                values["email"] = request.form["email"].strip()
                values["username"] = request.form["username"].strip()
                values["password"] = generate_password_hash(request.form["password"])
                values["is_active"] = 1 if request.form.get("is_active") else 0
                values["is_super_user"] = 1 if request.form.get("is_super_user") else 0
                values["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            if values:
                names = list(values)
                placeholders = ", ".join("?" for _ in names)
                connection.execute(
                    f"INSERT INTO {_quote_identifier(table_name)} "
                    f"({', '.join(_quote_identifier(name) for name in names)}) "
                    f"VALUES ({placeholders})",
                    [values[name] for name in names],
                )
            else:
                connection.execute(f"INSERT INTO {_quote_identifier(table_name)} DEFAULT VALUES")
            connection.commit()
            flash(f"A row was created in {_table_label(table_name)}.", "success")
            return redirect(return_url)
    except (sqlite3.IntegrityError, sqlite3.OperationalError, ValueError) as exc:
        connection.rollback()
        flash(f"The row was not created: {exc}", "error")
    finally:
        connection.close()
    fields, protected_default = _form_fields(table_name, columns, creating=True)
    return _render_page(
        FORM_TEMPLATE,
        f"Add · {_table_label(table_name)}",
        current_table=table_name,
        table_label=_table_label(table_name),
        action="Add row",
        submit_label="Create row",
        fields=fields,
        protected_default=protected_default,
        csrf_token=_csrf_token(),
        return_url=return_url,
    )


@admin_blueprint.route("/<table_name>/edit/", methods=("GET", "POST"))
@_login_required
def table_edit(table_name):
    connection, columns = _open_table(table_name)
    default_url = url_for("wucskkm_admin.table_list", table_name=table_name)
    return_url = _safe_return_url(default_url)
    row, where_sql, where_parameters = _fetch_row(connection, table_name, columns)
    protected_default = bool(
        table_name == "users" and row["username"] == DEFAULT_USERNAME
    )
    try:
        if request.method == "POST":
            _check_csrf()
            if protected_default:
                password = request.form.get("password", "")
                if not password:
                    raise ValueError("Enter a new password for the default Super User")
                connection.execute(
                    f"UPDATE users SET password = ?, updated_at = ? WHERE {where_sql}",
                    (
                        generate_password_hash(password),
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                        *where_parameters,
                    ),
                )
            else:
                values = {}
                for column in columns:
                    if column["pk"]:
                        continue
                    name = column["name"]
                    if table_name == "users" and name == "updated_at":
                        continue
                    if table_name == "users" and name == "password":
                        password = request.form.get("password", "")
                        if password:
                            values[name] = generate_password_hash(password)
                        continue
                    values[name] = _coerce_value(column, creating=False)
                if table_name == "users":
                    for required in ("name", "email", "username"):
                        if not str(values.get(required, "")).strip():
                            raise ValueError(f"{required} is required")
                        values[required] = str(values[required]).strip()
                    values["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                assignments = ", ".join(
                    f"{_quote_identifier(name)} = ?" for name in values
                )
                if assignments:
                    connection.execute(
                        f"UPDATE {_quote_identifier(table_name)} SET {assignments} WHERE {where_sql}",
                        [*values.values(), *where_parameters],
                    )
            connection.commit()
            flash(f"The {_table_label(table_name)} row was updated.", "success")
            return redirect(return_url)
    except (sqlite3.IntegrityError, sqlite3.OperationalError, ValueError) as exc:
        connection.rollback()
        flash(f"The row was not updated: {exc}", "error")
    finally:
        connection.close()
    fields, protected_default = _form_fields(table_name, columns, row=row)
    return _render_page(
        FORM_TEMPLATE,
        f"Edit · {_table_label(table_name)}",
        current_table=table_name,
        table_label=_table_label(table_name),
        action="Edit row",
        submit_label="Save changes",
        fields=fields,
        protected_default=protected_default,
        csrf_token=_csrf_token(),
        return_url=return_url,
    )


@admin_blueprint.route("/<table_name>/details/")
@_login_required
def table_details(table_name):
    connection, columns = _open_table(table_name)
    try:
        row, _where_sql, _where_parameters = _fetch_row(connection, table_name, columns)
        fields = [
            {
                "name": column["name"],
                "type": column["type"],
                "value": _detail_value(table_name, column["name"], row[column["name"]]),
            }
            for column in columns
        ]
        locator = _locator_for_row(columns, row)
    finally:
        connection.close()
    return _render_page(
        DETAIL_TEMPLATE,
        f"Details · {_table_label(table_name)}",
        current_table=table_name,
        table_name=table_name,
        table_label=_table_label(table_name),
        fields=fields,
        locator=locator,
    )


@admin_blueprint.route("/<table_name>/delete/", methods=("POST",))
@_login_required
def table_delete(table_name):
    connection, columns = _open_table(table_name)
    default_url = url_for("wucskkm_admin.table_list", table_name=table_name)
    return_url = _safe_return_url(default_url)
    try:
        _check_csrf()
        row, where_sql, where_parameters = _fetch_row(connection, table_name, columns)
        if table_name == "users" and row["username"] == DEFAULT_USERNAME:
            flash("The default Super User cannot be deleted.", "error")
            return redirect(return_url)
        deleting_current_user = bool(
            table_name == "users" and row["id"] == session.get("user_id")
        )
        connection.execute(
            f"DELETE FROM {_quote_identifier(table_name)} WHERE {where_sql}",
            where_parameters,
        )
        connection.commit()
        flash(f"The {_table_label(table_name)} row was deleted.", "success")
        if deleting_current_user:
            session.clear()
            home = _existing_endpoint("home")
            return redirect(url_for(home) if home else "/")
        return redirect(return_url)
    except (sqlite3.IntegrityError, sqlite3.OperationalError) as exc:
        connection.rollback()
        flash(f"The row was not deleted: {exc}", "error")
        return redirect(return_url)
    finally:
        connection.close()


def init_admin(app):
    """Create the database when needed and register the custom admin routes."""
    database_path = app.config.get("WUCSKKM_DB_PATH", DB_PATH)
    os.makedirs(os.path.dirname(os.path.abspath(database_path)), exist_ok=True)
    _initialize_database(database_path)
    app.config["WUCSKKM_ADMIN_BUILD"] = ADMIN_BUILD
    app.register_blueprint(admin_blueprint)

    @app.after_request
    def add_wucskkm_admin_build_header(response):
        response.headers.setdefault("X-WUCSKKM-Admin-Build", ADMIN_BUILD)
        return response

    # Preserve the endpoint used by secured.html: url_for('users.index_view').
    users_compatibility = Blueprint("users", __name__, url_prefix="/admin/users")

    @users_compatibility.route("/", endpoint="index_view")
    @_login_required
    def users_index_view():
        return table_list("users")

    app.register_blueprint(users_compatibility)
    print(f"WUCSKKM dependency-free admin build {ADMIN_BUILD} loaded")
    return admin_blueprint


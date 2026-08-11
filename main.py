import os
import sqlite3
from flask import Flask, flash, g, redirect, render_template, request, session, url_for, jsonify
import base64
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from contextlib import contextmanager
from itertools import groupby
from admin import init_admin
from flask import send_file
from datetime import datetime
app = Flask(__name__, static_folder='./static', template_folder='./templates')

admin = init_admin(app)
# SQLite database configuration
DB_PATH = os.path.join(os.path.dirname(__file__), 'wucskkm.db')


def fix_base64_image(data_str):
    """
    Fix base64 image data to ensure proper display
    Handles various formats of stored image data
    """
    if not data_str:
        return None

    # If already has data URI prefix, return as is
    if data_str.startswith('data:image/'):
        return data_str

    # Try to decode if it's double-encoded
    try:
        # First check if it's already base64
        if not data_str.startswith('data:'):
            # Try to decode to see if it's valid base64
            import base64
            decoded = base64.b64decode(data_str)
            # If successful, it's valid base64, add prefix
            return f"data:image/jpeg;base64,{data_str}"
    except:
        pass

    return data_str


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30.0,
        cached_statements=256,
    )
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA temp_store = MEMORY")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dict_from_row(row):
    """Convert sqlite3.Row to dictionary"""
    return {k: row[k] for k in row.keys()} if row else None


_QUERY_INDEXES = (
    (
        'farmers_data',
        'CREATE INDEX IF NOT EXISTS idx_farmers_data_year_pass_id '
        'ON farmers_data(year, pass, id)'
    ),
    (
        'farmers_data',
        'CREATE INDEX IF NOT EXISTS idx_farmers_data_year_first_pass_id '
        'ON farmers_data(year, first, pass, id)'
    ),
    (
        'farmers_data',
        'CREATE INDEX IF NOT EXISTS idx_farmers_data_pass_id '
        'ON farmers_data(pass, id)'
    ),
    (
        'farmers_map_data',
        'CREATE INDEX IF NOT EXISTS idx_farmers_map_data_mapid_id '
        'ON farmers_map_data(mapid, id)'
    ),
    (
        'farmers_map_data',
        'CREATE INDEX IF NOT EXISTS idx_farmers_map_data_pass_id '
        'ON farmers_map_data(pass, id)'
    ),
    (
        'farmers_year_data',
        'CREATE INDEX IF NOT EXISTS idx_farmers_year_data_y '
        'ON farmers_year_data(y)'
    ),
    (
        'farmers_years',
        'CREATE INDEX IF NOT EXISTS idx_farmers_years_years '
        'ON farmers_years(years)'
    ),
)


def ensure_query_indexes():
    """Create only the indexes used by frequent filters, joins, and ordering."""
    with sqlite3.connect(DB_PATH, timeout=30.0) as conn:
        existing_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for table_name, statement in _QUERY_INDEXES:
            if table_name in existing_tables:
                conn.execute(statement)


ensure_query_indexes()


def latest_financial_years(cursor, limit=1):
    """Return latest financial-year labels such as 2024-2025, newest first."""
    cursor.execute(
        """
        SELECT years AS year_label
        FROM farmers_years
        WHERE years IS NOT NULL AND TRIM(years) != ''
        GROUP BY years
        ORDER BY CAST(SUBSTR(years, 1, 4) AS INTEGER) DESC, id DESC
        LIMIT ?
        """,
        (limit,)
    )
    years = [row['year_label'] for row in cursor.fetchall()]
    if years:
        return years

    cursor.execute(
        """
        SELECT year AS year_label
        FROM farmers_data
        WHERE year IS NOT NULL AND TRIM(year) != ''
        GROUP BY year
        ORDER BY CAST(SUBSTR(year, 1, 4) AS INTEGER) DESC
        LIMIT ?
        """,
        (limit,)
    )
    return [row['year_label'] for row in cursor.fetchall()]


def latest_farmer_data_years(cursor, limit=1):
    """Return newest years that actually contain farmer data rows."""
    cursor.execute(
        """
        SELECT TRIM(year) AS year_label
        FROM farmers_data
        WHERE year IS NOT NULL
          AND TRIM(year) != ''
        GROUP BY TRIM(year)
        ORDER BY CAST(SUBSTR(TRIM(year), 1, 4) AS INTEGER) DESC,
                 TRIM(year) DESC
        LIMIT ?
        """,
        (limit,)
    )
    return [row['year_label'] for row in cursor.fetchall()]

def current_user_record():
    """Return and request-cache the active user without exposing the password."""
    if hasattr(g, 'current_user'):
        return g.current_user

    user_id = session.get('user_id')
    if not user_id:
        g.current_user = None
        return None

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, name, email, username, is_active, is_super_user, updated_at
            FROM users
            WHERE id = ? AND is_active = 1
            """,
            (user_id,)
        ).fetchone()

    g.current_user = dict_from_row(row)
    return g.current_user


@app.before_request
def refresh_logged_in_user():
    """Keep authorization in sync with the users table on every request."""
    if not session.get('logged_in'):
        return

    user = current_user_record()
    if not user:
        session.clear()
        return

    session['is_super_user'] = bool(user['is_super_user'])
    session['user_name'] = user['name']


ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app.config['SECRET_KEY'] = '9OLWxND4o83j4K4iuopO'
godpass = []


def newsreturn():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT headline, text1, text2, text3 FROM farmers_news WHERE id=1")
        row = cursor.fetchone()
        return tuple(row) if row else (None, None, None, None)


@app.route('/home')
def temp():
    return redirect(url_for('home'))


@app.route('/')
def home():
    session['delpass'] = 0
    myresult = newsreturn()
    hello, text1, text2, text3 = myresult

    user = current_user_record() if session.get('logged_in') else None
    template = 'secured.html' if user else 'index.html'
    return render_template(
        template,
        hello=hello,
        text1=text1,
        text2=text2,
        text3=text3,
        current_user=user,
    )


@app.route('/login', methods=['POST'])
def do_admin_login():
    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''

    with get_db() as conn:
        user = conn.execute(
            """
            SELECT id, name, password, is_active, is_super_user
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

    if user and user['is_active'] and check_password_hash(user['password'], password):
        session.clear()
        session['logged_in'] = True
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['is_super_user'] = bool(user['is_super_user'])
    else:
        flash('Invalid username or password.', 'error')
    return redirect(url_for('home'))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))


def li():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT years FROM farmers_years ORDER BY id DESC LIMIT 1")
        last_year = cursor.fetchone()

        if last_year:
            cursor.execute(
                "SELECT pass, name FROM farmers_data WHERE first=1 AND year=?",
                (last_year['years'],)
            )
            return [dict_from_row(row) for row in cursor.fetchall()]
        return []


@app.route("/list", methods=['GET', 'POST'])
def list1():
    sup = 3 if session.get('logged_in') else None
    data = li()
    return render_template('list.html', data=data, sup=sup)


@app.route("/wucscalc", methods=['GET', 'POST'])
def wucscalc():
    if session.get('logged_in'):
        return render_template('calc.html')
    return redirect(url_for('home'))


@app.route("/news", methods=['GET', 'POST'])
def news():
    if not session.get('logged_in'):
        return redirect(url_for('home'))

    if request.values.get("submit"):
        with get_db() as conn:
            cursor = conn.cursor()
            sql = "UPDATE farmers_news SET headline=?, text1=?, text2=?, text3=? WHERE id=1"
            cursor.execute(sql, (
                request.values.get("headline"),
                request.values.get("text1"),
                request.values.get("text2"),
                request.values.get("text3")
            ))

    myresult = newsreturn()
    data, text1, text2, text3 = myresult
    return render_template('news.html', data=data, text1=text1, text2=text2, text3=text3)


@app.route('/docinsert', methods=['GET', 'POST'])
def docinsert():
    """
    Insert a new document into the database
    - No file system storage required
    - Works purely with base64 encoding
    - HelioHost compatible
    """
    if not session.get('logged_in'):
        return redirect(url_for('document'))

    try:
        # Check if file is present in request
        if not request.files.get('file'):
            return redirect(url_for('document'))

        file = request.files['file']

        # Check if file has a filename
        if file.filename == '':
            return redirect(url_for('document'))

        # Validate file extension
        if not allowed_file(file.filename):
            return redirect(url_for('document'))

        # Secure the filename
        filename = secure_filename(file.filename)

        # Read file content and encode to base64
        file_content = file.read()

        # Encode to base64
        blob = base64.b64encode(file_content).decode('utf-8')

        # Get document title (use filename if not provided)
        title = request.values.get("n", "").strip() or filename

        # Insert into database
        with get_db() as conn:
            cursor = conn.cursor()
            sql = "INSERT INTO farmers_document (data, title, filename) VALUES (?, ?, ?)"
            cursor.execute(sql, (blob, title, filename))
            conn.commit()

    except Exception as e:
        # Log error for debugging (you can use proper logging in production)
        print(f"Error in docinsert: {str(e)}")

    return redirect(url_for('document'))


def getdoc():
    """
    Retrieve all documents from database
    - Returns base64-encoded document data
    - No file system access required
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, data, title, filename FROM farmers_document ORDER BY id DESC")
            rows = []

            for row in cursor.fetchall():
                try:
                    k = dict_from_row(row)
                    # Prepare base64 data URL for PDF embedding
                    data_url = f"data:application/pdf;base64,{k['data']}"

                    rows.append({
                        'id': k['id'],
                        'data': data_url,
                        'title': k['title'],
                        'filename': k['filename']
                    })
                except Exception as e:
                    print(f"Error processing row {row.get('id', 'unknown')}: {str(e)}")
                    continue

            # Create slide numbers
            slide_numbers = list(range(1, len(rows) + 1))
            return rows, slide_numbers

    except Exception as e:
        print(f"Error in getdoc: {str(e)}")
        return [], []


@app.route('/document', methods=['GET', 'POST'])
def document():
    """
    Display document page
    - Shows all documents from database
    - Admin controls visible when logged in
    """
    try:
        sup = 3 if session.get('logged_in') else None
        data, data1 = getdoc()

        # Assign slide numbers to each document
        for i in range(len(data)):
            if i < len(data1):
                data[i]['slide'] = data1[i]

        return render_template('document.html', data=data, sup=sup)

    except Exception as e:
        print(f"Error in document route: {str(e)}")
        return render_template('document.html', data=[], sup=None)


@app.route('/docupdate', methods=['GET', 'POST'])
def docupdate():
    """
    Update or delete documents
    - Update: Change document title
    - Delete: Remove document from database
    """
    if not session.get('logged_in'):
        return redirect(url_for('document'))

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM farmers_document")
            myresult = cursor.fetchall()

            for row in myresult:
                doc_id = row['id']
                title = row['title']
                update_id = f"update{doc_id}"
                delete_id = f"delete{doc_id}"

                # Check for update action
                if request.values.get(update_id):
                    new_title = request.values.get(f"n{doc_id}", "").strip()

                    if new_title and new_title != title:
                        sql = "UPDATE farmers_document SET title=? WHERE id=?"
                        cursor.execute(sql, (new_title, doc_id))
                        conn.commit()
                        break

                # Check for delete action
                elif request.values.get(delete_id):
                    sql = "DELETE FROM farmers_document WHERE id=?"
                    cursor.execute(sql, (doc_id,))
                    conn.commit()
                    break

    except Exception as e:
        print(f"Error in docupdate: {str(e)}")

    return redirect(url_for('document'))


# Optional: Add a route to download documents
@app.route('/docdownload/<int:doc_id>')
def docdownload(doc_id):
    """
    Download a document
    - Retrieves base64 data and sends as file
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data, filename FROM farmers_document WHERE id=?", (doc_id,))
            row = cursor.fetchone()

            if row:
                k = dict_from_row(row)
                # Decode base64 to binary
                file_data = base64.b64decode(k['data'])
                filename = k['filename']

                # Create response with file
                from flask import Response
                response = Response(file_data)
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'attachment; filename={filename}'
                return response
            else:
                return redirect(url_for('document'))

    except Exception as e:
        print(f"Error in docdownload: {str(e)}")
        return redirect(url_for('document'))


def youtube_url_to_embed(url):
    """
    Convert any YouTube URL format to an embed URL.
    Handles:
      https://www.youtube.com/watch?v=VIDEO_ID
      https://youtu.be/VIDEO_ID
      https://www.youtube.com/embed/VIDEO_ID  (already embed)
    """
    import re
    if not url:
        return None
    url = url.strip()
    # Already embed
    if 'youtube.com/embed/' in url:
        return url
    # youtu.be short link
    m = re.search(r'youtu\.be/([A-Za-z0-9_\-]+)', url)
    if m:
        return f"https://www.youtube.com/embed/{m.group(1)}"
    # Standard watch URL
    m = re.search(r'[?&]v=([A-Za-z0-9_\-]+)', url)
    if m:
        return f"https://www.youtube.com/embed/{m.group(1)}"
    return None


def init_videos_table():
    """Create farmers_videos table if it does not exist."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS farmers_videos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                url       TEXT NOT NULL,
                embed_url TEXT NOT NULL,
                added_on  TEXT DEFAULT (datetime('now','localtime'))
            )
        """)


@app.route('/videos', methods=['GET'])
def videos():
    """GET – show all saved videos (+ hardcoded fallback if DB empty)."""
    init_videos_table()
    sup = 3 if session.get('logged_in') else None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, url, embed_url FROM farmers_videos ORDER BY id DESC")
        data = [dict_from_row(r) for r in cursor.fetchall()]
    return render_template('videos.html', data=data, sup=sup)


@app.route('/videoinsert', methods=['POST'])
def videoinsert():
    """POST – add a new YouTube video URL (login required)."""
    if not session.get('logged_in'):
        return redirect(url_for('videos'))
    init_videos_table()
    raw_url = (request.form.get('url') or '').strip()
    embed_url = youtube_url_to_embed(raw_url)
    if raw_url and embed_url:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO farmers_videos (url, embed_url) VALUES (?, ?)",
                (raw_url, embed_url)
            )
    return redirect(url_for('videos'))


@app.route('/videodelete/<int:video_id>', methods=['POST'])
def videodelete(video_id):
    """POST – delete a video by id (login required)."""
    if not session.get('logged_in'):
        return redirect(url_for('videos'))
    init_videos_table()
    with get_db() as conn:
        conn.execute("DELETE FROM farmers_videos WHERE id=?", (video_id,))
    return redirect(url_for('videos'))


@app.route('/google256f32c4755af706.html', methods=['GET', 'POST'])
def googleseo():
    return render_template('google256f32c4755af706.html')


@app.route('/boardinsert', methods=['GET', 'POST'])
def boardinsert():
    if request.values.get("file"):
        with get_db() as conn:
            cursor = conn.cursor()
            sql = "INSERT INTO farmers_board (data, content) VALUES (?, ?)"
            cursor.execute(sql, (
                request.values.get("img1"),
                request.values.get("n") or " "
            ))

    return redirect(url_for('board'))


def getboard():
    """Fixed version with proper blob handling including -- prefix cleanup"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, data, content FROM farmers_board")
        rows = []

        for row in cursor.fetchall():
            k = dict_from_row(row)
            data_value = k['data']

            # Handle different data formats
            if data_value:
                # Check if it's already a data URI
                if data_value.startswith('data:image/'):
                    data = data_value
                # Check if it starts with base64 marker
                elif data_value.startswith('data:'):
                    data = data_value
                else:
                    # Clean up base64 data
                    clean_data = data_value

                    # Remove -- prefix if present (common encoding artifact)
                    if clean_data.startswith('--'):
                        clean_data = clean_data[2:]

                    # Remove any whitespace
                    clean_data = clean_data.strip()

                    # Try to validate it's valid base64
                    try:
                        # Test decode to ensure it's valid base64
                        base64.b64decode(clean_data)
                        # If successful, add the data URI prefix
                        data = f"data:image/jpeg;base64,{clean_data}"
                    except:
                        # If decode fails, try as-is
                        data = f"data:image/jpeg;base64,{data_value}"
            else:
                data = None

            rows.append({'id': k['id'], 'data': data, 'content': k['content']})

        return rows, list(range(1, len(rows) + 1))


@app.route('/board', methods=['GET', 'POST'])
def board():
    sup = 3 if session.get('logged_in') else None
    data, data1 = getboard()

    for i in range(len(data1)):
        data[i]['slide'] = data1[i]
    return render_template('noticeboard.html', data=data, sup=sup, hello="-")


@app.route('/boardupdate', methods=['GET', 'POST'])
def boardupdate():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, content FROM farmers_board")
        myresult = cursor.fetchall()

        for row in myresult:
            doc_id, content = row['id'], row['content']
            update_id = f"update{doc_id}"
            delete_id = f"delete{doc_id}"

            if request.values.get(update_id):
                blob = request.values.get(f"img2{doc_id}")
                n = request.values.get(f"n{doc_id}")

                if blob and n and n != content:
                    sql = "UPDATE farmers_board SET data=?, content=? WHERE id=?"
                    cursor.execute(sql, (blob, n, doc_id))
                elif blob:
                    sql = "UPDATE farmers_board SET data=? WHERE id=?"
                    cursor.execute(sql, (blob, doc_id))
                elif n and n != content:
                    sql = "UPDATE farmers_board SET content=? WHERE id=?"
                    cursor.execute(sql, (n, doc_id))
                else:
                    break
                break
            elif request.values.get(delete_id):
                sql = "DELETE FROM farmers_board WHERE id=?"
                cursor.execute(sql, (doc_id,))
                break

    return redirect(url_for('board'))


@app.route('/cropinsert', methods=['GET', 'POST'])
def cropinsert():
    if request.values.get("file"):
        with get_db() as conn:
            cursor = conn.cursor()
            sql = "INSERT INTO farmers_crops (data, content) VALUES (?, ?)"
            cursor.execute(sql, (
                request.values.get("img1"),
                request.values.get("n") or " "
            ))

    return redirect(url_for('crops'))


def getcrops():
    """Fixed version with proper blob handling including -- prefix cleanup"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, data, content FROM farmers_crops")
        rows = []

        for row in cursor.fetchall():
            k = dict_from_row(row)
            data_value = k['data']

            # Handle different data formats
            if data_value:
                # Check if it's already a data URI
                if data_value.startswith('data:image/'):
                    data = data_value
                # Check if it starts with base64 marker
                elif data_value.startswith('data:'):
                    data = data_value
                else:
                    # Clean up base64 data
                    clean_data = data_value

                    # Remove -- prefix if present (common encoding artifact)
                    if clean_data.startswith('--'):
                        clean_data = clean_data[2:]

                    # Remove any whitespace
                    clean_data = clean_data.strip()

                    # Try to validate it's valid base64
                    try:
                        # Test decode to ensure it's valid base64
                        base64.b64decode(clean_data)
                        # If successful, add the data URI prefix
                        data = f"data:image/jpeg;base64,{clean_data}"
                    except:
                        # If decode fails, try as-is
                        data = f"data:image/jpeg;base64,{data_value}"
            else:
                data = None

            rows.append({'id': k['id'], 'data': data, 'content': k['content']})

        return rows, list(range(1, len(rows) + 1))


@app.route('/crops', methods=['GET', 'POST'])
def crops():
    sup = 3 if session.get('logged_in') else None
    data, data1 = getcrops()

    for i in range(len(data1)):
        data[i]['slide'] = data1[i]
    return render_template('crops.html', data=data, sup=sup)


@app.route('/cropupdate', methods=['GET', 'POST'])
def cropupdate():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, content FROM farmers_crops")
        myresult = cursor.fetchall()

        for row in myresult:
            doc_id, content = row['id'], row['content']
            update_id = f"update{doc_id}"
            delete_id = f"delete{doc_id}"

            if request.values.get(update_id):
                blob = request.values.get(f"img2{doc_id}")
                n = request.values.get(f"n{doc_id}")

                if blob and n and n != content:
                    sql = "UPDATE farmers_crops SET data=?, content=? WHERE id=?"
                    cursor.execute(sql, (blob, n, doc_id))
                elif blob:
                    sql = "UPDATE farmers_crops SET data=? WHERE id=?"
                    cursor.execute(sql, (blob, doc_id))
                elif n and n != content:
                    sql = "UPDATE farmers_crops SET content=? WHERE id=?"
                    cursor.execute(sql, (n, doc_id))
                else:
                    break
                break
            elif request.values.get(delete_id):
                sql = "DELETE FROM farmers_crops WHERE id=?"
                cursor.execute(sql, (doc_id,))
                break

    return redirect(url_for('crops'))


@app.route('/feeds', methods=['GET', 'POST'])
def feed():
    """
    Feedback page:
    - Public: submit name, email, message → saved to farmers_feedback table
    - Admin: see all submissions as cards with delete option
    """
    submitted = False  # ✅ NEW

    with get_db() as conn:
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmers_feedback (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                firstname TEXT,
                lastname  TEXT,
                email     TEXT,
                message   TEXT,
                submitted TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.commit()

        # Handle form submission (any visitor can submit)
        if request.method == 'POST' and request.values.get('action') == 'submit':
            firstname = (request.values.get('firstname') or '').strip()
            lastname  = (request.values.get('lastname')  or '').strip()
            email     = (request.values.get('email')     or '').strip()
            message   = (request.values.get('message')   or '').strip()

            if firstname and message:
                cursor.execute(
                    "INSERT INTO farmers_feedback (firstname, lastname, email, message) VALUES (?,?,?,?)",
                    (firstname, lastname, email, message)
                )
                conn.commit()
                submitted = True  # ✅ MARK SUCCESS

        # Handle delete (admin only)
        if request.method == 'POST' and request.values.get('action') == 'delete':
            if session.get('logged_in'):
                del_id = request.values.get('feed_id')
                if del_id:
                    cursor.execute("DELETE FROM farmers_feedback WHERE id=?", (del_id,))
                    conn.commit()
            return redirect(url_for('feed'))

        # Load all feedback for admin view
        feeds = []
        if session.get('logged_in'):
            cursor.execute(
                "SELECT id, firstname, lastname, email, message, submitted FROM farmers_feedback ORDER BY id DESC"
            )
            feeds = [dict_from_row(r) for r in cursor.fetchall()]

    logged_in = session.get('logged_in', False)

    # ✅ Pass submitted flag to template
    return render_template(
        'feed.html',
        feeds=feeds,
        logged_in=logged_in,
        submitted=submitted
    )


@app.route("/every", methods=['GET', 'POST'])
def every():
    if session.get('logged_in') and request.values.get("printview"):
        return redirect(url_for('bylist', pass1=request.values.get("pass1")))
    return redirect(url_for('home'))


@app.route('/map', methods=['GET', 'POST'])
def map():
    data = [f"p{i}" for i in range(1, 394)]
    return render_template('drawhtml.html', data=data)


def getnext(text):
    """Map survey numbers to their canonical form"""
    survey_map = {
        204: [204, 392], 203: [203, 386], 206: [206, 385], 205: [205, 384],
        207: [207, 383], 209: [209, 382], 208: [208, 381], 13: [13, 15],
        1: [1, 8], 95: [95, 321], 2: [2, 9], 12: [12, 16], 3: [3, 10],
        155: [155, 375], 96: [96, 320], 192: [192, 376], 14: [14, 17],
        97: [97, 319], 190: [190, 374], 98: [98, 318], 196: [196, 378],
        99: [99, 317], 195: [195, 379], 156: [156, 387], 34: [34, 216],
        39: [39, 226], 380: [380, 193, 7], 81: [81, 282], 62: [62, 309],
        194: [194, 393], 44: [44, 286], 191: [191, 373], 154: [154, 372],
        100: [100, 316], 153: [153, 371], 101: [101, 315], 152: [152, 366],
        102: [102, 314], 151: [151, 365], 103: [103, 313], 150: [150, 364],
        104: [104, 312], 145: [145, 367], 105: [105, 311], 146: [146, 368],
        106: [106, 310], 107: [107, 337], 110: [110, 324], 177: [177, 348],
        173: [173, 391], 201: [201, 361], 174: [174, 347], 202: [202, 362],
        200: [200, 358], 199: [199, 359], 109: [109, 327], 198: [198, 360],
        108: [108, 326], 157: [157, 256], 134: [134, 243], 123: [123, 244],
        66: [66, 245], 136: [136, 219], 137: [137, 242], 138: [138, 247],
        158: [158, 249], 139: [139, 239], 159: [159, 250], 135: [135, 241],
        133: [133, 238], 140: [140, 248], 160: [160, 251], 143: [143, 253],
        161: [161, 252], 142: [142, 255], 162: [162, 254], 141: [141, 258],
        163: [163, 257], 128: [128, 260], 164: [164, 259], 127: [127, 262],
        165: [165, 261], 126: [126, 267], 166: [166, 263], 124: [124, 268],
        121: [121, 269], 125: [125, 270], 119: [119, 328], 114: [114, 329],
        115: [115, 330], 116: [116, 331], 284: [284, 285], 118: [118, 332],
        120: [120, 233], 117: [117, 333], 129: [129, 235], 113: [113, 334],
        130: [130, 234], 112: [112, 335], 56: [56, 304], 131: [131, 236],
        111: [111, 336], 132: [132, 237], 71: [71, 224], 38: [38, 225],
        73: [73, 228], 72: [72, 232], 74: [74, 231], 75: [75, 229],
        40: [40, 227], 76: [76, 230], 78: [78, 272], 41: [41, 281],
        80: [80, 283], 79: [79, 271], 53: [53, 294], 52: [52, 300],
        49: [49, 298], 47: [47, 296], 82: [82, 273], 85: [85, 278],
        83: [83, 274], 84: [84, 276], 86: [86, 275], 37: [37, 223],
        70: [70, 222], 69: [69, 221], 36: [36, 220], 35: [35, 217],
        68: [68, 218], 67: [67, 214], 31: [31, 215], 30: [30, 211],
        64: [64, 212], 18: [18, 388], 33: [33, 210], 32: [32, 389],
        23: [23, 24], 19: [19, 25], 65: [65, 213], 20: [20, 26],
        6: [6, 27], 22: [22, 29], 144: [144, 339], 175: [175, 349],
        148: [148, 350], 176: [176, 369], 149: [149, 370], 172: [172, 390],
        147: [147, 338], 167: [167, 344], 168: [168, 343], 170: [170, 341],
        171: [171, 340], 169: [169, 342]
    }

    for canonical, variants in survey_map.items():
        if text in variants:
            return canonical
    return text


@app.route('/owners')
def owners():
    text = request.args.get('jsdata', '')

    if text.startswith('p'):
        try:
            text = int(text[1:])
        except ValueError:
            text = 1

    text = getnext(int(text))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM farmers_map_data WHERE mapid=?", (text,))
        out1 = [dict_from_row(row) for row in cursor.fetchall()]

    template = 'loginmap.html' if session.get('logged_in') else 'sinfomap.html'
    return render_template(template, data=out1, data1=text)


@app.route('/ownersadd')
def ownersadd():
    text = request.args.get('jsdata', '')
    a = text.split(",")
    mid = getnext(int(a[1]))

    with get_db() as conn:
        cursor = conn.cursor()
        sql = "INSERT INTO farmers_map_data (mapid, name, pass, sno, area) VALUES (?, ?, ?, ?, ?)"
        cursor.execute(sql, (mid, " ", 0, 0, 0.0))
        cursor.execute("SELECT * FROM farmers_map_data WHERE mapid=?", (mid,))
        out1 = [dict_from_row(row) for row in cursor.fetchall()]

    template = 'loginmap.html' if session.get('logged_in') else 'sinfomap.html'
    return render_template(template, data=out1, data1=mid)


@app.route('/ownersdel')
def ownersdel():
    text = request.args.get('jsdata', '')
    a = text.split(",")
    mid = getnext(int(a[1]))

    with get_db() as conn:
        cursor = conn.cursor()
        sql = "DELETE FROM farmers_map_data WHERE id=?"
        cursor.execute(sql, (a[0],))
        cursor.execute("SELECT * FROM farmers_map_data WHERE mapid=?", (mid,))
        out1 = [dict_from_row(row) for row in cursor.fetchall()]

    template = 'loginmap.html' if session.get('logged_in') else 'sinfomap.html'
    return render_template(template, data=out1, data1=mid)


@app.route('/ownersupdate')
def ownersupdate():
    text = request.args.get('jsdata', '')
    a = text.split(",")
    mid = getnext(int(a[1]))

    with get_db() as conn:
        cursor = conn.cursor()
        sql = "UPDATE farmers_map_data SET name=?, pass=?, sno=?, area=? WHERE id=?"
        cursor.execute(sql, (a[3], int(a[2]), a[4], float(a[5]), a[0]))
        cursor.execute("SELECT * FROM farmers_map_data WHERE mapid=?", (mid,))
        out1 = [dict_from_row(row) for row in cursor.fetchall()]

    template = 'loginmap.html' if session.get('logged_in') else 'sinfomap.html'
    return render_template(template, data=out1, data1=mid)


@app.route('/imginsert', methods=['GET', 'POST'])
def imginsert():
    if request.values.get("file"):
        with get_db() as conn:
            cursor = conn.cursor()
            sql = "INSERT INTO farmers_gallery (data, content) VALUES (?, ?)"
            cursor.execute(sql, (
                request.values.get("img1"),
                request.values.get("n") or " "
            ))

    return redirect(url_for('gal'))


def getimg():
    """Fixed version with proper blob handling including -- prefix cleanup"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, data, content FROM farmers_gallery")
        rows = []

        for row in cursor.fetchall():
            k = dict_from_row(row)
            data_value = k['data']

            # Handle different data formats
            if data_value:
                # Check if it's already a data URI
                if data_value.startswith('data:image/'):
                    data = data_value
                # Check if it starts with base64 marker
                elif data_value.startswith('data:'):
                    data = data_value
                else:
                    # Clean up base64 data
                    clean_data = data_value

                    # Remove -- prefix if present (common encoding artifact)
                    if clean_data.startswith('--'):
                        clean_data = clean_data[2:]

                    # Remove any whitespace
                    clean_data = clean_data.strip()

                    # Try to validate it's valid base64
                    try:
                        # Test decode to ensure it's valid base64
                        base64.b64decode(clean_data)
                        # If successful, add the data URI prefix
                        data = f"data:image/jpeg;base64,{clean_data}"
                    except:
                        # If decode fails, try as-is
                        data = f"data:image/jpeg;base64,{data_value}"
            else:
                data = None

            rows.append({'id': k['id'], 'data': data, 'content': k['content']})

        return rows, list(range(1, len(rows) + 1))


@app.route('/gallery', methods=['GET', 'POST'])
def gal():
    sup = 3 if session.get('logged_in') else None
    data, data1 = getimg()

    for i in range(len(data1)):
        data[i]['slide'] = data1[i]
    return render_template('gal.html', data=data, sup=sup)


@app.route('/imgupdate', methods=['GET', 'POST'])
def imgupdate():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, content FROM farmers_gallery")
        myresult = cursor.fetchall()

        for row in myresult:
            doc_id, content = row['id'], row['content']
            update_id = f"update{doc_id}"
            delete_id = f"delete{doc_id}"

            if request.values.get(update_id):
                blob = request.values.get(f"img2{doc_id}")
                n = request.values.get(f"n{doc_id}")

                if blob and n and n != content:
                    sql = "UPDATE farmers_gallery SET data=?, content=? WHERE id=?"
                    cursor.execute(sql, (blob, n, doc_id))
                elif blob:
                    sql = "UPDATE farmers_gallery SET data=? WHERE id=?"
                    cursor.execute(sql, (blob, doc_id))
                elif n and n != content:
                    sql = "UPDATE farmers_gallery SET content=? WHERE id=?"
                    cursor.execute(sql, (n, doc_id))
                else:
                    break
                break
            elif request.values.get(delete_id):
                sql = "DELETE FROM farmers_gallery WHERE id=?"
                cursor.execute(sql, (doc_id,))
                break

    return redirect(url_for('gal'))


@app.route('/infoinsert', methods=['GET', 'POST'])
def infoinsert():
    if request.values.get("file"):
        with get_db() as conn:
            cursor = conn.cursor()
            sql = "INSERT INTO farmers_society (data) VALUES (?)"
            cursor.execute(sql, (request.values.get("img1"),))

    return redirect(url_for('socinfo'))


def getsocinfo():
    """Fixed version with proper blob handling"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, data FROM farmers_society")
        rows = []

        for row in cursor.fetchall():
            k = dict_from_row(row)
            data_value = k['data']

            # Handle different data formats
            if data_value:
                # Check if it's already a data URI
                if data_value.startswith('data:image/'):
                    data = data_value
                # Check if it starts with base64 marker
                elif data_value.startswith('data:'):
                    data = data_value
                else:
                    # Assume it's raw base64, add the data URI prefix
                    data = f"data:image/jpeg;base64,{data_value}"
            else:
                data = None

            rows.append({'id': k['id'], 'data': data})

        return rows, list(range(1, len(rows) + 1))


@app.route('/socinfo', methods=['GET', 'POST'])
def socinfo():
    sup = 3 if session.get('logged_in') else None
    data, data1 = getsocinfo()

    for i in range(len(data1)):
        data[i]['slide'] = data1[i]
    return render_template('socinfo.html', data=data, sup=sup)


@app.route('/infoupdate', methods=['GET', 'POST'])
def infoupdate():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM farmers_society")
        myresult = cursor.fetchall()

        for row in myresult:
            doc_id = row['id']
            update_id = f"update{doc_id}"
            delete_id = f"delete{doc_id}"

            if request.values.get(update_id):
                blob = request.values.get(f"img2{doc_id}")
                if blob:
                    sql = "UPDATE farmers_society SET data=? WHERE id=?"
                    cursor.execute(sql, (blob, doc_id))
                break
            elif request.values.get(delete_id):
                sql = "DELETE FROM farmers_society WHERE id=?"
                cursor.execute(sql, (doc_id,))
                break

    return redirect(url_for('socinfo'))


@app.route('/kara', methods=['GET', 'POST'])
def kara():
    return render_template('kara.html')


@app.route('/userinfo', methods=['GET', 'POST'])
def userinfo():
    text = request.args.get('jsdata')
    session['mappass'] = int(text)
    return jsonify(success=True)


@app.route('/bylist', methods=['GET', 'POST'])
def bylist():
    with get_db() as conn:
        cursor = conn.cursor()

        # Get all years
        cursor.execute("SELECT years FROM farmers_years ORDER BY id DESC")
        ye = [row['years'] for row in cursor.fetchall()]

        # Selected year (default latest)
        year = request.values.get('year')
        if not year:
            year = ye[0] if ye else None

        # Get all first=1 records for listing
        cursor.execute(
            "SELECT * FROM farmers_data WHERE first=1 AND year=? ORDER BY pass",
            (year,)
        )
        farmer_list = [dict_from_row(row) for row in cursor.fetchall()]

        # If user selected passes → show full print2 data
        rows = []
        for farmer in farmer_list:
            if request.values.get(str(farmer['pass'])):
                cursor.execute(
                    "SELECT * FROM farmers_data WHERE pass=? AND year=? ORDER BY pass",
                    (farmer['pass'], year)
                )
                rows.extend([dict_from_row(row) for row in cursor.fetchall()])

        if rows:
            return render_template('print2.html',
                                   data=rows,
                                   dby=ye,
                                   year1=year)

        # Otherwise show the existing member list page.
        return render_template('bylist.html',
                               data=farmer_list,
                               dby=ye,
                               year=year)


@app.route('/datasee', methods=['GET', 'POST'])
def datasee():
    return render_template('datasee.html')


@app.route('/dataseepay', methods=['GET', 'POST'])
def dataseepay():
    return render_template('dataseepay.html')


@app.route('/datasee1', methods=['GET', 'POST'])
def datasee1():
    text = request.args.get('jsdata', '')
    a = text.split(",")
    pass_no = a[0]
    year = a[1] if len(a) > 1 and a[1] else None

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT years FROM farmers_years ORDER BY id DESC")
        ye = [row['years'] for row in cursor.fetchall()]

        if not year:
            year = ye[0] if ye else None

        cursor.execute(
            "SELECT * FROM farmers_data WHERE pass=? AND year=? ORDER BY first DESC",
            (int(pass_no), year)
        )
        rows = [dict_from_row(row) for row in cursor.fetchall()]

        return render_template('datasee1.html', data=rows, dby=ye, year=year)


@app.route('/datasee1pay', methods=['GET', 'POST'])
def datasee1pay():
    text = request.args.get('jsdata', '')
    a = text.split(",")
    pass_no = a[0]
    year = a[1] if len(a) > 1 and a[1] else None

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT years FROM farmers_years ORDER BY id DESC")
        ye = [row['years'] for row in cursor.fetchall()]

        if not year:
            year = ye[0] if ye else None

        cursor.execute(
            "SELECT * FROM farmers_data WHERE pass=? AND year=? ORDER BY first DESC",
            (int(pass_no), year)
        )
        rows = [dict_from_row(row) for row in cursor.fetchall()]

        return render_template('datasee1pay.html', data=rows, dby=ye, year=year)


@app.route('/datapayment', methods=['GET', 'POST'])
def datapayment():
    text = request.args.get('jsdata', '')
    a = text.split(",")
    amount = float(a[0]) if a[0] else 0
    pass_no = int(a[1])
    year = a[2] if len(a) > 2 else None

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT years FROM farmers_years ORDER BY id DESC")
        ye = [row['years'] for row in cursor.fetchall()]

        if not year:
            year = ye[0] if ye else None

        # Bulk update all records for this pass and year
        cursor.execute(
            "UPDATE farmers_data SET paid=paid+?, balance=balance-? WHERE pass=? AND year=?",
            (amount, amount, pass_no, year)
        )

        cursor.execute(
            "SELECT * FROM farmers_data WHERE pass=? AND year=? ORDER BY first DESC",
            (pass_no, year)
        )
        rows = [dict_from_row(row) for row in cursor.fetchall()]

        return render_template('datasee1pay.html', data=rows, dby=ye, year=year)


@app.route('/userprint1', methods=['GET', 'POST'])
def userprint1():
    text = request.args.get('jsdata')
    session['upass'] = int(text)
    resp = jsonify(success=True)
    return resp


@app.route('/userprint', methods=['GET', 'POST'])
def userprint():
    if session.get('logged_in'):
        if session.get('upass'):
            text = session.get('upass')
            with get_db() as conn:
                cursor = conn.cursor()

                # One ordered read supplies both the full list and latest year.
                cursor.execute("SELECT years FROM farmers_years ORDER BY id")
                year_rows = cursor.fetchall()
                ye = [row['years'] for row in year_rows]
                y = ye[-1] if ye else None

                # Get data for the pass and year
                cursor.execute(
                    "SELECT * FROM farmers_data WHERE pass=? AND year=?",
                    (int(text), y)
                )
                rows = [dict_from_row(row) for row in cursor.fetchall()]

                return render_template('print2.html',
                                       data=rows,
                                       dby=ye,
                                       year1=y)
    return redirect(url_for('home'))


@app.route('/dbyearwise', methods=['GET', 'POST'])
def dbyearwise():
    year = request.values.get("year")

    with get_db() as conn:
        cursor = conn.cursor()
        if year:
            cursor.execute(
                """SELECT d.*, m.name as village, m.sno, m.area as acers 
                   FROM farmers_data d 
                   LEFT JOIN farmers_map_data m ON d.pass=m.pass 
                   WHERE d.year=? 
                   ORDER BY d.pass""",
                (year,)
            )
        else:
            cursor.execute(
                """SELECT d.*, m.name as village, m.sno, m.area as acers 
                   FROM farmers_data d 
                   LEFT JOIN farmers_map_data m ON d.pass=m.pass 
                   ORDER BY d.pass"""
            )

        suggestions = [dict_from_row(row) for row in cursor.fetchall()]

        if session.get('logged_in'):
            return render_template('dbyearwise1.html', data=suggestions)
        return render_template('dbyearwise.html', suggestions=suggestions)


@app.route('/dbupdate', methods=['POST'])
def dbupdate():
    if not session.get('logged_in'):
        return redirect(url_for('home'))

    year = request.values.get("year")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT d.id as sid, d.* 
               FROM farmers_data d 
               WHERE d.year=? 
               ORDER BY d.pass""",
            (year,)
        )
        data = [dict_from_row(row) for row in cursor.fetchall()]

        # Collect all updates in batch
        updates = []
        for i in data:
            sid = i['sid']
            updates.append((
                request.values.get(f"{sid}name"),
                request.values.get(f"{sid}share"),
                request.values.get(f"{sid}village"),
                request.values.get(f"{sid}sno"),
                request.values.get(f"{sid}acers"),
                request.values.get(f"{sid}crop1"),
                request.values.get(f"{sid}area1"),
                request.values.get(f"{sid}kara1"),
                request.values.get(f"{sid}crop2"),
                request.values.get(f"{sid}area2"),
                request.values.get(f"{sid}kara2"),
                request.values.get(f"{sid}wtax"),
                request.values.get(f"{sid}mtax"),
                request.values.get(f"{sid}total"),
                request.values.get(f"{sid}pp"),
                request.values.get(f"{sid}phone"),
                sid
            ))

        # Bulk update
        if updates:
            sql = """UPDATE farmers_data 
                     SET name=?, share=?, village=?, sno=?, area=?,
                         crop1=?, area1=?, kara1=?, crop2=?, area2=?,
                         kara2=?, wtax=?, mtax=?, total=?, pp=?, phone=?
                     WHERE id=?"""
            cursor.executemany(sql, updates)

    return redirect(url_for('dbyearwise'))


@app.route('/datapay', methods=['GET', 'POST'])
def datapay():
    if not session.get('logged_in'):
        return redirect(url_for('home'))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT years FROM farmers_years ORDER BY id DESC")
        ye = [row['years'] for row in cursor.fetchall()]
        year = request.values.get("year", ye[0] if ye else None)

        cursor.execute(
            """SELECT * FROM farmers_data 
               WHERE year=? AND first=1 
               ORDER BY pass""",
            (year,)
        )
        b = [dict_from_row(row) for row in cursor.fetchall()]

        rows = []
        for z, i in enumerate(b, 1):
            i['no'] = z
            rows.append(i)

        return render_template('dataedit1.html', data=rows, dby=ye, year=year)


@app.route('/datapayup', methods=['GET', 'POST'])
def datapayup():
    if request.values.get("year1"):
        year1 = request.values.get("year1")
        pass1 = request.values.get('pass')
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT years FROM farmers_years ORDER BY id DESC")
            ye = [row['years'] for row in cursor.fetchall()]
            cursor.execute(
                "SELECT * FROM farmers_data WHERE pass=? AND year=?",
                (int(pass1), year1)
            )
            rows = [dict_from_row(row) for row in cursor.fetchall()]
            return render_template('print2.html', data=rows, dby=ye, year1=year1)

    if request.values.get("up"):
        year = request.values.get('year')
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM farmers_data WHERE year=? AND first=1 ORDER BY pass",
                (year,)
            )
            b = [dict_from_row(row) for row in cursor.fetchall()]
            updates = []          # paid/balance updates for current year only
            name_share_updates = []  # name/share updates across ALL years

            for i in b:
                p     = int(request.values.get(f"pass{i['id']}"))
                name  = request.values.get(f"name{i['id']}")
                paid  = request.values.get(f"paid{i['id']}")
                tbal  = request.values.get(f"tbal{i['id']}")
                share = request.values.get(f"share{i['id']}")
                paid  = 0.0 if paid  == "None" or not paid  else round(float(paid),  2)
                tbal  = 0.0 if tbal  == "None" or not tbal  else round(float(tbal),  2)
                try:
                    share_form = int(share or 0)
                    share_db   = int(i['share'] or 0)
                    share_changed = share_form != share_db
                except (ValueError, TypeError):
                    share_form    = 0
                    share_changed = False

                name_changed = name != i['name']

                # If name or share changed → queue update across ALL years for this pass
                if name_changed or share_changed:
                    name_share_updates.append((name, share_form, p))

                # paid / balance changes → current year only
                pay_changed = (
                    round(float(paid), 2) != round(float(i['paid']),    2) or
                    round(float(tbal), 2) != round(float(i['balance']), 2)
                )
                if pay_changed:
                    updates.append((name, share_form, paid, tbal, year, int(p)))

            # Update each changed pass directly; avoids selecting every row ID first.
            if updates:
                sql = """UPDATE farmers_data
                         SET name=?, share=?, paid=?, balance=?
                         WHERE year=? AND pass=?"""
                cursor.executemany(sql, updates)

            # Propagate name/share to ALL years for each affected pass
            if name_share_updates:
                sql = "UPDATE farmers_data SET name=?, share=? WHERE pass=?"
                cursor.executemany(sql, name_share_updates)

            return redirect(url_for('datapay'))

    year = request.values.get('year')
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT years FROM farmers_years ORDER BY id DESC")
        ye = [row['years'] for row in cursor.fetchall()]
        cursor.execute(
            "SELECT DISTINCT pass FROM farmers_data WHERE year=? AND first=1 ORDER BY pass",
            (year,)
        )
        b = [dict_from_row(row) for row in cursor.fetchall()]
        rows = []
        for i in b:
            if request.values.get(str(i['pass'])):
                cursor.execute(
                    "SELECT * FROM farmers_data WHERE year=? AND pass=? ORDER BY pass",
                    (ye[0], i['pass'])
                )
                rows.extend([dict_from_row(row) for row in cursor.fetchall()])
        return render_template('print2.html', data=rows, dby=ye, year1=ye[0] if ye else None)


@app.route('/dataindex', methods=['GET', 'POST'])
def dataindex():
    if not session.get('logged_in'):
        return redirect(url_for('home'))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT years FROM farmers_years ORDER BY id DESC")
        ye = [row['years'] for row in cursor.fetchall()]
        year = request.values.get("year", ye[0] if ye else None)

        cursor.execute(
            "SELECT * FROM farmers_data WHERE year=? ORDER BY pass ASC, first DESC",
            (year,)
        )
        rows = [dict_from_row(row) for row in cursor.fetchall()]

        return render_template('dataindex.html', data=rows, dby=ye, year=year)


@app.route('/dataedit', methods=['GET', 'POST'])
def dataedit():
    if not session.get('logged_in'):
        return redirect(url_for('home'))

    if session.get('delpass') != 0:
        session['delpass'] = 0

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM farmers_year_data ORDER BY id DESC")
        ye = [dict_from_row(row) for row in cursor.fetchall()]
        year = request.values.get("year", ye[0]['y'] if ye else None)

        price = next((y for y in ye if y['y'] == year), None)
        years = [y['y'] for y in ye]

        cursor.execute(
            "SELECT * FROM farmers_data WHERE year=? ORDER BY pass",
            (year,)
        )
        b = [dict_from_row(row) for row in cursor.fetchall()]

        rows = []
        for z, i in enumerate(b, 1):
            i['no'] = z
            rows.append(i)

        return render_template('dataedit.html', data=rows, dby=years, year=year, price=price)


@app.route('/dataeditup', methods=['GET', 'POST'])
def dataeditup():
    y = request.values.get("year")

    if request.values.get("submit"):
        datanewadd()
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM farmers_data WHERE year=? ORDER BY id", (y,))
            b = [dict_from_row(row) for row in cursor.fetchall()]

            # Collect all updates for bulk operation
            updates = []
            for i in b:
                rec_id = i['id']

                # Get all form values
                name = request.values.get(f"name{rec_id}")
                p = request.values.get(f"pass{rec_id}")
                sno = request.values.get(f"sno{rec_id}")
                area = request.values.get(f"area{rec_id}")
                batha = request.values.get(f"batha{rec_id}")
                bkara = request.values.get(f"bkara{rec_id}")
                kabu = request.values.get(f"kabu{rec_id}")
                kkara = request.values.get(f"kkara{rec_id}")
                thota = request.values.get(f"thota{rec_id}")
                tkara = request.values.get(f"tkara{rec_id}")
                wtax = request.values.get(f"wtax{rec_id}")
                mtax = request.values.get(f"mtax{rec_id}")
                t1 = request.values.get(f"t1{rec_id}")
                bal = request.values.get(f"bal{rec_id}")
                t2 = request.values.get(f"t2{rec_id}")

                # Convert None strings to appropriate values
                def safe_float(val):
                    return 0.0 if val == "None" or not val else round(float(val), 2)

                area = safe_float(area)
                bal = safe_float(bal)
                batha = safe_float(batha)
                kabu = safe_float(kabu)
                thota = safe_float(thota)
                bkara = safe_float(bkara) if bkara else None
                kkara = safe_float(kkara) if kkara else None
                tkara = safe_float(tkara) if tkara else None
                wtax = safe_float(wtax) if wtax else None
                mtax = safe_float(mtax) if mtax else None
                t1 = safe_float(t1) if t1 else None
                t2 = safe_float(t2) if t2 else None
                p = int(p) if p else None

                # Check if anything changed
                changed = (
                        name != i['name'] or p != i['pass'] or sno != i['sno'] or
                        area != i['area'] or batha != i['batha'] or bkara != i['bkara'] or
                        kabu != i['kabu'] or kkara != i['kkara'] or thota != i['thota'] or
                        tkara != i['tkara'] or wtax != i['wtax'] or mtax != i['mtax'] or
                        t1 != i['t1'] or bal != i['bal'] or t2 != i['t2']
                )

                if changed:
                    updates.append((
                        name, p, sno, area, batha, bkara, kabu, kkara, thota, tkara,
                        wtax, mtax, t1, bal, t2, rec_id, y
                    ))

            # Bulk update
            if updates:
                sql = """UPDATE farmers_data 
                         SET name=?, pass=?, sno=?, area=?, batha=?, bkara=?,
                             kabu=?, kkara=?, thota=?, tkara=?, wtax=?, mtax=?,
                             t1=?, bal=?, t2=?
                         WHERE id=?"""
                cursor.executemany(sql, [(u[:-1]) for u in updates])

                # Update aggregates for affected passes
                affected_passes = set(u[1] for u in updates)
                for pass_no in affected_passes:
                    doalter(int(pass_no), y, cursor)

    return redirect(url_for('dataedit'))


def datanewadd():
    year = request.values.get("year")
    pass_no = int(request.values.get("pass"))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT count, bal FROM farmers_data WHERE pass=? AND year=?",
            (pass_no, year)
        )
        b = [dict_from_row(row) for row in cursor.fetchall()]

        count = (b[0]['count'] + 1) if b else 0
        first = 0 if b else 1

        # Get form values
        sno = request.values.get("sno")
        area = request.values.get("area")
        batha = request.values.get("batha")
        bkara = round(float(request.values.get("bkara")), 2)
        kabu = request.values.get("kabu")
        kkara = round(float(request.values.get("kkara")), 2)
        thota = request.values.get("thota")
        tkara = round(float(request.values.get("tkara")), 2)
        wtax = round(float(request.values.get("wtax")), 2)
        mtax = round(float(request.values.get("mtax")), 2)
        t1 = round(float(request.values.get("t1")), 2)
        bal = request.values.get("bal")
        t2 = round(float(request.values.get("t2")), 2)
        name = request.values.get("name")

        # Calculate aggregates from existing records
        rt = t1
        old = 0
        total = t2
        for j in b:
            rt += j.get('rt', 0)
            old = j.get('bal', 0)
            total += j.get('t2', 0)

        sql = """INSERT INTO farmers_data 
                 (pass, sno, area, batha, bkara, kabu, kkara, thota, tkara,
                  wtax, mtax, t1, bal, t2, count, name, rt, old, total, paid,
                  balance, first, share, year)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                         ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

        cursor.execute(sql, (
            pass_no, sno, area, batha, bkara, kabu, kkara, thota, tkara,
            wtax, mtax, t1, bal, t2, count, name, rt, old, total, 0.0,
            total, first, 0, year
        ))

        doalter(pass_no, year, cursor)


@app.route('/dataeditadd')
def dataeditadd():
    text = request.args.get('jsdata', '')
    text = text.split(",")
    pass_no = int(text[0])
    year = text[1]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT count, name, share FROM farmers_data WHERE pass=? AND year=?",
            (pass_no, year)
        )
        b = [dict_from_row(row) for row in cursor.fetchall()]

        count = (b[0]['count'] + 1) if b else 0
        name = b[0]['name'] if b else " "
        share = b[0]['share'] if b else 0

        sql = """INSERT INTO farmers_data
                 (pass, sno, area, batha, bkara, kabu, kkara, thota, tkara,
                  wtax, mtax, t1, bal, t2, count, name, rt, old, total, paid,
                  balance, first, share, year)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                         ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

        cursor.execute(sql, (
            pass_no, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            count, name, 0.0, 0.0, 0.0, 0.0, 0.0, 0, share, year
        ))

        # Pass cursor to avoid opening a second connection (fixes "database is locked")
        doalter(pass_no, year, cursor)

    return redirect(url_for('dataedit'))


@app.route('/dataeditdel')
def dataeditdel():
    text = request.args.get('jsdata', '')
    a = text.split(",")
    rec_id = a[0]
    pass_no = int(a[1])
    year = a[2]

    session['delpass'] = pass_no

    with get_db() as conn:
        cursor = conn.cursor()
        sql = "DELETE FROM farmers_data WHERE id=?"
        cursor.execute(sql, (rec_id,))

        # Pass cursor to avoid opening a second connection (fixes "database is locked")
        doalter(pass_no, year, cursor)

    return redirect(url_for('dataedit'))


def doalter(a, b, cursor=None):
    """Recalculate aggregates for a specific pass and year.

    Pass cursor= to reuse an existing connection (avoids 'database is locked').
    Omit cursor to open a standalone connection.
    """
    def _do(cur):
        cur.execute(
            "SELECT id, t1, bal, t2, paid FROM farmers_data WHERE pass=? AND year=?",
            (a, b)
        )
        c = [dict_from_row(row) for row in cur.fetchall()]
        if not c:
            return
        count = len(c)
        rt   = sum(float(j['t1'])  for j in c)
        old  = sum(float(j['bal']) for j in c)
        tot  = sum(float(j['t2'])  for j in c)
        paid = float(c[0]['paid']) if c else 0.0
        tbal = tot - paid
        updates = []
        for idx, k in enumerate(c):
            first  = 1 if idx == 0 else 0
            bcount = count if first == 1 else 0
            updates.append((
                bcount,
                round(float(rt),   2),
                round(float(old),  2),
                round(float(tot),  2),
                round(float(paid), 2),
                round(float(tbal), 2),
                first,
                k['id']
            ))
        sql = """UPDATE farmers_data
                 SET count=?, rt=?, old=?, total=?, paid=?, balance=?, first=?
                 WHERE id=?"""
        cur.executemany(sql, updates)

    if cursor is not None:
        _do(cursor)
    else:
        with get_db() as conn:
            _do(conn.cursor())


@app.route('/allmap', methods=['GET', 'POST'])
def allmap():
    return render_template('allmap.html')


@app.route('/year', methods=['GET', 'POST'])
def years():
    if not session.get('logged_in'):
        return redirect(url_for('home', _external=True, _scheme='https'))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT years FROM farmers_years ORDER BY id DESC LIMIT 1")
        y = cursor.fetchone()
        year = y['years'] if y else "2023-2024"

        a = year.split("-")
        next_year = f"{int(a[0]) + 1}-{int(a[1]) + 1}"

        cursor.execute("SELECT * FROM farmers_year_data ORDER BY id DESC")
        ye = [dict_from_row(row) for row in cursor.fetchall()]

        return render_template('year.html', year=year, ye=ye, next=next_year, pre=year)


@app.route('/datayearup', methods=['GET', 'POST'])
def yearsup():
    if request.values.get("submit"):
        year = request.values.get("year")
        batha = float(request.values.get("batha"))
        kabbu = float(request.values.get("kabbu"))
        tota = float(request.values.get("tota"))
        mt = float(request.values.get("mt"))

        with get_db() as conn:
            cursor = conn.cursor()
            # Get last year's data
            cursor.execute("SELECT years FROM farmers_years ORDER BY id DESC LIMIT 1")
            last_year_row = cursor.fetchone()

            if not last_year_row:
                return redirect(url_for('years'))

            last_year = last_year_row['years']

            cursor.execute(
                "SELECT * FROM farmers_data WHERE year=? ORDER BY id",
                (last_year,)
            )
            myresult = [dict_from_row(row) for row in cursor.fetchall()]

            # Group by pass
            ind = {}
            for j in myresult:
                pass_num = j['pass']
                if pass_num not in ind:
                    ind[pass_num] = []

                share = j.get('share', 0)

                # Calculate taxes based on crop type
                def calc_tax(area, price):
                    area_float = float(area)
                    integer_part = int(area_float)
                    decimal_part = area_float - integer_part
                    return (integer_part * 40 * price) + (decimal_part * 100 * price)

                bkara = calc_tax(j['batha'], batha)
                kkara = calc_tax(j['kabu'], kabbu)
                tkara = calc_tax(j['thota'], tota)
                mtax = calc_tax(j['area'], mt)
                wtax = round(bkara + kkara + tkara, 2)
                t1 = round(mtax + wtax, 2)

                # Get the previous year's balance for first records only
                old_balance = float(j['balance']) if j['first'] == 1 else 0.0

                mydict = {
                    'pass': pass_num,
                    'sno': j['sno'],
                    'area': float(j['area']),
                    'batha': float(j['batha']),
                    'bkara': round(bkara, 2),
                    'kabu': float(j['kabu']),
                    'kkara': round(kkara, 2),
                    'thota': float(j['thota']),
                    'tkara': round(tkara, 2),
                    'wtax': wtax,
                    'mtax': round(mtax, 2),
                    't1': t1,
                    'name': j['name'],
                    'share': share,
                    'year': year,
                    'first': j['first'],
                    'paid': 0.0,
                }

                # For first record, carry forward the balance
                if j['first'] == 1:
                    mydict['bal'] = old_balance
                    mydict['t2'] = round(t1 + old_balance, 2)
                    mydict['old'] = old_balance
                else:
                    mydict['bal'] = 0.0
                    mydict['t2'] = t1
                    mydict['old'] = 0.0

                ind[pass_num].append(mydict)

            # Calculate aggregates per pass
            data = []
            for pass_key in ind.keys():
                each_pass = ind[pass_key]
                count = len(each_pass)

                # Calculate totals
                rt = sum(p['t1'] for p in each_pass)
                old_sum = sum(p['bal'] for p in each_pass)  # Should only be first record's balance
                total_t2 = sum(p['t2'] for p in each_pass)

                for r in each_pass:
                    r['rt'] = round(rt, 2)
                    r['old'] = round(old_sum, 2)
                    r['total'] = round(total_t2, 2)
                    r['balance'] = round(total_t2, 2)  # Initial balance = total (no payments yet)
                    r['count'] = count if r['first'] == 1 else 0
                    data.append(r)

            # Bulk insert - order matters!
            if data:
                sql = """INSERT INTO farmers_data 
                         (pass, sno, area, batha, bkara, kabu, kkara, thota, tkara,
                          wtax, mtax, t1, name, share, year, first, paid, bal, t2, old,
                          rt, total, balance, count)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

                bulk_data = [
                    (
                        d['pass'], d['sno'], d['area'], d['batha'], d['bkara'],
                        d['kabu'], d['kkara'], d['thota'], d['tkara'], d['wtax'],
                        d['mtax'], d['t1'], d['name'], d['share'], d['year'],
                        d['first'], d['paid'], d['bal'], d['t2'], d['old'],
                        d['rt'], d['total'], d['balance'], d['count']
                    ) for d in data
                ]
                cursor.executemany(sql, bulk_data)

                # Insert year data
                sql = "INSERT INTO farmers_year_data (y, batha, kabbu, tota, mtax) VALUES (?, ?, ?, ?, ?)"
                cursor.execute(sql, (year, batha, kabbu, tota, mt))

                sql = "INSERT INTO farmers_years (years) VALUES (?)"
                cursor.execute(sql, (year,))

        return redirect(url_for('years'))

    if request.values.get("del"):
        z = request.values.get("del")
        text = z.split(" ")
        year = text[1]

        with get_db() as conn:
            cursor = conn.cursor()
            # Delete year data
            cursor.execute("DELETE FROM farmers_data WHERE year=?", (year,))
            cursor.execute("DELETE FROM farmers_year_data WHERE y=?", (year,))
            cursor.execute("DELETE FROM farmers_years WHERE years=?", (year,))

        return redirect(url_for('years'))

    return redirect(url_for('home'))


@app.route('/datacorrection', methods=['GET', 'POST'])
def datacorrection():
    year = request.values.get("year")

    with get_db() as conn:
        cursor = conn.cursor()
        # One ordered read replaces the previous query-per-pass loop.
        cursor.execute(
            "SELECT id, pass FROM farmers_data WHERE year=? ORDER BY pass, id",
            (year,)
        )
        year_records = cursor.fetchall()

        # Preserve the same lowest-id first-record and per-pass count behavior.
        values = []
        for _, grouped_records in groupby(year_records, key=lambda row: row['pass']):
            pass_records = list(grouped_records)
            for idx, record in enumerate(pass_records):
                first = 1 if idx == 0 else 0
                count = len(pass_records) if first == 1 else 0
                values.append((first, count, record['id']))

        # Bulk update
        if values:
            sql = "UPDATE farmers_data SET first=?, count=? WHERE id=?"
            cursor.executemany(sql, values)

        # Get corrected data for display
        cursor.execute("SELECT years FROM farmers_years ORDER BY id DESC")
        ye = [row['years'] for row in cursor.fetchall()]

        if not year:
            year = ye[0] if ye else None

        cursor.execute(
            "SELECT * FROM farmers_data WHERE year=? ORDER BY pass ASC, first DESC",
            (year,)
        )
        rows = [dict_from_row(row) for row in cursor.fetchall()]

        return render_template('dataindex.html', data=rows, dby=ye, year=year)

@app.route('/export_my_db', methods=['GET'])
def export_my_db():
    """
    Download current database as backup
    Requires login for security
    """
    # Security check - must be logged in
    if not session.get('logged_in'):
        return redirect(url_for('home'))

    # Check if database exists
    if not os.path.exists(DB_PATH):
        return "Database file not found!", 404

    try:
        # Generate filename with current date/time
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        download_name = f'wucskkm_backup_{timestamp}.db'

        # Send file as download
        return send_file(
            DB_PATH,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/x-sqlite3'
        )
    except Exception as e:
        return f"Error downloading database: {e}", 500

"""
=================================================================
CHART API ROUTES  —  Paste into main.py
Place AFTER the get_db() context-manager definition (~line 219).

Also add at the very top of main.py (with other imports):
    from collections import defaultdict
=================================================================
"""

from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


# ──────────────────────────────────────────────────────
# 1. Year-wise Paid Amount  (bar + trend line)
# ──────────────────────────────────────────────────────
def _area_to_guntes(value):
    """Convert stored Acre.Gunte notation to an integer Gunte total."""
    if value in (None, ''):
        return 0

    try:
        area = Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError):
        return 0

    if area <= 0:
        return 0

    acres = int(area)
    guntes = int(
        ((area - Decimal(acres)) * 100).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        )
    )
    return (acres * 40) + guntes


def _guntes_to_area(total_guntes):
    """Return normalized Acre/Gunte components and a display value."""
    total_guntes = max(0, int(total_guntes or 0))
    acres, guntes = divmod(total_guntes, 40)
    return {
        'acres': acres,
        'guntes': guntes,
        'total_guntes': total_guntes,
        'display': f'{acres} Acre {guntes} Gunte',
    }


@app.route('/api/chart/paid-by-year')
def api_paid_by_year():
    """SUM(paid) grouped by last 4 financial years (joined table) where first=1."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            years = latest_financial_years(cursor, limit=4)
            if not years:
                return jsonify({'labels': [], 'values': []})

            placeholders = ','.join('?' for _ in years)
            cursor.execute(f"""
                SELECT f.year,
                       SUM(f.paid) AS total_paid
                FROM farmers_data f
                JOIN farmers_year_data fy 
                     ON f.year = fy.y
                WHERE f.first = 1
                  AND f.year IN ({placeholders})
                GROUP BY f.year
                ORDER BY CAST(SUBSTR(f.year,1,4) AS INTEGER) ASC
            """, years)

            rows = cursor.fetchall()

        labels = [str(r['year']) for r in rows]
        values = [round(float(r['total_paid'] or 0), 2) for r in rows]

        return jsonify({'labels': labels, 'values': values})

    except Exception as e:
        print(f"[api_paid_by_year] {e}")
        return jsonify({'labels': [], 'values': [], 'error': str(e)})


# ──────────────────────────────────────────────────────
# 2. Crops Distribution by Area  (doughnut)
#    Main crops: batha (ಭತ್ತ)  kabu (ಕಬ್ಬು)  thota (ತೋಟ)
#    Everything else in crop1/crop2 → ಇತರೆ
#    Area conversion: int part = acres, frac*100 = guntes, 40g=1a
# ──────────────────────────────────────────────────────
@app.route('/api/chart/crops-area')
def api_crops_area():
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            latest_years = latest_farmer_data_years(cursor, limit=1)
            if not latest_years:
                return jsonify({'labels': [], 'values': [], 'years': [], 'year': None})

            placeholders = ','.join('?' for _ in latest_years)
            cursor.execute(f"""
                SELECT batha, kabu, thota, crop1, area1, crop2, area2
                FROM   farmers_data
                WHERE  year IN ({placeholders})
            """, latest_years)
            rows = cursor.fetchall()

        # names that already map to the three main crops (don't double-count)
        main_crop_names = {
            'batha', 'bhath', 'rice',
            'kabu',  'kabbu', 'sugarcane',
            'thota', 'tota',  'garden'
        }

        # Aggregate in Gunte (40 Gunte = 1 Acre), never by decimal addition.
        total_batha = 0
        total_kabu  = 0
        total_thota = 0
        total_other = 0

        for row in rows:
            total_batha += _area_to_guntes(row['batha'])
            total_kabu  += _area_to_guntes(row['kabu'])
            total_thota += _area_to_guntes(row['thota'])

            # crop1 / area1
            c1 = (row['crop1'] or '').strip().lower()
            a1 = _area_to_guntes(row['area1'])
            if a1 > 0 and c1 not in main_crop_names:
                total_other += a1

            # crop2 / area2
            c2 = (row['crop2'] or '').strip().lower()
            a2 = _area_to_guntes(row['area2'])
            if a2 > 0 and c2 not in main_crop_names:
                total_other += a2

        crop_data = [
            ('ಭತ್ತ', total_batha),
            ('ಕಬ್ಬು', total_kabu),
            ('ತೋಟ', total_thota),
            ('ಇತರೆ', total_other),
        ]

        labels = [c[0] for c in crop_data if c[1] > 0]
        values = [c[1] for c in crop_data if c[1] > 0]
        areas = [_guntes_to_area(c[1]) for c in crop_data if c[1] > 0]

        return jsonify({
            'labels': labels,
            # Values use the integer base unit; clients should display areas below.
            'values': values,
            'areas': areas,
            'formatted_values': [area['display'] for area in areas],
            'unit': 'gunte',
            'years': latest_years,
            'year': latest_years[0]
        })

    except Exception as e:
        print(f"[api_crops_area] {e}")
        return jsonify({'labels': [], 'values': [], 'error': str(e)})


# ──────────────────────────────────────────────────────
# 3. Share vs Non-Share  (LATEST year only)
#    share column: if it's a valid integer string → share member
#    else (empty, null, or non-numeric)          → non-share
# ──────────────────────────────────────────────────────
@app.route('/api/chart/share-count')
def api_share_count():
    """
    Counts unique farmers (first=1) in the latest year.
    share = numeric string  →  ಷೇರುದಾರರು
    share = blank / null    →  ಷೇರೇತರರು
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # --- resolve latest year ---
            years = latest_financial_years(cursor, limit=1)
            latest_year = years[0] if years else None

            if not latest_year:
                return jsonify({
                    'labels': ['ಷೇರುದಾರರು', 'ಷೇರೇತರರು'],
                    'values': [0, 0], 'year': None
                })

            # --- count ---
            # Share member   = numeric integer AND value > 0  (e.g. "123")
            # Non-share      = null / blank / "0" / non-numeric
            cursor.execute("""
                SELECT
                    SUM(CASE
                          WHEN share IS NOT NULL
                           AND TRIM(share) != ''
                           AND TRIM(share) GLOB '[1-9]*'
                           AND CAST(TRIM(share) AS INTEGER) > 0
                          THEN 1 ELSE 0 END) AS share_cnt,

                    SUM(CASE
                          WHEN share IS NULL
                            OR TRIM(share) = ''
                            OR TRIM(share) = '0'
                            OR NOT (TRIM(share) GLOB '[1-9]*')
                          THEN 1 ELSE 0 END) AS non_share_cnt

                FROM farmers_data
                WHERE year  = ?
                  AND first = 1
            """, (latest_year,))

            r = cursor.fetchone()

        return jsonify({
            'labels': ['ಷೇರುದಾರರು', 'ಷೇರೇತರರು'],
            'values': [int(r['share_cnt'] or 0), int(r['non_share_cnt'] or 0)],
            'year':   latest_year
        })

    except Exception as e:
        print(f"[api_share_count] {e}")
        return jsonify({
            'labels': ['ಷೇರುದಾರರು', 'ಷೇರೇತರರು'],
            'values': [0, 0], 'error': str(e)        })

# Initialize SQLAdmin
if __name__ == '__main__':
    # Import and initialize admin

    app.secret_key = os.urandom(12)
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=5000)

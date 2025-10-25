# add_user.py
from flask import Flask, request, jsonify, send_from_directory
import sqlite3, os, webbrowser
from threading import Timer
from flask_cors import CORS

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app, origins=["http://127.0.0.1:5500", "http://localhost:5500"])

DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name  TEXT NOT NULL,
            email      TEXT NOT NULL UNIQUE,
            password   TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -------- Static file serving (index.html, styles.css, assets/*) --------
@app.route("/")
def root():
    return send_from_directory(".", "index.html")  # serves your existing index.html

@app.route("/<path:path>")
def static_proxy(path):
    # This will serve styles.css, planner.html, assets/..., etc. from the same folder
    if os.path.exists(path):
        return send_from_directory(".", path)
    return ("Not found", 404)

# -------- API: Register user --------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    first = data.get("first_name", "").strip()
    last  = data.get("last_name", "").strip()
    email = data.get("email", "").strip().lower()
    pwd   = data.get("password", "")

    if not (first and last and email and pwd):
        return jsonify({"success": False, "error": "Missing fields"})

    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (first_name, last_name, email, password) VALUES (?, ?, ?, ?)",
            (first, last, email, pwd)
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "error": "Email already exists"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    pwd   = data.get("password") or ""

    if not (email and pwd):
        return jsonify({"success": False, "error": "Email and password are required"})

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT first_name, password FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({"success": False, "error": "Invalid email or password"})

    first_name, stored_pwd = row

    # NOTE: this compares plaintext since your table currently stores plaintext.
    # (We can switch to bcrypt later if you want.)
    if pwd != stored_pwd:
        return jsonify({"success": False, "error": "Invalid email or password"})

    return jsonify({"success": True, "first_name": first_name})

def open_browser():
    webbrowser.open("http://127.0.0.1:5000/")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)

import os, re, time
import jwt
import psycopg2
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

DB = dict(
    host=os.getenv("DB_HOST", "db"),
    dbname=os.getenv("DB_NAME", "library"),
    user=os.getenv("DB_USER", "library"),
    password=os.getenv("DB_PASSWORD", "library"),
)
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_conn():
    return psycopg2.connect(**DB)


def init_db():
    for _ in range(30):  # wait for the database to be ready
        try:
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )""")
            return
        except psycopg2.OperationalError:
            time.sleep(2)
    raise RuntimeError("Database not reachable")


def make_token(user_id, name, email):
    payload = {
        "sub": user_id, "name": name, "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=2),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def err(msg, code):
    return jsonify({"error": msg}), code


@app.post("/api/auth/register")
def register():
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    email = (d.get("email") or "").strip().lower()
    password = d.get("password") or ""

    if not name or not email or not password:
        return err("Name, email and password are required", 400)
    if not EMAIL_RE.match(email):
        return err("Invalid email format", 400)
    if len(password) < 6:
        return err("Password must be at least 6 characters", 400)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            return err("Email is already registered", 409)
        cur.execute(
            "INSERT INTO users (name,email,password_hash) VALUES (%s,%s,%s) RETURNING id",
            (name, email, generate_password_hash(password)),
        )
        uid = cur.fetchone()[0]
    return jsonify({"message": "Registered successfully",
                    "token": make_token(uid, name, email),
                    "user": {"id": uid, "name": name, "email": email}}), 201


@app.post("/api/auth/login")
def login():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    password = d.get("password") or ""
    if not email or not password:
        return err("Email and password are required", 400)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id,name,password_hash FROM users WHERE email=%s", (email,))
        row = cur.fetchone()
    if not row or not check_password_hash(row[2], password):
        return err("Invalid email or password", 401)
    return jsonify({"token": make_token(row[0], row[1], email),
                    "user": {"id": row[0], "name": row[1], "email": email}})


@app.get("/api/auth/me")
def me():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return err("Missing token", 401)
    try:
        p = jwt.decode(auth[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return err("Invalid or expired token", 401)
    return jsonify({"user": {"id": p["sub"], "name": p["name"], "email": p["email"]}})


@app.post("/api/auth/logout")
def logout():
    # JWT is stateless: the client deletes the token.
    return jsonify({"message": "Logged out"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


init_db()

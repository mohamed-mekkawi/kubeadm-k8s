
import os
import time

import jwt
import psycopg2
from flask import Flask, jsonify, request


app = Flask(__name__)

DB = {
    "host": os.getenv("DB_HOST", "db"),
    "dbname": os.getenv("DB_NAME", "library"),
    "user": os.getenv("DB_USER", "library"),
    "password": os.getenv("DB_PASSWORD", "library"),
}

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")

SEED = [
    ("Clean Code", "Robert C. Martin", "Programming", 45.00, 5),
    ("The Pragmatic Programmer", "Andrew Hunt", "Programming", 42.50, 4),
    ("The Phoenix Project", "Gene Kim", "DevOps", 30.00, 3),
    ("The DevOps Handbook", "Gene Kim", "DevOps", 38.00, 6),
    (
        "Designing Data-Intensive Applications",
        "Martin Kleppmann",
        "Databases",
        55.00,
        2,
    ),
    ("Atomic Habits", "James Clear", "Self-help", 20.00, 8),
    ("Sapiens", "Yuval Noah Harari", "History", 25.00, 4),
    ("1984", "George Orwell", "Fiction", 15.00, 1),
]


def get_conn():
    return psycopg2.connect(**DB)


def init_db():
    for _ in range(30):
        try:
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS books (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        category TEXT NOT NULL,
                        cover_image TEXT,
                        price NUMERIC(8,2) NOT NULL,
                        total_quantity INT NOT NULL,
                        available_quantity INT NOT NULL
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id SERIAL PRIMARY KEY,
                        user_id INT NOT NULL,
                        book_id INT NOT NULL REFERENCES books(id),
                        type TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        returned_at TIMESTAMPTZ
                    )
                """)

                cur.execute("SELECT COUNT(*) FROM books")

                if cur.fetchone()[0] == 0:
                    for title, author, category, price, quantity in SEED:
                        cur.execute(
                            """
                            INSERT INTO books (
                                title,
                                author,
                                category,
                                cover_image,
                                price,
                                total_quantity,
                                available_quantity
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                title,
                                author,
                                category,
                                "",
                                price,
                                quantity,
                                quantity,
                            ),
                        )

            return

        except psycopg2.OperationalError:
            time.sleep(2)

    raise RuntimeError("Database not reachable")


def err(msg, code):
    return jsonify({"error": msg}), code


def current_user():
    auth = request.headers.get("Authorization", "")

    if not auth.startswith("Bearer "):
        return None

    try:
        return jwt.decode(
            auth[7:],
            JWT_SECRET,
            algorithms=["HS256"],
        )["sub"]

    except jwt.PyJWTError:
        return None


COLS = (
    "id,title,author,category,cover_image,"
    "price,total_quantity,available_quantity"
)


def row_to_book(r):
    return {
        "id": r[0],
        "title": r[1],
        "author": r[2],
        "category": r[3],
        "cover_image": r[4],
        "price": float(r[5]),
        "total_quantity": r[6],
        "available_quantity": r[7],
        "can_borrow": r[7] > 0,
    }


@app.get("/api/books")
def list_books():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT {COLS} FROM books ORDER BY id")
        return jsonify([row_to_book(r) for r in cur.fetchall()])


def take_book(book_id, kind):
    uid = current_user()

    if uid is None:
        return err("Please login first", 401)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {COLS} FROM books WHERE id=%s FOR UPDATE",
            (book_id,),
        )

        row = cur.fetchone()

        if not row:
            return err("Book not found", 404)

        if row[7] <= 0:
            return err("No copies available", 409)

        if kind == "buy":
            cur.execute(
                """
                UPDATE books
                SET total_quantity = total_quantity - 1,
                    available_quantity = available_quantity - 1
                WHERE id = %s
                """,
                (book_id,),
            )
        else:
            cur.execute(
                """
                UPDATE books
                SET available_quantity = available_quantity - 1
                WHERE id = %s
                """,
                (book_id,),
            )

        cur.execute(
            """
            INSERT INTO transactions (user_id, book_id, type)
            VALUES (%s, %s, %s)
            """,
            (uid, book_id, kind),
        )

        cur.execute(
            f"SELECT {COLS} FROM books WHERE id=%s",
            (book_id,),
        )

        book = row_to_book(cur.fetchone())

    message = (
        "Purchase successful"
        if kind == "buy"
        else "Borrowed successfully"
    )

    return jsonify({"message": message, "book": book})


@app.post("/api/books/<int:book_id>/buy")
def buy(book_id):
    return take_book(book_id, "buy")


@app.post("/api/books/<int:book_id>/borrow")
def borrow(book_id):
    return take_book(book_id, "borrow")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


init_db()

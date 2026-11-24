
import os
import sqlite3
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY", "td-lost-found-development-key"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "GantiPassword123!")


# DATABASE
def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            report_type TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            report_date TEXT NOT NULL,
            contact TEXT NOT NULL,
            status TEXT DEFAULT 'Menunggu'
        )
    """)

    connection.commit()
    connection.close()


init_db()


# ADMIN PROTECTION
def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return function(*args, **kwargs)
    return wrapper


# HOME PAGE
@app.route("/")
def index():
    connection = get_db()

    lost_count = connection.execute(
        "SELECT COUNT(*) FROM items WHERE report_type = 'Hilang'"
    ).fetchone()[0]

    found_count = connection.execute(
        "SELECT COUNT(*) FROM items WHERE report_type = 'Ditemukan'"
    ).fetchone()[0]

    latest_items = connection.execute(
        "SELECT * FROM items ORDER BY id DESC LIMIT 6"
    ).fetchall()

    connection.close()

    return render_template(
        "index.html",
        lost_count=lost_count,
        found_count=found_count,
        latest_items=latest_items
    )


# REPORT LOST OR FOUND ITEM
@app.route("/report/<report_type>", methods=["GET", "POST"])
def report(report_type):
    if report_type not in ["Hilang", "Ditemukan"]:
        abort(404)

    if request.method == "POST":
        item_name = request.form.get("item_name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        report_date = request.form.get("report_date", "").strip()
        contact = request.form.get("contact", "").strip()

        if not all([
            item_name, category, description,
            location, report_date, contact
        ]):
            flash("Semua kolom wajib diisi.", "error")
            return render_template(
                "report.html", report_type=report_type
            )

        connection = get_db()

        connection.execute("""
            INSERT INTO items
            (item_name, category, report_type, description,
             location, report_date, contact)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            item_name, category, report_type, description,
            location, report_date, contact
        ))

        connection.commit()
        connection.close()

        flash("Laporan berhasil disimpan!", "success")
        return redirect(url_for("items"))

    return render_template("report.html", report_type=report_type)


# ITEM LIST AND SEARCH
@app.route("/items")
def items():
    search = request.args.get("search", "").strip()
    report_type = request.args.get("type", "").strip()

    connection = get_db()

    query = "SELECT * FROM items WHERE 1=1"
    parameters = []

    if search:
        query += " AND (item_name LIKE ? OR description LIKE ? OR location LIKE ?)"
        keyword = f"%{search}%"
        parameters.extend([keyword, keyword, keyword])

    if report_type in ["Hilang", "Ditemukan"]:
        query += " AND report_type = ?"
        parameters.append(report_type)

    query += " ORDER BY id DESC"

    all_items = connection.execute(
        query, parameters
    ).fetchall()

    connection.close()

    return render_template(
        "items.html",
        items=all_items,
        search=search,
        selected_type=report_type
    )


# ITEM DETAIL
@app.route("/item/<int:item_id>")
def detail(item_id):
    connection = get_db()

    item = connection.execute(
        "SELECT * FROM items WHERE id = ?",
        (item_id,)
    ).fetchone()

    connection.close()

    if item is None:
        abort(404)

    return render_template("detail.html", item=item)


# ADMIN LOGIN
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))

        flash("Username atau password salah.", "error")

    return render_template("admin.html")


# ADMIN DASHBOARD
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    connection = get_db()

    all_items = connection.execute(
        "SELECT * FROM items ORDER BY id DESC"
    ).fetchall()

    connection.close()

    return render_template(
        "admin_dashboard.html",
        items=all_items
    )


# UPDATE ITEM STATUS
@app.route("/admin/update/<int:item_id>", methods=["POST"])
@admin_required
def update_status(item_id):
    status = request.form.get("status")

    if status not in ["Menunggu", "Diproses", "Selesai"]:
        abort(400)

    connection = get_db()

    connection.execute(
        "UPDATE items SET status = ? WHERE id = ?",
        (status, item_id)
    )

    connection.commit()
    connection.close()

    flash("Status laporan berhasil diperbarui.", "success")
    return redirect(url_for("admin_dashboard"))


# DELETE REPORT
@app.route("/admin/delete/<int:item_id>", methods=["POST"])
@admin_required
def delete_item(item_id):
    connection = get_db()

    connection.execute(
        "DELETE FROM items WHERE id = ?",
        (item_id,)
    )

    connection.commit()
    connection.close()

    flash("Laporan berhasil dihapus.", "success")
    return redirect(url_for("admin_dashboard"))


# ADMIN LOGOUT
@app.route("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)

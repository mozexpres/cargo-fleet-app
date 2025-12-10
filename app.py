import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__, template_folder=".")

# 🔐 SCHIMBĂ ASTA (obligatoriu)
app.secret_key = "schimba_asta_cu_ceva_foarte_secret"

# 🔐 LOGIN (un singur utilizator)
USERNAME = "admin"
PASSWORD = "parola123"

DB_NAME = "database.db"

# ---------------- DB ----------------

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS curse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loc_inc TEXT NOT NULL,
            loc_desc TEXT NOT NULL,
            data_inc TEXT NOT NULL,
            data_desc TEXT NOT NULL,
            paleti TEXT NOT NULL,
            nr_paleti INTEGER,
            pret REAL NOT NULL,
            firma TEXT NOT NULL,
            nr_auto TEXT NOT NULL,
            status TEXT NOT NULL,
            obs TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()

# ---------------- LOGIN REQUIRED ----------------

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------- ROUTES ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username", "")
        pwd = request.form.get("password", "")
        if user == USERNAME and pwd == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("lista_curse"))
        else:
            return render_template("login.html", error="Utilizator sau parolă greșite.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def lista_curse():
    conn = get_db()
    cur = conn.cursor()

    status = request.args.get("status", "")
    d1 = request.args.get("d1", "")
    d2 = request.args.get("d2", "")

    query = "SELECT * FROM curse WHERE 1=1"
    params = []

    if status and status != "Toate":
        query += " AND status=?"
        params.append(status)

    if d1 and d2:
        query += " AND substr(data_inc,1,10) BETWEEN ? AND ?"
        params.extend([d1, d2])

    query += " ORDER BY data_inc DESC"

    cur.execute(query, params)
    curse = cur.fetchall()

    total = sum(c["pret"] for c in curse)

    conn.close()
    return render_template(
        "curse.html",
        curse=curse,
        total=total,
        status_curent=status,
        d1=d1,
        d2=d2
    )


@app.route("/curse/adauga", methods=["GET", "POST"])
@login_required
def adauga_cursa():
    if request.method == "POST":
        f = request.form

        loc_inc = f.get("loc_inc", "").strip()
        loc_desc = f.get("loc_desc", "").strip()
        data_inc = f.get("data_inc", "").strip()
        data_desc = f.get("data_desc", "").strip()
        paleti = f.get("paleti", "Nu")
        nr_paleti = f.get("nr_paleti", "0")
        pret = f.get("pret", "0")
        firma = f.get("firma", "").strip()
        nr_auto = f.get("nr_auto", "").strip()
        status = f.get("status", "Neplanificată")
        obs = f.get("obs", "").strip()

        if not (loc_inc and loc_desc and data_inc and data_desc and pret and firma and nr_auto):
            return "Câmpuri obligatorii lipsă", 400

        try:
            pret_val = float(pret.replace(",", "."))
        except ValueError:
            return "Preț invalid", 400

        try:
            nr_paleti_val = int(nr_paleti)
        except ValueError:
            nr_paleti_val = 0

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO curse
            (loc_inc, loc_desc, data_inc, data_desc, paleti, nr_paleti, pret, firma, nr_auto, status, obs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            loc_inc, loc_desc, data_inc, data_desc,
            paleti, nr_paleti_val, pret_val,
            firma, nr_auto, status, obs
        ))
        conn.commit()
        conn.close()

        return redirect(url_for("lista_curse"))

    return render_template("form_cursa.html", cursa=None)


@app.route("/curse/<int:cursa_id>/edit", methods=["GET", "POST"])
@login_required
def editeaza_cursa(cursa_id):
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        f = request.form

        loc_inc = f.get("loc_inc", "").strip()
        loc_desc = f.get("loc_desc", "").strip()
        data_inc = f.get("data_inc", "").strip()
        data_desc = f.get("data_desc", "").strip()
        paleti = f.get("paleti", "Nu")
        nr_paleti = f.get("nr_paleti", "0")
        pret = f.get("pret", "0")
        firma = f.get("firma", "").strip()
        nr_auto = f.get("nr_auto", "").strip()
        status = f.get("status", "Neplanificată")
        obs = f.get("obs", "").strip()

        try:
            pret_val = float(pret.replace(",", "."))
        except ValueError:
            conn.close()
            return "Preț invalid", 400

        try:
            nr_paleti_val = int(nr_paleti)
        except ValueError:
            nr_paleti_val = 0

        cur.execute("""
            UPDATE curse SET
            loc_inc=?, loc_desc=?, data_inc=?, data_desc=?,
            paleti=?, nr_paleti=?, pret=?, firma=?, nr_auto=?, status=?, obs=?
            WHERE id=?
        """, (
            loc_inc, loc_desc, data_inc, data_desc,
            paleti, nr_paleti_val, pret_val,
            firma, nr_auto, status, obs, cursa_id
        ))
        conn.commit()
        conn.close()
        return redirect(url_for("lista_curse"))

    cur.execute("SELECT * FROM curse WHERE id=?", (cursa_id,))
    cursa = cur.fetchone()
    conn.close()

    if not cursa:
        return "Cursa nu există", 404

    return render_template("form_cursa.html", cursa=cursa)


@app.route("/curse/<int:cursa_id>/sterge")
@login_required
def sterge_cursa(cursa_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM curse WHERE id=?", (cursa_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("lista_curse"))


# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True

    )

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import sqlite3
import os
import datetime
import csv
import io
import random

app = Flask(__name__)
app.secret_key = "cambia_esto_por_algo_mas_seguro"

DB_NAME = "domotica.db"

# Usuarios y roles (simple, hardcodeado)
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"},
}

# Estado de dispositivos (domótica)
devices = {
    "luz_living": False,
    "luz_cocina": False,
    "puerta_principal": False,
    "alarma": False,
}

# Estado de sensores simulados
sensors = {
    "temperatura": 22.0,
    "movimiento": False,
    "puerta_abierta": False,
    "humo": False,
}

def init_db():
    """Crea la base de datos si no existe"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user TEXT NOT NULL,
            action TEXT NOT NULL,
            device TEXT,
            extra TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_event(user, action, device=None, extra=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO events (timestamp, user, action, device, extra) VALUES (?, ?, ?, ?, ?)",
        (datetime.datetime.now().isoformat(timespec="seconds"), user, action, device, extra),
    )
    conn.commit()
    conn.close()

def get_last_events(limit=50):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT timestamp, user, action, device, extra FROM events ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = c.fetchall()
    conn.close()
    return rows

def simulate_sensors():
    """Simula cambios simples en los sensores cada vez que se consulta el estado"""
    # temperatura entre 18 y 30 grados
    sensors["temperatura"] = round(random.uniform(18, 30), 1)
    # movimiento aleatorio (10% de prob)
    sensors["movimiento"] = random.random() < 0.1
    # puerta abierta (según estado de puerta_principal)
    sensors["puerta_abierta"] = devices["puerta_principal"]
    # humo aleatorio (5% de prob)
    sensors["humo"] = random.random() < 0.05

def setup():
    init_db()
    log_event("system", "Servidor iniciado")


def login_required(f):
    """Decorador para requerir login"""
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapper

def admin_required(f):
    """Decorador para requerir rol admin"""
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            return "No autorizado (se requiere rol admin)", 403
        return f(*args, **kwargs)

    return wrapper

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = USERS.get(username)
        if user and user["password"] == password:
            session["username"] = username
            session["role"] = user["role"]
            log_event(username, "login")
            return redirect(url_for("index"))
        else:
            error = "Usuario o contraseña incorrectos"
            return render_template("login.html", error=error)
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    username = session.get("username")
    log_event(username, "logout")
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    return render_template("index.html", devices=devices, sensors=sensors, role=session.get("role"))

@app.route("/api/state")
@login_required
def api_state():
    simulate_sensors()
    events = get_last_events(20)
    events_list = [
        {
            "timestamp": e[0],
            "user": e[1],
            "action": e[2],
            "device": e[3],
            "extra": e[4],
        }
        for e in events
    ]
    return jsonify(
        {
            "devices": devices,
            "sensors": sensors,
            "events": events_list,
            "user": session.get("username"),
            "role": session.get("role"),
        }
    )

@app.route("/api/toggle", methods=["POST"])
@login_required
def api_toggle():
    data = request.get_json()
    device = data.get("device")
    state = data.get("state")
    if device not in devices:
        return jsonify({"error": "Dispositivo inválido"}), 400
    devices[device] = bool(state)
    log_event(
        session.get("username"),
        f"toggle_{'ON' if state else 'OFF'}",
        device=device,
    )
    return jsonify({"ok": True, "devices": devices})

@app.route("/api/mode", methods=["POST"])
@login_required
def api_mode():
    data = request.get_json()
    mode = data.get("mode")
    if mode == "seguridad":
        devices["alarma"] = True
        devices["luz_living"] = True
        devices["luz_cocina"] = True
        action = "modo_seguridad"
        extra = "Alarma activada, luces encendidas"
    elif mode == "ahorro":
        devices["alarma"] = False
        devices["luz_living"] = False
        devices["luz_cocina"] = False
        action = "modo_ahorro"
        extra = "Luces apagadas, alarma desactivada"
    else:
        return jsonify({"error": "Modo inválido"}), 400
    log_event(session.get("username"), action, extra=extra)
    return jsonify({"ok": True, "devices": devices})

@app.route("/api/events")
@login_required
def api_events():
    limit = int(request.args.get("limit", 50))
    events = get_last_events(limit)
    events_list = [
        {
            "timestamp": e[0],
            "user": e[1],
            "action": e[2],
            "device": e[3],
            "extra": e[4],
        }
        for e in events
    ]
    return jsonify({"events": events_list})

@app.route("/api/events/export")
@login_required
def api_events_export():
    events = get_last_events(1000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "user", "action", "device", "extra"])
    for e in events:
        writer.writerow(e)
    output.seek(0)
    return send_file(
        io.BytesIO(output.read().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="eventos_domotica.csv",
    )

@app.route("/api/admin/add_device", methods=["POST"])
@admin_required
def api_admin_add_device():
    data = request.get_json()
    name = data.get("name")
    if not name:
        return jsonify({"error": "Nombre requerido"}), 400
    if name in devices:
        return jsonify({"error": "El dispositivo ya existe"}), 400
    devices[name] = False
    log_event(session.get("username"), "add_device", device=name)
    return jsonify({"ok": True, "devices": devices})

@app.route("/api/admin/delete_device", methods=["POST"])
@admin_required
def api_admin_delete_device():
    data = request.get_json()
    name = data.get("name")
    if not name:
        return jsonify({"error": "Nombre requerido"}), 400
    if name not in devices:
        return jsonify({"error": "El dispositivo no existe"}), 400

    # Eliminar dispositivo
    del devices[name]

    # Registrar en historial
    log_event(session.get("username"), "delete_device", device=name)

    return jsonify({"ok": True, "devices": devices})


if __name__ == "__main__":
    setup()  # Ejecutamos la creación de la BD antes de levantar el server
    app.run(host="0.0.0.0", port=8080, debug=True)


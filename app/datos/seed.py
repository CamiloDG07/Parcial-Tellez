"""Datos de demostración. Uso: `python -m app.datos.seed` (o `--reset` para recrear la BD)."""
from __future__ import annotations

import json
import os
import random
import sys
from datetime import date, datetime, timedelta

from app import config
from app.datos.conexion import ConexionBD

from app.seguridad import hashear_password

CLIENTE = ("Camila Demo", "cliente@demo.com", "Cliente123!")
ADMINS = [
    ("Admin Demo", "admin@demo.com", "Admin123!"),
    ("Admin Dos", "admin2@demo.com", "Admin123!"),
    ("Admin Tres", "admin3@demo.com", "Admin123!"),
    ("Admin Cuatro", "admin4@demo.com", "Admin123!"),
    ("Admin Cinco", "admin5@demo.com", "Admin123!"),
]

# nombre, dirección, ciudad, cocina, descripción, mesas [(capacidad, ubicación)], horario {días: (apertura, cierre)}
RESTAURANTES = [
    ("Freddy's Slice Palace", "Cra 7 #45-12", "Bogotá", "Pizzería",
     "Pizzas de horno de leña bajo las luces de escenario. Pasillos oscuros, mesas de fiesta.",
     [(2, "Salón"), (2, "Salón"), (4, "Salón"), (4, "Escenario"), (6, "Escenario"), (8, "Sala de fiestas")],
     {range(0, 7): ("12:00", "23:00")}),
    ("La Cocina del Turno Noche", "Cl 85 #14-30", "Bogotá", "Colombiana",
     "Cocina criolla servida de madrugada: ajiaco, bandeja paisa y sancocho.",
     [(2, "Barra"), (3, "Ventana"), (4, "Ventana"), (4, "Salón"), (6, "Salón")],
     {range(1, 7): ("11:00", "22:00")}),
    ("Pasillo Este Sushi", "Av 6N #23-50", "Cali", "Japonesa",
     "Sushi y ramen en un corredor de neón. Reserva para ver el cuarto de control.",
     [(2, "Barra"), (2, "Barra"), (4, "Salón"), (5, "Reservado")],
     {range(2, 7): ("13:00", "23:00")}),
    ("Cámara 04 Parrilla", "Cra 43A #7-15", "Medellín", "Parrilla",
     "Cortes a las brasas y carta de vinos con vistas a la sala de monitores.",
     [(2, "Terraza"), (4, "Terraza"), (4, "Salón"), (6, "Salón"), (10, "Salón privado")],
     {range(0, 7): ("12:00", "22:30")}),
    ("Backstage Pasta & Vino", "Cl 10 #4-21", "Cali", "Italiana",
     "Pastas frescas detrás del telón. Cortinas rojas, velas y música en vivo.",
     [(2, "Telón"), (2, "Telón"), (4, "Salón"), (4, "Salón"), (8, "Mesa larga")],
     {range(0, 7): ("12:30", "22:00")}),
]


CARTA_JSON = config.BASE_DIR.parent / "carta_demo.json"
RESTAURANTES_CON_CARTA = (1, 5)          # los dos restaurantes de cocina italiana usan la carta demo
INVITADOS = [("Invitado Uno", "invitado1@demo.com"), ("Invitado Dos", "invitado2@demo.com"),
             ("Invitado Tres", "invitado3@demo.com")]


def _sembrar_carta(con) -> None:
    """Carga `carta_demo.json` (menú de PIZZATRO, JuanPZ28, con su autorización): precios en COP enteros."""
    carta = json.loads(CARTA_JSON.read_text(encoding="utf-8"))
    for rid in RESTAURANTES_CON_CARTA:
        for categoria in carta["categorias"]:
            cur = con.execute("INSERT INTO categoria (restaurante_id, nombre, orden) VALUES (?,?,?)",
                              (rid, categoria["nombre"], categoria["orden"]))
            for p in categoria["productos"]:
                con.execute(
                    "INSERT INTO producto (restaurante_id, categoria_id, nombre, descripcion, precio_cop, imagen, disponible) "
                    "VALUES (?,?,?,?,?,?,1)",
                    (rid, cur.lastrowid, p["nombre"], p["descripcion"], int(p["precio_cop"]), p["slug_foto"] + ".jpg"))


def _sembrar_historial(con) -> None:
    """Reservas de los últimos 14 días y de la próxima semana en el restaurante 1, para que el panel tenga datos."""
    azar = random.Random(42)
    hash_demo = hashear_password("Invitado123!")
    ids = []
    for nombre, email in INVITADOS:
        ids.append(con.execute("INSERT INTO usuario (nombre, email, password_hash, rol) VALUES (?,?,?, 'cliente')",
                               (nombre, email, hash_demo)).lastrowid)
    mesas = [(f[0], f[1]) for f in con.execute("SELECT id, capacidad FROM mesa WHERE restaurante_id = 1")]
    productos = [(f[0], f[1]) for f in con.execute("SELECT id, precio_cop FROM producto WHERE restaurante_id = 1")]
    hoy = date.today()
    for delta in range(-13, 8):
        dia = hoy + timedelta(days=delta)
        combos = [(m, h) for m in mesas for h in ("12:00", "14:00", "16:00", "18:00", "20:00")]
        for (mesa_id, cap), hora in azar.sample(combos, azar.randint(1, 5)):
            estado = "CONFIRMADA" if delta < 0 else azar.choice(["PENDIENTE", "CONFIRMADA"])
            rid = con.execute(
                "INSERT INTO reserva (usuario_id, restaurante_id, mesa_id, fecha, hora, num_personas, estado, notas, creado_en) "
                "VALUES (?,1,?,?,?,?,?,'',?)",
                (azar.choice(ids), mesa_id, dia.isoformat(), hora, azar.randint(1, cap), estado,
                 datetime.now().isoformat(timespec="seconds"))).lastrowid
            for pid, precio in azar.sample(productos, azar.randint(1, 4)):
                con.execute("INSERT INTO reserva_item (reserva_id, producto_id, cantidad, precio_unitario_cop) VALUES (?,?,?,?)",
                            (rid, pid, azar.randint(1, 3), precio))


def sembrar(reiniciar: bool = False, historial: bool = False) -> None:
    con_bd = ConexionBD()
    if reiniciar and os.path.exists(con_bd.ruta):
        os.remove(con_bd.ruta)
    con_bd.inicializar_esquema()
    with con_bd.sesion() as con:
        if con.execute("SELECT COUNT(*) FROM usuario").fetchone()[0]:
            print("La base de datos ya tiene datos; usa --reset para recrearla.")
            return
        nombre, email, pw = CLIENTE
        con.execute("INSERT INTO usuario (nombre, email, password_hash, rol) VALUES (?,?,?, 'cliente')",
                    (nombre, email, hashear_password(pw)))
        admin_ids = []
        for nombre, email, pw in ADMINS:
            cur = con.execute("INSERT INTO usuario (nombre, email, password_hash, rol) VALUES (?,?,?, 'administrador')",
                              (nombre, email, hashear_password(pw)))
            admin_ids.append(cur.lastrowid)
        for admin_id, (nombre, direccion, ciudad, cocina, desc, mesas, horario) in zip(admin_ids, RESTAURANTES):
            cur = con.execute(
                "INSERT INTO restaurante (nombre, direccion, ciudad, tipo_cocina, descripcion, admin_id) VALUES (?,?,?,?,?,?)",
                (nombre, direccion, ciudad, cocina, desc, admin_id))
            rid = cur.lastrowid
            for numero, (cap, ubic) in enumerate(mesas, start=1):
                con.execute("INSERT INTO mesa (restaurante_id, numero, capacidad, ubicacion, activa) VALUES (?,?,?,?,1)",
                            (rid, numero, cap, ubic))
            for dias, (ap, ci) in horario.items():
                for dia in dias:
                    con.execute("INSERT INTO horario (restaurante_id, dia_semana, hora_apertura, hora_cierre) VALUES (?,?,?,?)",
                                (rid, dia, ap, ci))
        _sembrar_carta(con)
        if historial:
            _sembrar_historial(con)
    print(f"Base de datos sembrada en {con_bd.ruta}")


if __name__ == "__main__":
    sembrar(reiniciar="--reset" in sys.argv, historial="--sin-historial" not in sys.argv)

"""Datos de demostración. Uso: `python -m app.datos.seed` (o `--reset` para recrear la BD)."""
from __future__ import annotations

import os
import sys

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


def sembrar(reiniciar: bool = False) -> None:
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
    print(f"Base de datos sembrada en {con_bd.ruta}")


if __name__ == "__main__":
    sembrar(reiniciar="--reset" in sys.argv)

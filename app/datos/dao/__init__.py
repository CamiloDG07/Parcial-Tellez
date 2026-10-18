"""Capa de acceso a datos: DAO."""
from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, TypeVar

from app.datos.conexion import ConexionBD
from app.datos.modelos import (Categoria, Horario, Mesa, Producto, Reserva, ReservaItem,
                               Restaurante, Usuario)

T = TypeVar("T")


class BaseDAO(ABC, Generic[T]):
    """DAO genérico: CRUD común. Las subclases definen tabla, columnas y el mapeo fila→modelo.

    Los nombres de tabla y columnas son constantes de clase (nunca datos del usuario);
    todos los valores viajan como parámetros `?`.
    """

    tabla: str
    columnas: tuple[str, ...]          # columnas sin `id`

    @abstractmethod
    def _desde_fila(self, fila: sqlite3.Row) -> T: ...

    def _valores(self, entidad: T) -> tuple[Any, ...]:
        return tuple(getattr(entidad, c) for c in self.columnas)

    def obtener_por_id(self, id_: int) -> T | None:
        with ConexionBD().sesion() as con:
            fila = con.execute(f"SELECT * FROM {self.tabla} WHERE id = ?", (id_,)).fetchone()
        return self._desde_fila(fila) if fila else None

    def listar(self) -> list[T]:
        with ConexionBD().sesion() as con:
            filas = con.execute(f"SELECT * FROM {self.tabla} ORDER BY id").fetchall()
        return [self._desde_fila(f) for f in filas]

    def insertar(self, entidad: T) -> int:
        marcas = ", ".join("?" for _ in self.columnas)
        with ConexionBD().sesion() as con:
            cur = con.execute(
                f"INSERT INTO {self.tabla} ({', '.join(self.columnas)}) VALUES ({marcas})",
                self._valores(entidad),
            )
            return int(cur.lastrowid)

    def actualizar(self, entidad: T) -> None:
        asignaciones = ", ".join(f"{c} = ?" for c in self.columnas)
        with ConexionBD().sesion() as con:
            con.execute(
                f"UPDATE {self.tabla} SET {asignaciones} WHERE id = ?",
                (*self._valores(entidad), entidad.id),  # type: ignore[attr-defined]
            )

    def eliminar(self, id_: int) -> None:
        with ConexionBD().sesion() as con:
            con.execute(f"DELETE FROM {self.tabla} WHERE id = ?", (id_,))


class UsuarioDAO(BaseDAO[Usuario]):
    """DAO de `usuario`. Reconstruye las filas con una fábrica inyectada (Factory Method),
    así la capa de datos no importa la capa de negocio."""

    tabla = "usuario"
    columnas = ("nombre", "email", "password_hash", "rol")

    def __init__(self, fabrica: Callable[[str, dict], Usuario]) -> None:
        self._fabrica = fabrica

    def _desde_fila(self, fila: sqlite3.Row) -> Usuario:
        return self._fabrica(fila["rol"], dict(fila))

    def obtener_por_email(self, email: str) -> Usuario | None:
        with ConexionBD().sesion() as con:
            fila = con.execute("SELECT * FROM usuario WHERE email = ?", (email.strip().lower(),)).fetchone()
        return self._desde_fila(fila) if fila else None


class RestauranteDAO(BaseDAO[Restaurante]):
    tabla = "restaurante"
    columnas = ("nombre", "direccion", "ciudad", "tipo_cocina", "descripcion", "admin_id")

    def _desde_fila(self, fila: sqlite3.Row) -> Restaurante:
        return Restaurante(**dict(fila))

    def buscar(self, nombre: str = "", tipo_cocina: str = "", ciudad: str = "") -> list[Restaurante]:
        with ConexionBD().sesion() as con:
            filas = con.execute(
                "SELECT * FROM restaurante WHERE nombre LIKE ? AND tipo_cocina LIKE ? AND ciudad LIKE ? ORDER BY nombre",
                (f"%{nombre}%", f"%{tipo_cocina}%", f"%{ciudad}%"),
            ).fetchall()
        return [self._desde_fila(f) for f in filas]

    def obtener_por_admin(self, admin_id: int) -> Restaurante | None:
        with ConexionBD().sesion() as con:
            fila = con.execute("SELECT * FROM restaurante WHERE admin_id = ?", (admin_id,)).fetchone()
        return self._desde_fila(fila) if fila else None

    def listar_cocinas_y_ciudades(self) -> tuple[list[str], list[str]]:
        with ConexionBD().sesion() as con:
            cocinas = [f[0] for f in con.execute("SELECT DISTINCT tipo_cocina FROM restaurante ORDER BY 1")]
            ciudades = [f[0] for f in con.execute("SELECT DISTINCT ciudad FROM restaurante ORDER BY 1")]
        return cocinas, ciudades


class MesaDAO(BaseDAO[Mesa]):
    tabla = "mesa"
    columnas = ("restaurante_id", "numero", "capacidad", "ubicacion", "activa")

    def _desde_fila(self, fila: sqlite3.Row) -> Mesa:
        datos = dict(fila)
        datos["activa"] = bool(datos["activa"])
        return Mesa(**datos)

    def listar_por_restaurante(self, restaurante_id: int) -> list[Mesa]:
        with ConexionBD().sesion() as con:
            filas = con.execute(
                "SELECT * FROM mesa WHERE restaurante_id = ? ORDER BY numero", (restaurante_id,)
            ).fetchall()
        return [self._desde_fila(f) for f in filas]

    def obtener_por_numero(self, restaurante_id: int, numero: int) -> Mesa | None:
        with ConexionBD().sesion() as con:
            fila = con.execute(
                "SELECT * FROM mesa WHERE restaurante_id = ? AND numero = ?", (restaurante_id, numero)
            ).fetchone()
        return self._desde_fila(fila) if fila else None


class HorarioDAO(BaseDAO[Horario]):
    tabla = "horario"
    columnas = ("restaurante_id", "dia_semana", "hora_apertura", "hora_cierre")

    def _desde_fila(self, fila: sqlite3.Row) -> Horario:
        return Horario(**dict(fila))

    def listar_por_restaurante(self, restaurante_id: int) -> list[Horario]:
        with ConexionBD().sesion() as con:
            filas = con.execute(
                "SELECT * FROM horario WHERE restaurante_id = ? ORDER BY dia_semana", (restaurante_id,)
            ).fetchall()
        return [self._desde_fila(f) for f in filas]

    def obtener_por_dia(self, restaurante_id: int, dia_semana: int) -> Horario | None:
        with ConexionBD().sesion() as con:
            fila = con.execute(
                "SELECT * FROM horario WHERE restaurante_id = ? AND dia_semana = ?",
                (restaurante_id, dia_semana),
            ).fetchone()
        return self._desde_fila(fila) if fila else None


class ReservaDAO(BaseDAO[Reserva]):
    tabla = "reserva"
    columnas = ("usuario_id", "restaurante_id", "mesa_id", "fecha", "hora",
                "num_personas", "estado", "notas", "creado_en",
                "subtotal_cop", "descuento_pct", "descuento_cop", "impuesto_pct", "impuesto_cop", "total_pagar_cop")

    def _desde_fila(self, fila: sqlite3.Row) -> Reserva:
        return Reserva(**dict(fila))

    def listar_por_usuario(self, usuario_id: int) -> list[Reserva]:
        with ConexionBD().sesion() as con:
            filas = con.execute(
                "SELECT * FROM reserva WHERE usuario_id = ? ORDER BY fecha DESC, hora DESC", (usuario_id,)
            ).fetchall()
        return [self._desde_fila(f) for f in filas]

    def listar_por_restaurante(self, restaurante_id: int, fecha: str | None = None,
                               estado: str | None = None) -> list[Reserva]:
        sql = "SELECT * FROM reserva WHERE restaurante_id = ?"
        params: list[Any] = [restaurante_id]
        if fecha:
            sql += " AND fecha = ?"
            params.append(fecha)
        if estado:
            sql += " AND estado = ?"
            params.append(estado)
        sql += " ORDER BY fecha DESC, hora DESC"
        with ConexionBD().sesion() as con:
            filas = con.execute(sql, params).fetchall()
        return [self._desde_fila(f) for f in filas]

    def listar_activas_por_mesa_y_fecha(self, mesa_id: int, fecha: str) -> list[Reserva]:
        """Reservas de la mesa ese día, ignorando las canceladas."""
        with ConexionBD().sesion() as con:
            filas = con.execute(
                "SELECT * FROM reserva WHERE mesa_id = ? AND fecha = ? AND estado <> 'CANCELADA'",
                (mesa_id, fecha),
            ).fetchall()
        return [self._desde_fila(f) for f in filas]

    def listar_activas_por_restaurante_y_fecha(self, restaurante_id: int, fecha: str) -> list[Reserva]:
        with ConexionBD().sesion() as con:
            filas = con.execute(
                "SELECT * FROM reserva WHERE restaurante_id = ? AND fecha = ? AND estado <> 'CANCELADA'",
                (restaurante_id, fecha),
            ).fetchall()
        return [self._desde_fila(f) for f in filas]

    def insertar_con_items(self, reserva: Reserva) -> int:
        """Inserta la reserva y su pre-pedido en UNA transacción (o se guarda todo o nada)."""
        marcas = ", ".join("?" for _ in self.columnas)
        with ConexionBD().sesion() as con:
            cur = con.execute(
                f"INSERT INTO reserva ({', '.join(self.columnas)}) VALUES ({marcas})", self._valores(reserva))
            nuevo_id = int(cur.lastrowid)
            con.executemany(
                "INSERT INTO reserva_item (reserva_id, producto_id, cantidad, precio_unitario_cop) VALUES (?,?,?,?)",
                [(nuevo_id, i.producto_id, i.cantidad, i.precio_unitario_cop) for i in reserva.items])
        return nuevo_id

    def insertar_si_libre(self, reserva: Reserva, duracion_min: int) -> int | None:
        """Comprueba el solape y guarda la reserva con su pre-pedido en UNA transacción exclusiva (BEGIN IMMEDIATE).

        Devuelve el id nuevo, o None si la mesa ya está ocupada en esa franja. Como el bloqueo de escritura se toma
        antes de comprobar, dos procesos (o dos conexiones) no pueden reservar la misma mesa a la vez.
        Las horas son «HH:MM»: se pasan a minutos en SQL y dos reservas chocan si distan menos de `duracion_min`."""
        h, m = reserva.hora.split(":")[:2]
        minutos = int(h) * 60 + int(m)
        marcas = ", ".join("?" for _ in self.columnas)
        with ConexionBD().sesion_inmediata() as con:
            choque = con.execute(
                "SELECT 1 FROM reserva WHERE mesa_id = ? AND fecha = ? AND estado <> 'CANCELADA' AND "
                "ABS((CAST(substr(hora, 1, 2) AS INTEGER) * 60 + CAST(substr(hora, 4, 2) AS INTEGER)) - ?) < ? LIMIT 1",
                (reserva.mesa_id, reserva.fecha, minutos, duracion_min)).fetchone()
            if choque:
                return None
            cur = con.execute(
                f"INSERT INTO reserva ({', '.join(self.columnas)}) VALUES ({marcas})", self._valores(reserva))
            nuevo_id = int(cur.lastrowid)
            con.executemany(
                "INSERT INTO reserva_item (reserva_id, producto_id, cantidad, precio_unitario_cop) VALUES (?,?,?,?)",
                [(nuevo_id, i.producto_id, i.cantidad, i.precio_unitario_cop) for i in reserva.items])
        return nuevo_id

    def cambiar_estado(self, reserva_id: int, estado: str) -> None:
        """Al cancelar, el pre-pedido de la reserva se elimina en la misma transacción."""
        with ConexionBD().sesion() as con:
            con.execute("UPDATE reserva SET estado = ? WHERE id = ?", (estado, reserva_id))
            if estado == "CANCELADA":
                con.execute("DELETE FROM reserva_item WHERE reserva_id = ?", (reserva_id,))

    def contar_por_dia(self, restaurante_id: int, desde: str, hasta: str) -> dict[str, int]:
        """Reservas no canceladas por fecha en [desde, hasta]."""
        with ConexionBD().sesion() as con:
            filas = con.execute(
                "SELECT fecha, COUNT(*) FROM reserva WHERE restaurante_id = ? AND fecha BETWEEN ? AND ? "
                "AND estado <> 'CANCELADA' GROUP BY fecha", (restaurante_id, desde, hasta)).fetchall()
        return {f[0]: f[1] for f in filas}


class CategoriaDAO(BaseDAO[Categoria]):
    tabla = "categoria"
    columnas = ("restaurante_id", "nombre", "orden")

    def _desde_fila(self, fila: sqlite3.Row) -> Categoria:
        return Categoria(**dict(fila))

    def listar_por_restaurante(self, restaurante_id: int) -> list[Categoria]:
        with ConexionBD().sesion() as con:
            filas = con.execute(
                "SELECT * FROM categoria WHERE restaurante_id = ? ORDER BY orden, nombre", (restaurante_id,)).fetchall()
        return [self._desde_fila(f) for f in filas]

    def obtener_por_nombre(self, restaurante_id: int, nombre: str) -> Categoria | None:
        with ConexionBD().sesion() as con:
            fila = con.execute("SELECT * FROM categoria WHERE restaurante_id = ? AND nombre = ?",
                               (restaurante_id, nombre)).fetchone()
        return self._desde_fila(fila) if fila else None


class ProductoDAO(BaseDAO[Producto]):
    tabla = "producto"
    columnas = ("restaurante_id", "categoria_id", "nombre", "descripcion", "precio_cop", "imagen", "disponible")

    def _desde_fila(self, fila: sqlite3.Row) -> Producto:
        datos = dict(fila)
        datos["disponible"] = bool(datos["disponible"])
        return Producto(**datos)

    def listar_por_restaurante(self, restaurante_id: int, solo_disponibles: bool = False) -> list[Producto]:
        sql = "SELECT * FROM producto WHERE restaurante_id = ?"
        if solo_disponibles:
            sql += " AND disponible = 1"
        with ConexionBD().sesion() as con:
            filas = con.execute(sql + " ORDER BY categoria_id, id", (restaurante_id,)).fetchall()
        return [self._desde_fila(f) for f in filas]

    def contar_por_categoria(self, categoria_id: int) -> int:
        with ConexionBD().sesion() as con:
            return con.execute("SELECT COUNT(*) FROM producto WHERE categoria_id = ?", (categoria_id,)).fetchone()[0]


class ReservaItemDAO(BaseDAO[ReservaItem]):
    tabla = "reserva_item"
    columnas = ("reserva_id", "producto_id", "cantidad", "precio_unitario_cop")

    def _desde_fila(self, fila: sqlite3.Row) -> ReservaItem:
        return ReservaItem(**dict(fila))

    def listar_por_reserva(self, reserva_id: int) -> list[ReservaItem]:
        with ConexionBD().sesion() as con:
            filas = con.execute("SELECT * FROM reserva_item WHERE reserva_id = ? ORDER BY id", (reserva_id,)).fetchall()
        return [self._desde_fila(f) for f in filas]

    def listar_con_nombre(self, reserva_ids: list[int]) -> dict[int, list[tuple[ReservaItem, str]]]:
        """Pre-pedidos de muchas reservas en UNA consulta (evita el N+1): {reserva_id: [(item, nombre del plato)]}."""
        if not reserva_ids:
            return {}
        marcas = ", ".join("?" for _ in reserva_ids)
        with ConexionBD().sesion() as con:
            filas = con.execute(
                f"SELECT i.*, p.nombre AS nombre_producto FROM reserva_item i "
                f"LEFT JOIN producto p ON p.id = i.producto_id WHERE i.reserva_id IN ({marcas}) ORDER BY i.id",
                list(reserva_ids)).fetchall()
        resultado: dict[int, list[tuple[ReservaItem, str]]] = {}
        for fila in filas:
            datos = dict(fila)
            nombre = datos.pop("nombre_producto") or "(producto eliminado)"
            resultado.setdefault(datos["reserva_id"], []).append((ReservaItem(**datos), nombre))
        return resultado

    def ingresos_estimados(self, restaurante_id: int, desde_fecha: str) -> int:
        """Suma de pre-pedidos de reservas no canceladas desde una fecha."""
        with ConexionBD().sesion() as con:
            return con.execute(
                "SELECT COALESCE(SUM(i.cantidad * i.precio_unitario_cop), 0) FROM reserva_item i "
                "JOIN reserva r ON r.id = i.reserva_id WHERE r.restaurante_id = ? AND r.fecha >= ? "
                "AND r.estado <> 'CANCELADA'", (restaurante_id, desde_fecha)).fetchone()[0]

    def top_productos(self, restaurante_id: int, limite: int = 5) -> list[tuple[str, int]]:
        with ConexionBD().sesion() as con:
            filas = con.execute(
                "SELECT p.nombre, SUM(i.cantidad) AS n FROM reserva_item i JOIN producto p ON p.id = i.producto_id "
                "JOIN reserva r ON r.id = i.reserva_id WHERE r.restaurante_id = ? AND r.estado <> 'CANCELADA' "
                "GROUP BY p.id ORDER BY n DESC, p.nombre LIMIT ?", (restaurante_id, limite)).fetchall()
        return [(f[0], f[1]) for f in filas]

"""Capa de acceso a datos: DAO."""
from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, TypeVar

from app.datos.conexion import ConexionBD
from app.datos.modelos import Horario, Mesa, Reserva, Restaurante, Usuario

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
                "num_personas", "estado", "notas", "creado_en")

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

    def cambiar_estado(self, reserva_id: int, estado: str) -> None:
        with ConexionBD().sesion() as con:
            con.execute("UPDATE reserva SET estado = ? WHERE id = ?", (estado, reserva_id))

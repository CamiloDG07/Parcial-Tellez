"""Acceso a la base de datos: patrón Singleton."""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from typing import Iterator

from app import config


class ConexionBD:
    """PATRÓN CREACIONAL · Singleton (rol: Singleton).

    Garantiza una única instancia que conoce la ruta de la base de datos y
    entrega conexiones SQLite con las claves foráneas activadas. La creación es
    segura entre hilos: bloqueo + doble verificación.
    """

    _instancia: "ConexionBD | None" = None
    _lock = threading.Lock()

    def __new__(cls, ruta: str | None = None) -> "ConexionBD":
        if cls._instancia is None:                 # 1.ª verificación (sin bloqueo)
            with cls._lock:
                if cls._instancia is None:         # 2.ª verificación (con bloqueo)
                    instancia = super().__new__(cls)
                    instancia._ruta = str(ruta or config.DB_PATH)
                    cls._instancia = instancia
        return cls._instancia

    @classmethod
    def reiniciar(cls, ruta: str | None = None) -> "ConexionBD":
        """Descarta la instancia actual (útil en pruebas para apuntar a otra BD)."""
        with cls._lock:
            cls._instancia = None
        return cls(ruta)

    @property
    def ruta(self) -> str:
        return self._ruta

    def conectar(self) -> sqlite3.Connection:
        """Abre una conexión nueva con FK activadas y filas accesibles por nombre."""
        conexion = sqlite3.connect(self._ruta, timeout=10)
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON")
        return conexion

    @contextmanager
    def sesion(self) -> Iterator[sqlite3.Connection]:
        """Conexión con commit/rollback automático y cierre garantizado."""
        conexion = self.conectar()
        try:
            yield conexion
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()

    def inicializar_esquema(self) -> None:
        with self.sesion() as conexion:
            conexion.executescript(config.SCHEMA_PATH.read_text(encoding="utf-8"))

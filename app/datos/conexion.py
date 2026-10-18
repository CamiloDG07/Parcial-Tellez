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
        conexion = sqlite3.connect(self._ruta, timeout=10)      # espera hasta 10 s si otra conexión escribe
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON")
        conexion.execute("PRAGMA journal_mode = WAL")           # lectores y escritor no se bloquean entre sí
        conexion.execute("PRAGMA synchronous = NORMAL")         # seguro con WAL y bastante más rápido
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

    @contextmanager
    def sesion_inmediata(self) -> Iterator[sqlite3.Connection]:
        """Como `sesion`, pero abre la transacción con BEGIN IMMEDIATE: toma el bloqueo de escritura desde el
        principio, así que «comprobar e insertar» es atómico incluso entre varios procesos (no solo hilos)."""
        conexion = self.conectar()
        try:
            conexion.execute("BEGIN IMMEDIATE")
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
            self._migrar_instantanea_cobro(conexion)

    @staticmethod
    def _migrar_instantanea_cobro(conexion: sqlite3.Connection) -> None:
        """Bases creadas antes de guardar el cobro: agrega las columnas y calcula la instantánea de las reservas
        activas con las tasas VIGENTES (aproximación: no hay forma de saber qué tasas regían entonces).
        En una base nueva no hace nada."""
        columnas = {f[1] for f in conexion.execute("PRAGMA table_info(reserva)")}
        if "total_pagar_cop" in columnas:
            return
        for nombre in ("subtotal_cop", "descuento_pct", "descuento_cop", "impuesto_pct", "impuesto_cop"):
            conexion.execute(f"ALTER TABLE reserva ADD COLUMN {nombre} INTEGER NOT NULL DEFAULT 0")
        conexion.execute("ALTER TABLE reserva ADD COLUMN total_pagar_cop INTEGER NOT NULL DEFAULT 0")
        medio = lambda monto, pct: (monto * pct + 50) // 100              # misma regla half-up del Decorator
        for rid, sub in conexion.execute(
                "SELECT r.id, SUM(i.cantidad * i.precio_unitario_cop) FROM reserva r "
                "JOIN reserva_item i ON i.reserva_id = r.id GROUP BY r.id").fetchall():
            pct_d = config.DESCUENTO_PEDIDO_GRANDE_PCT if sub >= config.DESCUENTO_PEDIDO_GRANDE_MINIMO_COP > 0 else 0
            desc = medio(sub, pct_d)
            imp = medio(sub - desc, config.TASA_IMPUESTO_CONSUMO_PCT)
            conexion.execute(
                "UPDATE reserva SET subtotal_cop=?, descuento_pct=?, descuento_cop=?, impuesto_pct=?, impuesto_cop=?, "
                "total_pagar_cop=? WHERE id=?",
                (sub, pct_d, desc, config.TASA_IMPUESTO_CONSUMO_PCT, imp, sub - desc + imp, rid))

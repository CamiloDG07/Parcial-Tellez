"""Fixtures: cada prueba usa una base de datos SQLite temporal ya sembrada."""
from datetime import date, timedelta

import functools

import pytest

from app.datos import seed
from app.datos.conexion import ConexionBD


_HASH_CACHEADO = functools.cache(seed.hashear_password)


@pytest.fixture()
def bd(tmp_path, monkeypatch):
    # scrypt es lento a propósito: en las pruebas se calcula una sola vez por contraseña
    monkeypatch.setattr(seed, "hashear_password", _HASH_CACHEADO)
    ConexionBD.reiniciar(str(tmp_path / "prueba.db"))
    seed.sembrar()
    yield ConexionBD()
    ConexionBD.reiniciar()


def proximo_dia(dia_semana: int | None = None, desde: int = 2) -> str:
    """Fecha ISO futura (por defecto dentro de 2 días, o el siguiente `dia_semana` 0=lunes)."""
    d = date.today() + timedelta(days=desde)
    while dia_semana is not None and d.weekday() != dia_semana:
        d += timedelta(days=1)
    return d.isoformat()

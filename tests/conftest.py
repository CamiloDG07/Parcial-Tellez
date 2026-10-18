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


@pytest.fixture(autouse=True)
def limpiar_subidas():
    """Las pruebas que suben imágenes escriben en static/uploads: se borran al terminar."""
    from app import config
    antes = set(config.UPLOADS_DIR.glob("*")) if config.UPLOADS_DIR.exists() else set()
    yield
    if config.UPLOADS_DIR.exists():
        for f in set(config.UPLOADS_DIR.glob("*")) - antes:
            if f.name != ".gitkeep":
                f.unlink()


@pytest.fixture(autouse=True)
def reiniciar_limitador_de_login():
    """El límite de intentos vive en memoria: cada prueba empieza sin fallos registrados."""
    from app.presentacion.controladores import auth_controller
    auth_controller.limitador_cuenta.reiniciar()
    auth_controller.limitador_ip.reiniciar()
    yield

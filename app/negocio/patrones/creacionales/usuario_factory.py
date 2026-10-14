"""Patrón Factory Method para la creación de usuarios por rol."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.datos.modelos import Administrador, Cliente, Usuario
from app.negocio.excepciones import ReglaNegocioError


class FabricaUsuario(ABC):
    """PATRÓN CREACIONAL · Factory Method (rol: Creator).

    Declara el método fábrica `_instanciar`; `crear` lo usa y normaliza los datos.
    """

    def crear(self, datos: dict) -> Usuario:
        usuario = self._instanciar(datos)
        usuario.email = usuario.email.strip().lower()
        return usuario

    @abstractmethod
    def _instanciar(self, datos: dict) -> Usuario:
        """Método fábrica: cada creador concreto decide la subclase."""


class FabricaCliente(FabricaUsuario):
    """Factory Method · rol: ConcreteCreator (produce `Cliente`)."""

    def _instanciar(self, datos: dict) -> Usuario:
        return Cliente(id=datos.get("id"), nombre=datos["nombre"], email=datos["email"],
                       password_hash=datos.get("password_hash", ""))


class FabricaAdministrador(FabricaUsuario):
    """Factory Method · rol: ConcreteCreator (produce `Administrador`)."""

    def _instanciar(self, datos: dict) -> Usuario:
        return Administrador(id=datos.get("id"), nombre=datos["nombre"], email=datos["email"],
                             password_hash=datos.get("password_hash", ""))


class UsuarioFactory:
    """Punto de entrada: elige el creador concreto según el rol.

    Lo usan `UsuarioDAO` (al reconstruir filas) y `AuthService` (tras el login/registro).
    """

    _creadores: dict[str, FabricaUsuario] = {
        "cliente": FabricaCliente(),
        "administrador": FabricaAdministrador(),
    }

    @classmethod
    def crear(cls, rol: str, datos: dict) -> Usuario:
        creador = cls._creadores.get(rol)
        if creador is None:
            raise ReglaNegocioError(f"Rol desconocido: {rol!r}")
        return creador.crear(datos)

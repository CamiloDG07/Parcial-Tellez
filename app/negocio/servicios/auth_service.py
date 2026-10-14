"""Servicio de autenticación (hash de contraseñas con scrypt de la librería estándar)."""
from __future__ import annotations

import re

from app.datos.dao import UsuarioDAO
from app.datos.modelos import Usuario
from app.seguridad import hashear_password, verificar_password
from app.negocio.excepciones import ReglaNegocioError
from app.negocio.patrones.creacionales.usuario_factory import UsuarioFactory

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class AuthService:
    def __init__(self, usuario_dao: UsuarioDAO) -> None:
        self._dao = usuario_dao

    def autenticar(self, email: str, password: str) -> Usuario:
        """Devuelve el usuario (ya construido por UsuarioFactory dentro del DAO) o falla con mensaje genérico."""
        usuario = self._dao.obtener_por_email(email or "")
        if usuario is None or not verificar_password(password or "", usuario.password_hash):
            raise ReglaNegocioError("Correo o contraseña incorrectos.")
        return usuario

    def obtener(self, usuario_id: int) -> Usuario | None:
        return self._dao.obtener_por_id(usuario_id)

    def registrar(self, nombre: str, email: str, password: str, confirmacion: str) -> Usuario:
        """Registro público: el rol es SIEMPRE `cliente` (los administradores solo existen por seed)."""
        nombre, email = (nombre or "").strip(), (email or "").strip().lower()
        if not 2 <= len(nombre) <= 60:
            raise ReglaNegocioError("El nombre debe tener entre 2 y 60 caracteres.")
        if not _EMAIL.match(email) or len(email) > 120:
            raise ReglaNegocioError("Escribe un correo electrónico válido.")
        if len(password or "") < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            raise ReglaNegocioError("La contraseña debe tener al menos 8 caracteres, con letras y números.")
        if len(password) > 128:
            raise ReglaNegocioError("La contraseña es demasiado larga.")
        if password != confirmacion:
            raise ReglaNegocioError("La confirmación no coincide con la contraseña.")
        if self._dao.obtener_por_email(email):
            raise ReglaNegocioError("Ya existe una cuenta con ese correo.")
        usuario = UsuarioFactory.crear("cliente", {"nombre": nombre, "email": email,
                                                   "password_hash": hashear_password(password)})
        usuario.id = self._dao.insertar(usuario)
        return usuario

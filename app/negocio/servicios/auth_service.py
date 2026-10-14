"""Servicio de autenticación (hash de contraseñas con scrypt de la librería estándar)."""
from __future__ import annotations

from app.datos.dao import UsuarioDAO
from app.datos.modelos import Usuario
from app.seguridad import hashear_password, verificar_password
from app.negocio.excepciones import ReglaNegocioError

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

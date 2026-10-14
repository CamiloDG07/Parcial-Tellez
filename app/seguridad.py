"""Utilidades transversales de seguridad: hash de contraseñas con scrypt (librería estándar)."""
import hashlib
import hmac
import secrets

_N, _R, _P = 2 ** 14, 8, 1


def hashear_password(password: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=sal, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${sal.hex()}${h.hex()}"


def verificar_password(password: str, almacenado: str) -> bool:
    try:
        _, n, r, p, sal, esperado = almacenado.split("$")
        h = hashlib.scrypt(password.encode(), salt=bytes.fromhex(sal), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(h.hex(), esperado)
    except (ValueError, TypeError):
        return False

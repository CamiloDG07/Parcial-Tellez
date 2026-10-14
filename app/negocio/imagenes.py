"""Validación y guardado seguro de imágenes subidas por el administrador."""
from __future__ import annotations

import secrets
from pathlib import Path

from app import config
from app.negocio.excepciones import ReglaNegocioError

MAX_BYTES = 2 * 1024 * 1024


def detectar_tipo(contenido: bytes) -> str | None:
    """Tipo real según los primeros bytes (no se confía en el nombre ni en el Content-Type enviados)."""
    if contenido.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return ".webp"
    return None


def guardar_imagen(contenido: bytes, directorio: Path | None = None) -> str:
    """Guarda la imagen con nombre aleatorio y devuelve ese nombre. Solo JPG/PNG/WebP de hasta 2 MB."""
    if not contenido:
        raise ReglaNegocioError("No se recibió ninguna imagen.")
    if len(contenido) > MAX_BYTES:
        raise ReglaNegocioError("La imagen supera el máximo de 2 MB.")
    extension = detectar_tipo(contenido)
    if extension is None:
        raise ReglaNegocioError("Formato no permitido: usa JPG, PNG o WebP.")
    destino = directorio or config.UPLOADS_DIR
    destino.mkdir(parents=True, exist_ok=True)
    nombre = f"{secrets.token_hex(16)}{extension}"
    (destino / nombre).write_bytes(contenido)
    return nombre

"""Utilidades de la capa de presentación: plantillas, sesión, CSRF, flash y guardas de rol."""
from __future__ import annotations

import secrets
from datetime import date
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import config
from app.datos.modelos import Usuario
from app.dependencias import auth_service, fachada
from app.negocio.excepciones import ReglaNegocioError

DIRECTORIO = Path(__file__).resolve().parent
plantillas = Jinja2Templates(directory=str(DIRECTORIO / "templates"))   # autoescape activo para .html
plantillas.env.globals.update(BRAND_NAME=config.BRAND_NAME, DIAS_SEMANA=config.DIAS_SEMANA)


def _cop(valor: int) -> str:
    """Formato de pesos colombianos: 18000 → $18.000 (sin centavos)."""
    return "$" + f"{int(valor):,}".replace(",", ".")


def _url_imagen(nombre: str) -> str:
    """URL de la foto de un producto: subida por el admin, foto demo o ilustración de reemplazo."""
    if nombre:
        if (config.UPLOADS_DIR / nombre).is_file():
            return f"/static/uploads/{nombre}"
        if (config.PLATOS_DIR / nombre).is_file():
            return f"/static/img/platos/{nombre}"
    return "/static/img/plato-vacio.svg"


plantillas.env.filters["cop"] = _cop
plantillas.env.globals["url_imagen"] = _url_imagen


class RedirigirLogin(Exception):
    """Se requiere iniciar sesión."""


def token_csrf(request: Request) -> str:
    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_urlsafe(32)
    return request.session["csrf"]


async def verificar_csrf(request: Request) -> None:
    """Protección CSRF por token de sesión: campo `csrf_token` del formulario o cabecera X-CSRF-Token."""
    esperado = request.session.get("csrf")
    recibido = request.headers.get("x-csrf-token")
    if recibido is None:
        formulario = await request.form()
        recibido = formulario.get("csrf_token")
    if not esperado or not isinstance(recibido, str) or not secrets.compare_digest(esperado, recibido):
        raise HTTPException(status_code=403, detail="Token CSRF inválido. Recarga la página e inténtalo de nuevo.")


def usuario_actual(request: Request) -> Usuario | None:
    uid = request.session.get("usuario_id")
    return auth_service.obtener(uid) if uid else None


def requiere_usuario(request: Request) -> Usuario:
    usuario = usuario_actual(request)
    if usuario is None:
        raise RedirigirLogin()
    return usuario


def requiere_cliente(request: Request) -> Usuario:
    usuario = requiere_usuario(request)
    if usuario.rol != "cliente":
        raise HTTPException(status_code=403, detail="Esta sección es solo para clientes.")
    return usuario


def requiere_admin(request: Request) -> Usuario:
    usuario = requiere_usuario(request)
    if usuario.rol != "administrador":
        raise HTTPException(status_code=403, detail="Esta sección es solo para administradores.")
    return usuario


def avisar(request: Request, mensaje: str, tipo: str = "ok") -> None:
    # Se reasigna la lista: Starlette no detecta mutaciones in situ de valores anidados de la sesión.
    request.session["flash"] = [*request.session.get("flash", []), {"tipo": tipo, "texto": mensaje}]


def renderizar(request: Request, plantilla: str, estado: int = 200, **contexto):
    usuario = usuario_actual(request)
    proximas = 0
    if usuario is not None and usuario.rol == "cliente":
        hoy = date.today().isoformat()
        proximas = fachada.contar_proximas(usuario, hoy)
    mensajes = request.session.pop("flash", [])
    carrito = fachada.carrito_ver(request.session) if usuario is not None and usuario.rol == "cliente" else None
    contexto.update(request=request, usuario=usuario, csrf_token=token_csrf(request),
                    mensajes=mensajes, reservas_proximas=proximas, carrito=carrito)
    return plantillas.TemplateResponse(request, plantilla, contexto, status_code=estado)


def redirigir(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


def entero(valor: str, campo: str) -> int:
    try:
        return int(str(valor).strip())
    except ValueError:
        raise ReglaNegocioError(f"El campo «{campo}» debe ser un número entero.") from None

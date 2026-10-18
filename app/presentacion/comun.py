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
    valor = int(valor)
    return ("-" if valor < 0 else "") + "$" + f"{abs(valor):,}".replace(",", ".")


def _url_imagen(nombre: str) -> str:
    """URL de la foto de un producto: subida por el admin, foto demo o ilustración de reemplazo."""
    if nombre:
        if (config.UPLOADS_DIR / nombre).is_file():
            return f"/static/uploads/{nombre}"
        if (config.PLATOS_DIR / nombre).is_file():
            return f"/static/img/platos/{nombre}"
    return "/static/img/plato-vacio.svg"


def _srcset_imagen(nombre: str) -> str:
    """`srcset` de la foto de un plato si existe su versión pequeña `<slug>@400.jpg` (si no, cadena vacía)."""
    if nombre and nombre.endswith(".jpg") and not (config.UPLOADS_DIR / nombre).is_file():
        pequena = nombre[:-4] + "@400.jpg"
        if (config.PLATOS_DIR / nombre).is_file() and (config.PLATOS_DIR / pequena).is_file():
            return f"/static/img/platos/{pequena} 400w, /static/img/platos/{nombre} 800w"
    return ""


_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
          "octubre", "noviembre", "diciembre")


def _fecha_larga(texto: str) -> str:
    """'2026-10-15' → 'jueves 15 de octubre de 2026' (sin depender de la configuración regional del sistema)."""
    try:
        d = date.fromisoformat(str(texto))
    except ValueError:
        return str(texto)
    return f"{_DIAS[d.weekday()]} {d.day} de {_MESES[d.month - 1]} de {d.year}"


def _codigo(reserva_id: int) -> str:
    """Código visible de una reserva, derivado de su id (no requiere columna nueva): 60 → MD-0060."""
    return f"MD-{int(reserva_id):04d}"


def clasificar_reservas(filas: list[dict], hoy: str) -> dict[str, list[dict]]:
    """Agrupa las reservas del cliente: próximas (por fecha ascendente), pasadas y canceladas (más recientes primero)."""
    clave = lambda f: (f["reserva"].fecha, f["reserva"].hora)
    proximas = sorted((f for f in filas if f["reserva"].estado != "CANCELADA" and f["reserva"].fecha >= hoy), key=clave)
    pasadas = sorted((f for f in filas if f["reserva"].estado != "CANCELADA" and f["reserva"].fecha < hoy), key=clave, reverse=True)
    canceladas = sorted((f for f in filas if f["reserva"].estado == "CANCELADA"), key=clave, reverse=True)
    return {"proximas": proximas, "pasadas": pasadas, "canceladas": canceladas}


plantillas.env.filters["cop"] = _cop
plantillas.env.filters["fecha_larga"] = _fecha_larga
plantillas.env.filters["codigo"] = _codigo
plantillas.env.globals["url_imagen"] = _url_imagen
plantillas.env.globals["srcset_imagen"] = _srcset_imagen


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

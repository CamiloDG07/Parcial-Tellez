"""Punto de entrada: crea la app, middlewares y routers."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import config
from app.datos.conexion import ConexionBD
from app.negocio.excepciones import NoAutorizadoError, NoEncontradoError
from app.presentacion.comun import RedirigirLogin, redirigir, renderizar
from app.presentacion.controladores import admin_controller, api_controller, auth_controller, cliente_controller

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    ConexionBD().inicializar_esquema()
    yield


app = FastAPI(title=config.BRAND_NAME, lifespan=ciclo_de_vida)
app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, same_site="lax",
                   https_only=False, max_age=60 * 60 * 8, session_cookie="midnight_sesion")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "presentacion" / "static"), name="static")

for router in (auth_controller.router, cliente_controller.router, api_controller.router, admin_controller.router):
    app.include_router(router)


def _error(request: Request, codigo: int, titulo: str, detalle: str):
    return renderizar(request, "error.html", estado=codigo, codigo=codigo, titulo=titulo, detalle=detalle)


@app.exception_handler(RedirigirLogin)
async def _sin_sesion(request: Request, exc: RedirigirLogin):
    return redirigir("/login")


@app.exception_handler(NoAutorizadoError)
async def _no_autorizado(request: Request, exc: NoAutorizadoError):
    return _error(request, 403, "ACCESO DENEGADO", str(exc))


@app.exception_handler(NoEncontradoError)
async def _no_encontrado(request: Request, exc: NoEncontradoError):
    return _error(request, 404, "SEÑAL PERDIDA", str(exc))


@app.exception_handler(HTTPException)
async def _http(request: Request, exc: HTTPException):
    titulos = {403: "ACCESO DENEGADO", 404: "SEÑAL PERDIDA"}
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": str(exc.detail)}, status_code=exc.status_code)
    return _error(request, exc.status_code, titulos.get(exc.status_code, "ERROR"), str(exc.detail))


@app.exception_handler(Exception)
async def _inesperado(request: Request, exc: Exception):
    logging.getLogger("reservas").exception("Error no controlado")
    return _error(request, 500, "FALLO DEL SISTEMA", "Algo salió mal de nuestro lado. Inténtalo de nuevo en un momento.")


@app.exception_handler(RequestValidationError)
async def _validacion(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "Parámetros inválidos."}, status_code=422)
    return _error(request, 422, "DATOS INVÁLIDOS", "Algún dato de la solicitud no tiene el formato esperado.")

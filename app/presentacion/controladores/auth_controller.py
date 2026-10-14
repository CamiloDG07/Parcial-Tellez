"""Controlador de autenticación: /login y /logout."""
from fastapi import APIRouter, Depends, Form, Request

from app.dependencias import auth_service
from app.negocio.excepciones import ReglaNegocioError
from app.presentacion.comun import renderizar, redirigir, usuario_actual, verificar_csrf

router = APIRouter()


@router.get("/login")
def formulario_login(request: Request):
    usuario = usuario_actual(request)
    if usuario:
        return redirigir(usuario.ruta_inicio())
    return renderizar(request, "login.html")


@router.post("/login", dependencies=[Depends(verificar_csrf)])
def iniciar_sesion(request: Request, email: str = Form(""), password: str = Form("")):
    try:
        usuario = auth_service.autenticar(email, password)
    except ReglaNegocioError as error:
        return renderizar(request, "login.html", estado=401, error=str(error), email=email)
    request.session.clear()                       # evita fijación de sesión
    request.session["usuario_id"] = usuario.id
    return redirigir(usuario.ruta_inicio())       # el rol decide el destino (Factory Method: ruta_inicio)


@router.post("/logout", dependencies=[Depends(verificar_csrf)])
def cerrar_sesion(request: Request):
    request.session.clear()
    return redirigir("/login")

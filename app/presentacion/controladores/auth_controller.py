"""Controlador de autenticación: /login y /logout."""
from fastapi import APIRouter, Depends, Form, Request

from app.dependencias import auth_service
from app.negocio.excepciones import ReglaNegocioError
from app.presentacion.comun import renderizar, redirigir, usuario_actual, verificar_csrf
from app.presentacion.limitador import LimitadorIntentos

router = APIRouter()
# 5 fallos con el mismo correo desde la misma IP => 5 min de bloqueo; 20 fallos desde una IP (cualquier correo) => igual.
limitador_cuenta = LimitadorIntentos(max_fallos=5, ventana_s=300, bloqueo_s=300)
limitador_ip = LimitadorIntentos(max_fallos=20, ventana_s=300, bloqueo_s=300)


@router.get("/login")
def formulario_login(request: Request):
    usuario = usuario_actual(request)
    if usuario:
        return redirigir(usuario.ruta_inicio())
    return renderizar(request, "login.html")


@router.post("/login", dependencies=[Depends(verificar_csrf)])
def iniciar_sesion(request: Request, email: str = Form(""), password: str = Form("")):
    ip = request.client.host if request.client else "desconocida"
    clave_cuenta = (ip, (email or "").strip().lower())
    espera = max(limitador_cuenta.segundos_bloqueo(clave_cuenta), limitador_ip.segundos_bloqueo(ip))
    if espera:
        respuesta = renderizar(request, "login.html", estado=429, email=email,
                               error=f"Demasiados intentos fallidos. Inténtalo de nuevo en {-(-espera // 60)} min.")
        respuesta.headers["Retry-After"] = str(espera)
        return respuesta
    try:
        usuario = auth_service.autenticar(email, password)
    except ReglaNegocioError as error:
        limitador_cuenta.registrar_fallo(clave_cuenta)
        limitador_ip.registrar_fallo(ip)
        return renderizar(request, "login.html", estado=401, error=str(error), email=email)
    limitador_cuenta.limpiar(clave_cuenta)
    request.session.clear()                       # evita fijación de sesión
    request.session["usuario_id"] = usuario.id
    return redirigir(usuario.ruta_inicio())       # el rol decide el destino (Factory Method: ruta_inicio)


@router.post("/logout", dependencies=[Depends(verificar_csrf)])
def cerrar_sesion(request: Request):
    request.session.clear()
    return redirigir("/login")

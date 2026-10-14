"""API JSON para el frontend (JavaScript vanilla con fetch)."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.datos.modelos import Usuario
from app.dependencias import fachada
from app.negocio.excepciones import NoEncontradoError, ReglaNegocioError
from app.presentacion.comun import requiere_cliente, requiere_usuario, verificar_csrf

router = APIRouter(prefix="/api")


@router.get("/disponibilidad")
def disponibilidad(restaurante_id: int, fecha: str, personas: int = 2,
                   usuario: Usuario = Depends(requiere_usuario)):
    """Franjas y mesas libres: `GET /api/disponibilidad?restaurante_id=&fecha=&personas=`."""
    try:
        return fachada.buscar_disponibilidad(restaurante_id, fecha, personas)
    except NoEncontradoError as error:
        return JSONResponse({"error": str(error)}, status_code=404)
    except ReglaNegocioError as error:
        return JSONResponse({"error": str(error)}, status_code=400)


# ---------- pre-pedido (carrito en la sesión) ----------
class LineaCarrito(BaseModel):
    producto_id: int
    cantidad: int = 1


def _respuesta_carrito(accion):
    try:
        return accion()
    except NoEncontradoError as error:
        return JSONResponse({"error": str(error)}, status_code=404)
    except ReglaNegocioError as error:
        return JSONResponse({"error": str(error)}, status_code=400)


@router.get("/carrito")
def ver_carrito(request: Request, usuario: Usuario = Depends(requiere_cliente)):
    return fachada.carrito_ver(request.session)


@router.post("/carrito/agregar", dependencies=[Depends(verificar_csrf)])
def agregar_al_carrito(request: Request, linea: LineaCarrito, usuario: Usuario = Depends(requiere_cliente)):
    return _respuesta_carrito(lambda: fachada.carrito_agregar(request.session, linea.producto_id, linea.cantidad))


@router.post("/carrito/cambiar", dependencies=[Depends(verificar_csrf)])
def cambiar_carrito(request: Request, linea: LineaCarrito, usuario: Usuario = Depends(requiere_cliente)):
    return _respuesta_carrito(lambda: fachada.carrito_cambiar(request.session, linea.producto_id, linea.cantidad))


@router.post("/carrito/vaciar", dependencies=[Depends(verificar_csrf)])
def vaciar_carrito(request: Request, usuario: Usuario = Depends(requiere_cliente)):
    return fachada.carrito_vaciar(request.session)


@router.get("/cobro")
def cobro(request: Request, propina: bool = False, usuario: Usuario = Depends(requiere_cliente)):
    """Total a pagar del pre-pedido en curso. El cliente solo indica si incluye la propina; los montos los calcula el servidor."""
    return fachada.cobro_pre_pedido(request.session, propina)

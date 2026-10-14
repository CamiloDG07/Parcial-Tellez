"""Controlador del administrador: gestiona solo el restaurante que administra."""
from datetime import date

from fastapi import APIRouter, Depends, Form, Request

from app import config
from app.datos.modelos import Usuario
from app.dependencias import fachada, horario_service, mesa_service, reserva_service, restaurante_service
from app.negocio.excepciones import NoAutorizadoError, NoEncontradoError, ReglaNegocioError
from app.presentacion.comun import avisar, entero, renderizar, redirigir, requiere_admin, verificar_csrf

router = APIRouter(prefix="/admin")


def _restaurante(admin: Usuario):
    return restaurante_service.del_administrador(admin)


def _ejecutar(request: Request, accion, ok: str, destino: str):
    """Ejecuta una acción de servicio y convierte los errores de negocio en avisos amigables."""
    try:
        accion()
        avisar(request, ok)
    except (ReglaNegocioError, NoEncontradoError, NoAutorizadoError) as error:
        avisar(request, str(error), "error")
    return redirigir(destino)


@router.get("")
def panel(request: Request, admin: Usuario = Depends(requiere_admin)):
    rest = _restaurante(admin)
    todas = reserva_service.listar_por_restaurante(admin, rest.id)
    hoy = date.today().isoformat()
    resumen = {
        "hoy": sum(1 for r in todas if r.fecha == hoy and r.estado != "CANCELADA"),
        "pendientes": sum(1 for r in todas if r.estado == "PENDIENTE"),
        "proximas": sum(1 for r in todas if r.fecha >= hoy and r.estado != "CANCELADA"),
        "mesas": len(mesa_service.listar(rest.id)),
    }
    return renderizar(request, "admin/panel.html", restaurante=rest, resumen=resumen)


# ---------- mesas ----------
@router.get("/mesas")
def mesas(request: Request, admin: Usuario = Depends(requiere_admin)):
    rest = _restaurante(admin)
    return renderizar(request, "admin/mesas.html", restaurante=rest, mesas=mesa_service.listar(rest.id))


@router.post("/mesas", dependencies=[Depends(verificar_csrf)])
def crear_mesa(request: Request, numero: str = Form(""), capacidad: str = Form(""), ubicacion: str = Form(""),
               activa: str = Form(""), admin: Usuario = Depends(requiere_admin)):
    rest = _restaurante(admin)
    def accion():
        mesa_service.crear(admin, rest.id, entero(numero, "número"), entero(capacidad, "capacidad"),
                           ubicacion, bool(activa))
    return _ejecutar(request, accion, "Mesa creada.", "/admin/mesas")


@router.post("/mesas/{mesa_id}/editar", dependencies=[Depends(verificar_csrf)])
def editar_mesa(request: Request, mesa_id: int, numero: str = Form(""), capacidad: str = Form(""),
                ubicacion: str = Form(""), activa: str = Form(""), admin: Usuario = Depends(requiere_admin)):
    def accion():
        mesa_service.actualizar(admin, mesa_id, entero(numero, "número"), entero(capacidad, "capacidad"),
                                ubicacion, bool(activa))
    return _ejecutar(request, accion, "Mesa actualizada.", "/admin/mesas")


@router.post("/mesas/{mesa_id}/eliminar", dependencies=[Depends(verificar_csrf)])
def eliminar_mesa(request: Request, mesa_id: int, admin: Usuario = Depends(requiere_admin)):
    return _ejecutar(request, lambda: mesa_service.eliminar(admin, mesa_id), "Mesa eliminada.", "/admin/mesas")


# ---------- horarios ----------
@router.get("/horarios")
def horarios(request: Request, admin: Usuario = Depends(requiere_admin)):
    rest = _restaurante(admin)
    por_dia = {h.dia_semana: h for h in horario_service.listar(rest.id)}
    return renderizar(request, "admin/horarios.html", restaurante=rest, por_dia=por_dia)


@router.post("/horarios", dependencies=[Depends(verificar_csrf)])
def guardar_horario(request: Request, dia_semana: str = Form(""), hora_apertura: str = Form(""),
                    hora_cierre: str = Form(""), admin: Usuario = Depends(requiere_admin)):
    rest = _restaurante(admin)
    def accion():
        horario_service.guardar(admin, rest.id, entero(dia_semana, "día"), hora_apertura, hora_cierre)
    return _ejecutar(request, accion, "Horario guardado.", "/admin/horarios")


@router.post("/horarios/{horario_id}/eliminar", dependencies=[Depends(verificar_csrf)])
def eliminar_horario(request: Request, horario_id: int, admin: Usuario = Depends(requiere_admin)):
    return _ejecutar(request, lambda: horario_service.eliminar(admin, horario_id),
                     "Horario eliminado (el restaurante queda cerrado ese día).", "/admin/horarios")


# ---------- reservas ----------
@router.get("/reservas")
def reservas(request: Request, fecha: str = "", estado: str = "", admin: Usuario = Depends(requiere_admin)):
    rest = _restaurante(admin)
    estado = estado if estado in config.ESTADOS else ""
    lista = reserva_service.listar_por_restaurante(admin, rest.id, fecha or None, estado or None)
    return renderizar(request, "admin/reservas.html", restaurante=rest, filas=fachada.enriquecer(lista),
                      filtro={"fecha": fecha, "estado": estado}, estados=config.ESTADOS)


@router.post("/reservas/{reserva_id}/confirmar", dependencies=[Depends(verificar_csrf)])
def confirmar(request: Request, reserva_id: int, admin: Usuario = Depends(requiere_admin)):
    return _ejecutar(request, lambda: reserva_service.confirmar_reserva(admin, reserva_id),
                     "Reserva confirmada.", "/admin/reservas")


@router.post("/reservas/{reserva_id}/cancelar", dependencies=[Depends(verificar_csrf)])
def cancelar(request: Request, reserva_id: int, admin: Usuario = Depends(requiere_admin)):
    return _ejecutar(request, lambda: reserva_service.cancelar_reserva(admin, reserva_id),
                     "Reserva cancelada.", "/admin/reservas")

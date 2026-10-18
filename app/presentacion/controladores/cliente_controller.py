"""Controlador del cliente: habla únicamente con la fachada (`ReservaFacade`)."""
from datetime import date, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import Response

from app import config
from app.datos.modelos import Usuario
from app.dependencias import auth_service, fachada
from app.negocio.calendario import evento_ics
from app.negocio.excepciones import NoAutorizadoError, NoEncontradoError, ReglaNegocioError
from app.presentacion.comun import (_cop, avisar, clasificar_reservas, entero, renderizar, redirigir,
                                    requiere_cliente, usuario_actual, verificar_csrf)

router = APIRouter()


@router.get("/")
def inicio(request: Request):
    usuario = usuario_actual(request)
    destacados = [fachada.resumen_restaurante(r) for r in fachada.listar_restaurantes()[:2]]
    return renderizar(request, "inicio.html", destacados=destacados)


@router.get("/restaurantes")
def restaurantes(request: Request, nombre: str = "", cocina: str = "", ciudad: str = ""):
    lista = [fachada.resumen_restaurante(r) for r in fachada.listar_restaurantes(nombre, cocina, ciudad)]
    cocinas, ciudades = fachada.filtros_restaurantes()
    return renderizar(request, "restaurantes.html", restaurantes=lista, cocinas=cocinas, ciudades=ciudades,
                      filtro={"nombre": nombre, "cocina": cocina, "ciudad": ciudad})


@router.get("/registro")
def formulario_registro(request: Request):
    usuario = usuario_actual(request)
    if usuario:
        return redirigir(usuario.ruta_inicio())
    return renderizar(request, "registro.html", valores={})


@router.post("/registro", dependencies=[Depends(verificar_csrf)])
def registrar(request: Request, nombre: str = Form(""), email: str = Form(""), password: str = Form(""),
              confirmacion: str = Form("")):
    try:
        usuario = auth_service.registrar(nombre, email, password, confirmacion)   # el rol siempre es cliente
    except ReglaNegocioError as error:
        return renderizar(request, "registro.html", estado=400, error=str(error),
                          valores={"nombre": nombre, "email": email})
    request.session.clear()
    request.session["usuario_id"] = usuario.id
    avisar(request, f"¡Bienvenido, {usuario.nombre}! Tu cuenta está lista.")
    return redirigir(usuario.ruta_inicio())


@router.get("/carta")
def carta(request: Request, restaurante_id: int | None = None):
    todos = fachada.listar_restaurantes()
    if restaurante_id is None and todos:
        restaurante_id = todos[0].id
    restaurante = fachada.obtener_restaurante(restaurante_id) if restaurante_id else None
    secciones = fachada.carta_de(restaurante.id) if restaurante else []
    return renderizar(request, "carta.html", restaurantes=todos, restaurante=restaurante, secciones=secciones)


@router.get("/reservar")
def formulario_reserva(request: Request, restaurante_id: int | None = None, fecha: str = "",
                       hora: str = "", personas: str = "2", mesa_id: str = "", notas: str = "",
                       propina: str = "", usuario: Usuario = Depends(requiere_cliente)):
    todos = fachada.listar_restaurantes()
    restaurante = None
    if restaurante_id is not None:
        try:
            restaurante = fachada.obtener_restaurante(restaurante_id)
        except NoEncontradoError:
            avisar(request, "Ese restaurante no existe.", "error")
    manana = (date.today() + timedelta(days=1)).isoformat()
    return renderizar(request, "reservar.html", restaurantes=todos, restaurante=restaurante,
                      valores={"fecha": fecha or manana, "hora": hora, "personas": personas,
                               "mesa_id": mesa_id, "notas": notas},
                      hoy=date.today().isoformat(), maximo=(date.today() + timedelta(days=180)).isoformat(),
                      cobro=fachada.cobro_pre_pedido(request.session, bool(propina)), propina=bool(propina),
                      tasa_propina=config.TASA_PROPINA_SUGERIDA_PCT)


@router.post("/reservar", dependencies=[Depends(verificar_csrf)])
def crear_reserva(request: Request, restaurante_id: str = Form(""), fecha: str = Form(""), hora: str = Form(""),
                  personas: str = Form(""), mesa_id: str = Form(""), notas: str = Form(""),
                  propina: str = Form(""), usuario: Usuario = Depends(requiere_cliente)):
    try:
        reserva = fachada.reservar_con_pre_pedido(usuario, {
            "restaurante_id": entero(restaurante_id, "restaurante"), "fecha": fecha, "hora": hora,
            "personas": entero(personas, "personas"), "mesa_id": entero(mesa_id, "mesa") if mesa_id else None,
            "notas": notas}, request.session)
    except (ReglaNegocioError, NoEncontradoError) as error:
        avisar(request, str(error), "error")
        consulta = urlencode({"restaurante_id": restaurante_id, "fecha": fecha, "hora": hora,
                              "personas": personas, "mesa_id": mesa_id, "notas": notas[:300], "propina": propina})
        return redirigir(f"/reservar?{consulta}")
    extra = ""
    if reserva.items:
        cobro = fachada.cobro_de_reserva(reserva, bool(propina))     # calculado en el servidor con la cadena de decoradores
        extra = (f" Pre-pedido: {len(reserva.items)} plato(s). Total a pagar estimado: {_cop(cobro['total_cop'])}"
                 f"{' (propina incluida)' if propina else ''}.")
    avisar(request, f"¡Reserva #{reserva.id} creada! Queda PENDIENTE hasta que el restaurante la confirme.{extra}")
    return redirigir("/mis-reservas")


VISTAS_RESERVAS = ("proximas", "pasadas", "canceladas", "todas")


@router.get("/mis-reservas")
def mis_reservas(request: Request, ver: str = "", usuario: Usuario = Depends(requiere_cliente)):
    hoy = date.today().isoformat()
    filas = fachada.mis_reservas(usuario)
    grupos = clasificar_reservas(filas, hoy)
    grupos["todas"] = grupos["proximas"] + grupos["pasadas"] + grupos["canceladas"]
    if ver not in VISTAS_RESERVAS:                      # por defecto: las próximas, o todas si no hay ninguna
        ver = "proximas" if grupos["proximas"] else "todas"
    conteos = {k: len(v) for k, v in grupos.items()}
    return renderizar(request, "mis_reservas.html", filas=grupos[ver], ver=ver, conteos=conteos,
                      total=len(filas), hoy=hoy)


@router.get("/mis-reservas/{reserva_id}/comprobante")
def comprobante(request: Request, reserva_id: int, usuario: Usuario = Depends(requiere_cliente)):
    """Comprobante imprimible. El Proxy rechaza (403) las reservas de otros clientes."""
    return renderizar(request, "comprobante.html", f=fachada.detalle_reserva(usuario, reserva_id),
                      tasa_propina=config.TASA_PROPINA_SUGERIDA_PCT)


@router.get("/mis-reservas/{reserva_id}/calendario.ics")
def calendario(reserva_id: int, usuario: Usuario = Depends(requiere_cliente)):
    f = fachada.detalle_reserva(usuario, reserva_id)
    contenido = evento_ics(f["reserva"], f["restaurante"], f["mesa"])
    return Response(contenido, media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="reserva-{reserva_id}.ics"'})


@router.post("/mis-reservas/{reserva_id}/cancelar", dependencies=[Depends(verificar_csrf)])
def cancelar(request: Request, reserva_id: int, usuario: Usuario = Depends(requiere_cliente)):
    try:
        fachada.cancelar(usuario, reserva_id)
        avisar(request, "Reserva cancelada.")
    except NoAutorizadoError:
        avisar(request, "No puedes cancelar esa reserva.", "error")
    except (ReglaNegocioError, NoEncontradoError) as error:
        avisar(request, str(error), "error")
    return redirigir("/mis-reservas")

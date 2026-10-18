"""Controlador del administrador: gestiona solo el restaurante que administra."""
import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response

from app import config
from app.datos.modelos import Usuario
from app.dependencias import (carta_service, estadisticas_service, fachada, horario_service, mesa_service,
                              reserva_service, restaurante_service)
from app.negocio.imagenes import MAX_BYTES, guardar_imagen
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
    datos = estadisticas_service.panel(rest.id)
    maximo = max([d["n"] for d in datos["serie_14d"]] + [1])
    for d in datos["serie_14d"]:
        d["pct"] = round(100 * d["n"] / maximo)
    tope = max([n for _, n in datos["top_productos"]] + [1])
    top = [{"nombre": nombre, "n": n, "pct": round(100 * n / tope)} for nombre, n in datos["top_productos"]]
    # dona de reservas por estado: porcentaje de cada segmento y desplazamiento acumulado (circunferencia = 100)
    total_estados = sum(datos["por_estado"].values())
    dona, acumulado = [], 0.0
    for estado, n in datos["por_estado"].items():
        pct = 100 * n / total_estados if total_estados else 0
        dona.append({"estado": estado, "n": n, "pct": round(pct), "largo": round(pct, 2), "inicio": round(acumulado, 2)})
        acumulado += pct
    calor = datos["mapa_calor"]
    return renderizar(request, "admin/panel.html", restaurante=rest, datos=datos, top=top, dona=dona,
                      total_estados=total_estados, calor=calor, dias_cortos=("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"),
                      mesas=len(mesa_service.listar(rest.id)))


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
POR_PAGINA = 10


def _reservas_filtradas(admin: Usuario, rest, fecha: str, estado: str, q: str) -> list[dict]:
    """Reservas del restaurante con los filtros del listado (las usan la tabla y la exportación CSV)."""
    estado = estado if estado in config.ESTADOS else ""
    lista = reserva_service.listar_por_restaurante(admin, rest.id, fecha or None, estado or None)
    filas = fachada.enriquecer(lista)
    termino = q.strip().lower()
    if termino:
        filas = [f for f in filas if termino in " ".join([
            str(f["reserva"].id), f["cliente"].nombre, f["cliente"].email, f["reserva"].notas]).lower()]
    return filas


@router.get("/reservas")
def reservas(request: Request, fecha: str = "", estado: str = "", q: str = "", pagina: int = 1,
             admin: Usuario = Depends(requiere_admin)):
    rest = _restaurante(admin)
    estado = estado if estado in config.ESTADOS else ""
    filas = _reservas_filtradas(admin, rest, fecha, estado, q)
    total = len(filas)
    paginas = max(1, -(-total // POR_PAGINA))
    pagina = min(max(pagina, 1), paginas)
    filas = filas[(pagina - 1) * POR_PAGINA: pagina * POR_PAGINA]
    return renderizar(request, "admin/reservas.html", restaurante=rest, filas=filas, total=total,
                      filtro={"fecha": fecha, "estado": estado, "q": q}, estados=config.ESTADOS,
                      pagina=pagina, paginas=paginas)


def _celda_csv(valor) -> str:
    """Evita la inyección de fórmulas al abrir el CSV en una hoja de cálculo (celdas que empiezan por = + - @)."""
    texto = "" if valor is None else str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


@router.get("/reservas.csv")
def exportar_reservas(fecha: str = "", estado: str = "", q: str = "", admin: Usuario = Depends(requiere_admin)):
    """Exporta las reservas filtradas. Separador «;» y BOM UTF-8 para que Excel en español lo abra en columnas."""
    rest = _restaurante(admin)
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(["codigo", "fecha", "hora", "cliente", "correo", "personas", "mesa", "estado",
                       "subtotal_pre_pedido_cop", "total_a_pagar_cop", "notas"])
    for f in _reservas_filtradas(admin, rest, fecha, estado, q):
        r = f["reserva"]
        escritor.writerow([_celda_csv(v) for v in (
            f"MD-{r.id:04d}", r.fecha, r.hora, f["cliente"].nombre, f["cliente"].email, r.num_personas,
            f["mesa"].numero, r.estado, f["total_cop"], f["cobro"]["total_cop"], r.notas)])
    return Response(("\ufeff" + salida.getvalue()).encode("utf-8"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="reservas-{date.today().isoformat()}.csv"'})


@router.post("/reservas/{reserva_id}/confirmar", dependencies=[Depends(verificar_csrf)])
def confirmar(request: Request, reserva_id: int, admin: Usuario = Depends(requiere_admin)):
    return _ejecutar(request, lambda: reserva_service.confirmar_reserva(admin, reserva_id),
                     "Reserva confirmada.", "/admin/reservas")


@router.post("/reservas/{reserva_id}/cancelar", dependencies=[Depends(verificar_csrf)])
def cancelar(request: Request, reserva_id: int, admin: Usuario = Depends(requiere_admin)):
    return _ejecutar(request, lambda: reserva_service.cancelar_reserva(admin, reserva_id),
                     "Reserva cancelada.", "/admin/reservas")


# ---------- carta: categorías y productos ----------
@router.get("/carta")
def carta(request: Request, admin: Usuario = Depends(requiere_admin)):
    rest = _restaurante(admin)
    return renderizar(request, "admin/carta.html", restaurante=rest,
                      secciones=carta_service.carta(rest.id, solo_disponibles=False),
                      categorias=carta_service.categorias(rest.id))


@router.post("/carta/categorias", dependencies=[Depends(verificar_csrf)])
def crear_categoria(request: Request, nombre: str = Form(""), orden: str = Form("0"),
                    admin: Usuario = Depends(requiere_admin)):
    rest = _restaurante(admin)
    return _ejecutar(request, lambda: carta_service.crear_categoria(admin, rest.id, nombre, entero(orden, "orden")),
                     "Categoría creada.", "/admin/carta")


@router.post("/carta/categorias/{categoria_id}/editar", dependencies=[Depends(verificar_csrf)])
def editar_categoria(request: Request, categoria_id: int, nombre: str = Form(""), orden: str = Form("0"),
                     admin: Usuario = Depends(requiere_admin)):
    return _ejecutar(request, lambda: carta_service.actualizar_categoria(admin, categoria_id, nombre, entero(orden, "orden")),
                     "Categoría actualizada.", "/admin/carta")


@router.post("/carta/categorias/{categoria_id}/eliminar", dependencies=[Depends(verificar_csrf)])
def eliminar_categoria(request: Request, categoria_id: int, admin: Usuario = Depends(requiere_admin)):
    return _ejecutar(request, lambda: carta_service.eliminar_categoria(admin, categoria_id),
                     "Categoría eliminada.", "/admin/carta")


def _imagen_subida(archivo: UploadFile | None) -> str | None:
    """Lee (con tope de tamaño) y valida la imagen; devuelve el nombre aleatorio guardado o None si no se envió."""
    if archivo is None or not archivo.filename:
        return None
    return guardar_imagen(archivo.file.read(MAX_BYTES + 1))


@router.post("/carta/productos", dependencies=[Depends(verificar_csrf)])
def crear_producto(request: Request, categoria_id: str = Form(""), nombre: str = Form(""), descripcion: str = Form(""),
                   precio_cop: str = Form(""), disponible: str = Form(""), imagen: UploadFile | None = File(None),
                   admin: Usuario = Depends(requiere_admin)):
    rest = _restaurante(admin)
    def accion():
        carta_service.crear_producto(admin, rest.id, entero(categoria_id, "categoría"), nombre, descripcion,
                                     entero(precio_cop, "precio"), _imagen_subida(imagen) or "", bool(disponible))
    return _ejecutar(request, accion, "Producto creado.", "/admin/carta")


@router.post("/carta/productos/{producto_id}/editar", dependencies=[Depends(verificar_csrf)])
def editar_producto(request: Request, producto_id: int, categoria_id: str = Form(""), nombre: str = Form(""),
                    descripcion: str = Form(""), precio_cop: str = Form(""), disponible: str = Form(""),
                    imagen: UploadFile | None = File(None), admin: Usuario = Depends(requiere_admin)):
    def accion():
        carta_service.actualizar_producto(admin, producto_id, entero(categoria_id, "categoría"), nombre, descripcion,
                                          entero(precio_cop, "precio"), _imagen_subida(imagen), bool(disponible))
    return _ejecutar(request, accion, "Producto actualizado.", "/admin/carta")


@router.post("/carta/productos/{producto_id}/disponibilidad", dependencies=[Depends(verificar_csrf)])
def alternar_producto(request: Request, producto_id: int, admin: Usuario = Depends(requiere_admin)):
    return _ejecutar(request, lambda: carta_service.alternar_disponibilidad(admin, producto_id),
                     "Disponibilidad actualizada.", "/admin/carta")


@router.post("/carta/productos/{producto_id}/eliminar", dependencies=[Depends(verificar_csrf)])
def eliminar_producto(request: Request, producto_id: int, admin: Usuario = Depends(requiere_admin)):
    return _ejecutar(request, lambda: carta_service.eliminar_producto(admin, producto_id),
                     "Producto eliminado.", "/admin/carta")

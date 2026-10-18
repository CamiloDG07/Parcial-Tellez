"""Fase 5 (pulido): tarjetas y comprobante, calendario .ics, panel con gráficas, CSV, transacción contra la doble
reserva, límite de intentos de login, cabeceras de seguridad y consultas en lote."""
import csv
import io
import os
import threading
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import config
from app.datos import seed
from app.datos.conexion import ConexionBD
from app.datos.modelos import Mesa, Reserva, Restaurante
from app.main import app
from app.negocio.calendario import _doblar, evento_ics
from app.presentacion.comun import _codigo, _fecha_larga, _srcset_imagen, clasificar_reservas
from app.presentacion.limitador import LimitadorIntentos
from tests.conftest import proximo_dia
from tests.test_web import admin_web, cliente_web, entrar, reservar, token  # noqa: F401  (fixtures y ayudas)


# ---------- ayudas de presentación ----------
def test_codigo_y_fecha_larga():
    assert _codigo(60) == "MD-0060" and _codigo(7) == "MD-0007"
    assert _fecha_larga("2026-10-15") == "jueves 15 de octubre de 2026"
    assert _fecha_larga("2026-01-01") == "jueves 1 de enero de 2026"
    assert _fecha_larga("basura") == "basura"


def test_srcset_solo_si_existe_la_foto_pequena(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PLATOS_DIR", tmp_path)
    monkeypatch.setattr(config, "UPLOADS_DIR", tmp_path / "subidas")
    (tmp_path / "pizza.jpg").write_bytes(b"x")
    assert _srcset_imagen("pizza.jpg") == ""                    # falta pizza@400.jpg
    (tmp_path / "pizza@400.jpg").write_bytes(b"x")
    assert _srcset_imagen("pizza.jpg") == "/static/img/platos/pizza@400.jpg 400w, /static/img/platos/pizza.jpg 800w"
    assert _srcset_imagen("") == "" and _srcset_imagen("no-existe.jpg") == ""


def _ultimo_id() -> int:
    with ConexionBD().sesion() as con:
        return con.execute("SELECT MAX(id) FROM reserva").fetchone()[0]


def _fila(estado, fecha, hora="19:00"):
    return {"reserva": Reserva(1, 1, 1, 1, fecha, hora, 2, estado)}


def test_clasificar_reservas_orden_y_grupos():
    filas = [_fila("PENDIENTE", "2026-10-25"), _fila("CONFIRMADA", "2026-10-20", "13:00"), _fila("CANCELADA", "2026-10-30"),
             _fila("CONFIRMADA", "2026-10-01"), _fila("PENDIENTE", "2026-10-20", "12:00")]
    g = clasificar_reservas(filas, "2026-10-18")
    assert [(f["reserva"].fecha, f["reserva"].hora) for f in g["proximas"]] == [
        ("2026-10-20", "12:00"), ("2026-10-20", "13:00"), ("2026-10-25", "19:00")]     # la más cercana primero
    assert [f["reserva"].fecha for f in g["pasadas"]] == ["2026-10-01"]
    assert [f["reserva"].estado for f in g["canceladas"]] == ["CANCELADA"]


# ---------- páginas del cliente ----------
def test_mis_reservas_filtros_y_codigo(cliente_web):
    assert "No hay grabaciones" in cliente_web.get("/mis-reservas").text
    reservar(cliente_web)
    rid = _ultimo_id()
    codigo = _codigo(rid)
    pagina = cliente_web.get("/mis-reservas").text                  # por defecto: próximas
    assert codigo in pagina and "PENDIENTE" in pagina and "CALENDARIO" in pagina and "COMPROBANTE" in pagina
    t = token(cliente_web, "/mis-reservas")
    cliente_web.post(f"/mis-reservas/{rid}/cancelar", data={"csrf_token": t})
    assert codigo not in cliente_web.get("/mis-reservas?ver=proximas").text.split("</nav>")[1].split("<footer")[0]
    assert codigo in cliente_web.get("/mis-reservas?ver=canceladas").text
    assert codigo in cliente_web.get("/mis-reservas?ver=todas").text
    assert codigo in cliente_web.get("/mis-reservas?ver=inventado").text          # valor inválido: vista por defecto


def test_comprobante_y_calendario_solo_para_el_dueno(cliente_web, admin_web, bd):
    reservar(cliente_web)
    rid = _ultimo_id()
    c = cliente_web.get(f"/mis-reservas/{rid}/comprobante")
    assert c.status_code == 200 and _codigo(rid) in c.text and "no es una factura" in c.text
    ics = cliente_web.get(f"/mis-reservas/{rid}/calendario.ics")
    assert ics.status_code == 200 and ics.headers["content-type"].startswith("text/calendar")
    assert "attachment" in ics.headers["content-disposition"] and "BEGIN:VEVENT" in ics.text

    otro = TestClient(app, follow_redirects=False)                                  # otro cliente registrado
    t = token(otro, "/registro")
    otro.post("/registro", data={"csrf_token": t, "nombre": "Otra Persona", "email": "otra@demo.com",
                                 "password": "Clave12345", "confirmacion": "Clave12345"})
    assert otro.get(f"/mis-reservas/{rid}/comprobante").status_code == 403        # Proxy: reserva ajena
    assert otro.get(f"/mis-reservas/{rid}/calendario.ics").status_code == 403
    assert admin_web.get(f"/mis-reservas/{rid}/comprobante").status_code == 403   # el administrador no es cliente
    assert TestClient(app, follow_redirects=False).get(f"/mis-reservas/{rid}/comprobante").status_code == 303   # sin sesión
    assert cliente_web.get("/mis-reservas/9999/comprobante").status_code == 404


def test_paginas_con_portadas_noscript_y_srcset(cliente_web):
    assert cliente_web.get("/restaurantes").text.count('class="portada"') == 5
    assert "<noscript>" in cliente_web.get("/reservar?restaurante_id=1").text
    carta = cliente_web.get("/carta?restaurante_id=1").text
    assert 'loading="lazy"' in carta and 'decoding="async"' in carta


# ---------- calendario .ics ----------
def _datos_ics(nombre="Slice's, Medianoche; Palace"):
    r = Reserva(60, 1, 1, 3, "2026-10-23", "20:00", 5, "PENDIENTE", "Cumpleaños\nvela, por favor")
    rest = Restaurante(1, nombre, "Cra 7 #45-12", "Bogotá", "Pizzería", "", 1)
    return r, rest, Mesa(3, 1, 3, 4, "Salón")


def test_evento_ics_valido_y_escapado():
    r, rest, mesa = _datos_ics()
    texto = evento_ics(r, rest, mesa, ahora=datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc))
    assert texto.startswith("BEGIN:VCALENDAR\r\n") and texto.endswith("END:VCALENDAR\r\n")
    assert "DTSTART:20261023T200000" in texto and "DTEND:20261023T220000" in texto
    assert "DTSTAMP:20261018T120000Z" in texto and "UID:reserva-60@midnight-diner.local" in texto
    assert "SUMMARY:Reserva en Slice's\\, Medianoche\\; Palace" in texto.replace("\r\n ", "")     # , y ; escapados
    assert "Cumpleaños\\nvela\\, por favor" in texto.replace("\r\n ", "")                    # salto de línea escapado
    assert "STATUS:TENTATIVE" in texto
    for linea in texto.split("\r\n"):
        assert len(linea.encode("utf-8")) <= 75                                              # RFC 5545: líneas plegadas


def test_doblar_lineas_largas_sin_cortar_caracteres():
    larga = "DESCRIPTION:" + "ñ" * 80
    partes = _doblar(larga)
    assert len(partes) > 1 and all(len(p.encode("utf-8")) <= 75 for p in partes) and all(p.startswith(" ") for p in partes[1:])
    assert "".join(p[1:] if i else p for i, p in enumerate(partes)) == larga


def test_ics_de_reserva_cancelada():
    r, rest, mesa = _datos_ics()
    r.estado = "CANCELADA"
    assert "STATUS:CANCELLED" in evento_ics(r, rest, mesa)


# ---------- panel de administración ----------
def test_estadisticas_por_estado_y_mapa_de_calor(bd):
    from app.negocio.servicios.estadisticas_service import FRANJAS_CALOR, EstadisticasService
    rs = [Reserva(1, 1, 1, 1, "2026-10-19", "19:30", 2, "PENDIENTE"),      # lunes, franja 19–21
          Reserva(2, 1, 1, 1, "2026-10-19", "20:00", 2, "CONFIRMADA"),     # lunes, franja 19–21
          Reserva(3, 1, 1, 1, "2026-10-20", "12:00", 2, "CONFIRMADA"),     # martes, franja 11–13
          Reserva(4, 1, 1, 1, "2026-10-20", "12:00", 2, "CANCELADA")]      # cancelada: no cuenta en el calor
    assert EstadisticasService.por_estado(rs) == {"PENDIENTE": 1, "CONFIRMADA": 2, "CANCELADA": 1}
    calor = EstadisticasService.mapa_calor(rs)
    assert calor["celdas"][0][FRANJAS_CALOR.index((19, 21))] == 2
    assert calor["celdas"][1][0] == 1 and calor["maximo"] == 2
    assert sum(sum(f) for f in calor["celdas"]) == 3
    assert len(calor["franjas"]) == len(FRANJAS_CALOR) and calor["franjas"][0] == "11–13"


def test_panel_muestra_dona_y_mapa_de_calor(admin_web, cliente_web):
    reservar(cliente_web)
    pagina = admin_web.get("/admin").text
    assert "RESERVAS POR ESTADO" in pagina and "OCUPACIÓN POR DÍA Y HORA" in pagina
    assert 'class="dona-svg"' in pagina and "Gráfico de dona" in pagina and 'class="calor"' in pagina
    assert 'class="solo-lectores"' in pagina                       # tabla alternativa para lectores de pantalla


def test_exportar_csv(admin_web, cliente_web):
    reservar(cliente_web, notas="=1+1")                              # nota que parece una fórmula
    r = admin_web.get("/admin/reservas.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"] and r.content.startswith(b"\xef\xbb\xbf")
    filas = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig")), delimiter=";"))
    assert filas[0][:3] == ["codigo", "fecha", "hora"] and len(filas[0]) == 11
    propia = [f for f in filas[1:] if f[0] == _codigo(_ultimo_id())][0]
    assert propia[3] == "Camila Demo" and propia[7] == "PENDIENTE"
    assert propia[10] == "'=1+1"                                      # sin inyección de fórmulas
    solo_pendientes = list(csv.reader(io.StringIO(admin_web.get("/admin/reservas.csv?estado=CONFIRMADA").content.decode("utf-8-sig")), delimiter=";"))
    assert all(f[7] == "CONFIRMADA" for f in solo_pendientes[1:])


def test_csv_solo_del_restaurante_del_admin_y_solo_admin(cliente_web, bd):
    reservar(cliente_web)
    otro = entrar("admin2@demo.com", "Admin123!")
    assert _codigo(_ultimo_id()).encode() not in otro.get("/admin/reservas.csv").content
    assert cliente_web.get("/admin/reservas.csv").status_code == 403


# ---------- doble reserva: transacción exclusiva ----------
def _reserva(mesa_id, hora, fecha=None, usuario=1):
    return Reserva(None, usuario, 1, mesa_id, fecha or proximo_dia(), hora, 2, "PENDIENTE", "", "2026-10-18T10:00:00")


def test_insertar_si_libre_respeta_la_franja(bd):
    from app.dependencias import reserva_dao
    assert reserva_dao.insertar_si_libre(_reserva(3, "19:00"), 120) is not None
    assert reserva_dao.insertar_si_libre(_reserva(3, "20:59"), 120) is None             # dentro de las 2 h
    assert reserva_dao.insertar_si_libre(_reserva(3, "17:01"), 120) is None
    assert reserva_dao.insertar_si_libre(_reserva(3, "21:00"), 120) is not None         # justo al terminar la anterior
    assert reserva_dao.insertar_si_libre(_reserva(4, "19:00"), 120) is not None         # otra mesa
    assert reserva_dao.insertar_si_libre(_reserva(3, "19:00", proximo_dia(desde=3)), 120) is not None   # otro día


def test_cancelar_libera_la_mesa_para_insertar_si_libre(bd):
    from app.dependencias import reserva_dao
    rid = reserva_dao.insertar_si_libre(_reserva(3, "19:00"), 120)
    reserva_dao.cambiar_estado(rid, "CANCELADA")
    assert reserva_dao.insertar_si_libre(_reserva(3, "19:00"), 120) is not None


def test_dos_conexiones_a_la_vez_solo_una_gana_la_mesa(bd):
    """Sin pasar por el cerrojo del servicio: la transacción BEGIN IMMEDIATE decide quién se queda con la mesa."""
    from app.dependencias import reserva_dao
    hilos, resultados, barrera = 8, [], threading.Barrier(8)

    def intentar(i):
        barrera.wait()
        resultados.append(reserva_dao.insertar_si_libre(_reserva(3, "19:00", usuario=1), 120))

    ts = [threading.Thread(target=intentar, args=(i,)) for i in range(hilos)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sum(r is not None for r in resultados) == 1 and sum(r is None for r in resultados) == hilos - 1
    with ConexionBD().sesion() as con:
        assert con.execute("SELECT COUNT(*) FROM reserva WHERE mesa_id = 3 AND fecha = ?", (proximo_dia(),)).fetchone()[0] == 1


def test_el_servicio_rechaza_si_pierde_la_carrera(cliente_web, monkeypatch):
    from app.dependencias import reserva_dao
    monkeypatch.setattr(reserva_dao, "insertar_si_libre", lambda reserva, duracion: None)   # otra reserva se adelantó
    r = reservar(cliente_web)
    assert r.headers["location"].startswith("/reservar?")
    assert "ya está reservada" in cliente_web.get(r.headers["location"]).text


def test_sqlite_en_modo_wal(bd):
    con = ConexionBD().conectar()
    try:
        assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        con.close()


def test_seed_reset_borra_tambien_los_archivos_wal(tmp_path):
    ruta = str(tmp_path / "wal.db")
    ConexionBD.reiniciar(ruta)
    seed.sembrar()
    for sufijo in ("-wal", "-shm"):
        with open(ruta + sufijo, "wb") as f:
            f.write(b"basura")
    seed.sembrar(reiniciar=True)
    with ConexionBD().sesion() as con:
        assert con.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 6
    for sufijo in ("-wal", "-shm"):
        assert not os.path.exists(ruta + sufijo) or open(ruta + sufijo, "rb").read() != b"basura"
    ConexionBD.reiniciar()


# ---------- límite de intentos de login ----------
class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_limitador_bloquea_y_se_libera():
    reloj = Reloj()
    lim = LimitadorIntentos(max_fallos=3, ventana_s=60, bloqueo_s=120, reloj=reloj)
    clave = ("1.2.3.4", "a@b.co")
    for _ in range(2):
        lim.registrar_fallo(clave)
    assert lim.segundos_bloqueo(clave) == 0
    lim.registrar_fallo(clave)
    assert lim.segundos_bloqueo(clave) == 121
    assert lim.segundos_bloqueo(("1.2.3.4", "otro@b.co")) == 0                       # otra cuenta no se afecta
    reloj.t += 119
    assert 0 < lim.segundos_bloqueo(clave) <= 2
    reloj.t += 3
    assert lim.segundos_bloqueo(clave) == 0                                           # el bloqueo venció
    lim.registrar_fallo(clave)
    assert lim.segundos_bloqueo(clave) == 0                                           # empieza de cero


def test_limitador_ventana_y_limpiar():
    reloj = Reloj()
    lim = LimitadorIntentos(max_fallos=3, ventana_s=60, bloqueo_s=120, reloj=reloj)
    lim.registrar_fallo("k"); lim.registrar_fallo("k")
    reloj.t += 61                                                                     # los fallos viejos salen de la ventana
    lim.registrar_fallo("k")
    assert lim.segundos_bloqueo("k") == 0
    lim.registrar_fallo("k"); lim.registrar_fallo("k")
    assert lim.segundos_bloqueo("k") > 0
    lim.limpiar("k")
    assert lim.segundos_bloqueo("k") == 0


def _intentar_login(c, email, password):
    return c.post("/login", data={"email": email, "password": password, "csrf_token": token(c)})


def test_login_se_bloquea_tras_cinco_fallos(bd):
    c = TestClient(app, follow_redirects=False)
    for _ in range(5):
        assert _intentar_login(c, "cliente@demo.com", "mala").status_code == 401
    r = _intentar_login(c, "cliente@demo.com", "Cliente123!")                         # ya bloqueado: ni con la clave correcta
    assert r.status_code == 429 and "Demasiados intentos" in r.text and int(r.headers["Retry-After"]) > 0
    assert _intentar_login(c, "admin@demo.com", "Admin123!").status_code == 303        # otra cuenta sigue entrando


def test_un_login_correcto_reinicia_el_contador(bd):
    c = TestClient(app, follow_redirects=False)
    for _ in range(4):
        _intentar_login(c, "cliente@demo.com", "mala")
    assert _intentar_login(c, "cliente@demo.com", "Cliente123!").status_code == 303
    c2 = TestClient(app, follow_redirects=False)
    for _ in range(4):
        assert _intentar_login(c2, "cliente@demo.com", "mala").status_code == 401     # no llega a bloquearse
    assert _intentar_login(c2, "cliente@demo.com", "Cliente123!").status_code == 303


# ---------- cabeceras de seguridad y caché ----------
def test_cabeceras_de_seguridad(bd):
    c = TestClient(app)
    h = c.get("/login").headers
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in h["content-security-policy"] and "script-src 'self'" in h["content-security-policy"]
    assert "referrer-policy" in h and "strict-transport-security" not in h


def test_hsts_y_cookie_segura_solo_con_https_only(bd, monkeypatch):
    monkeypatch.setattr(config, "HTTPS_ONLY", True)
    assert "max-age" in TestClient(app).get("/login").headers["strict-transport-security"]


def test_cache_en_archivos_estaticos(bd):
    c = TestClient(app)
    assert c.get("/static/css/tema.css").headers["cache-control"] == "public, max-age=300"
    assert c.get("/static/img/plato-vacio.svg").headers["cache-control"] == "public, max-age=86400"
    assert "cache-control" not in c.get("/login").headers or "public" not in c.get("/login").headers["cache-control"]


# ---------- consultas en lote (sin N+1) ----------
def test_enriquecer_usa_un_numero_constante_de_consultas(tmp_path):
    ConexionBD.reiniciar(str(tmp_path / "lote.db"))
    seed.sembrar(historial=True)
    from app.dependencias import fachada, reserva_dao
    cuenta = {"n": 0}
    original = ConexionBD.conectar

    def contando(self):
        con = original(self)
        con.set_trace_callback(lambda s: cuenta.__setitem__("n", cuenta["n"] + 1))
        return con

    ConexionBD.conectar = contando
    try:
        todas = reserva_dao.listar_por_restaurante(1)
        assert len(todas) >= 50
        filas = fachada.enriquecer(todas)
    finally:
        ConexionBD.conectar = original
        ConexionBD.reiniciar()
    assert len(filas) == len(todas)
    assert cuenta["n"] < 40            # antes de la optimización eran ~200 (una consulta por plato de cada reserva)
    assert any(f["detalle"] for f in filas) and all("nombre" in d for f in filas for d in f["detalle"])

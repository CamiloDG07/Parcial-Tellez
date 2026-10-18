"""El cobro (subtotal, descuento, impuesto y total) se guarda al crear la reserva: un cambio posterior de tasas
en config.py no altera lo que se cobró antes (auditabilidad)."""
import sqlite3

import pytest

from app import config
from app.datos.conexion import ConexionBD
from app.dependencias import auth_service, fachada, reserva_dao, reserva_service
from app.negocio.patrones.estructurales.cobro_decorator import desglose, desglose_guardado, instantanea
from tests.conftest import proximo_dia


def _cliente():
    return auth_service.autenticar("cliente@demo.com", "Cliente123!")


def _reservar(items, hora="19:00", mesa=3):
    return reserva_service.crear_reserva(_cliente(), {
        "restaurante_id": 1, "fecha": proximo_dia(), "hora": hora, "personas": 2, "mesa_id": mesa, "items": items})


def test_la_reserva_guarda_la_instantanea_del_cobro(bd):
    r = _reservar([(1, 10)])                                   # 10 × $18.000 = $180.000 (supera el mínimo del descuento)
    guardada = reserva_dao.obtener_por_id(r.id)
    assert (guardada.subtotal_cop, guardada.descuento_pct, guardada.descuento_cop) == (180000, 10, 18000)
    assert (guardada.impuesto_pct, guardada.impuesto_cop, guardada.total_pagar_cop) == (8, 12960, 174960)
    assert guardada.total_pagar_cop == guardada.subtotal_cop - guardada.descuento_cop + guardada.impuesto_cop


def test_sin_descuento_cuando_no_llega_al_minimo(bd):
    r = _reservar([(1, 2)])
    g = reserva_dao.obtener_por_id(r.id)
    assert (g.subtotal_cop, g.descuento_pct, g.descuento_cop, g.impuesto_cop, g.total_pagar_cop) == (36000, 0, 0, 2880, 38880)


def test_reserva_sin_pre_pedido_cobra_cero(bd):
    r = _reservar(None)
    g = reserva_dao.obtener_por_id(r.id)
    assert (g.subtotal_cop, g.impuesto_cop, g.total_pagar_cop) == (0, 0, 0)


def test_cambiar_las_tasas_no_altera_reservas_anteriores(bd, monkeypatch):
    antes = _reservar([(1, 10)])
    monkeypatch.setattr(config, "TASA_IMPUESTO_CONSUMO_PCT", 19)
    monkeypatch.setattr(config, "DESCUENTO_PEDIDO_GRANDE_PCT", 0)
    filas = {f["reserva"].id: f for f in fachada.mis_reservas(_cliente())}
    assert filas[antes.id]["cobro"]["total_cop"] == 174960                    # lo que se cobró entonces
    assert [l["etiqueta"] for l in filas[antes.id]["cobro"]["lineas"]][1:] == [
        "Descuento por pedido grande (10 %)", "Impuesto al consumo (8 %)"]
    nueva = _reservar([(1, 10)], hora="12:00", mesa=4)                          # esta ya nace con las tasas nuevas
    assert reserva_dao.obtener_por_id(nueva.id).impuesto_pct == 19
    assert reserva_dao.obtener_por_id(nueva.id).total_pagar_cop == 214200


def test_desglose_guardado_coincide_con_el_calculo_en_vivo_y_suma_las_lineas(bd):
    r = _reservar([(1, 10), (2, 1)])
    g = reserva_dao.obtener_por_id(r.id)
    g.items = r.items
    for con_propina in (False, True):
        vivo, guardado = desglose(g.items, con_propina), desglose_guardado(g, con_propina)
        assert vivo["total_cop"] == guardado["total_cop"]
        assert sum(l["monto_cop"] for l in guardado["lineas"]) == guardado["total_cop"]
    assert desglose_guardado(g)["propina_sugerida_cop"] == desglose(g.items)["propina_sugerida_cop"]


def test_cancelar_borra_el_pre_pedido_y_el_cobro_visible_es_cero(bd):
    r = _reservar([(1, 10)])
    reserva_dao.cambiar_estado(r.id, "CANCELADA")
    fila = fachada.mis_reservas(_cliente())[0]
    assert fila["cobro"]["total_cop"] == 0 and not fila["detalle"]
    assert reserva_dao.obtener_por_id(r.id).total_pagar_cop == 174960          # el registro conserva lo que se había calculado


def test_el_esquema_rechaza_totales_incoherentes(bd):
    r = _reservar([(1, 2)])
    with ConexionBD().sesion() as con:
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("UPDATE reserva SET total_pagar_cop = 1 WHERE id = ?", (r.id,))


def test_instantanea_usa_las_mismas_reglas_de_redondeo():
    class L:                                                                     # línea mínima del pre-pedido
        def __init__(self, c, p): self.cantidad, self.precio_unitario_cop = c, p
    s = instantanea([L(1, 150000)])                                              # justo en el mínimo: sí hay descuento
    assert (s["descuento_cop"], s["impuesto_cop"], s["total_pagar_cop"]) == (15000, 10800, 145800)
    s = instantanea([L(1, 149999)])
    assert (s["descuento_pct"], s["descuento_cop"]) == (0, 0)


def test_migracion_agrega_columnas_y_calcula_reservas_anteriores(tmp_path):
    """Una base creada antes de guardar el cobro se actualiza sola al iniciar."""
    ruta = tmp_path / "vieja.db"
    viejo = sqlite3.connect(ruta)
    viejo.executescript("""
        CREATE TABLE reserva (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, restaurante_id INTEGER,
            mesa_id INTEGER, fecha TEXT, hora TEXT, num_personas INTEGER, estado TEXT DEFAULT 'PENDIENTE',
            notas TEXT DEFAULT '', creado_en TEXT);
        CREATE TABLE reserva_item (id INTEGER PRIMARY KEY AUTOINCREMENT, reserva_id INTEGER, producto_id INTEGER,
            cantidad INTEGER, precio_unitario_cop INTEGER);
        INSERT INTO reserva (usuario_id, restaurante_id, mesa_id, fecha, hora, num_personas, creado_en)
            VALUES (1, 1, 1, '2026-10-30', '19:00', 2, 'x');
        INSERT INTO reserva_item (reserva_id, producto_id, cantidad, precio_unitario_cop) VALUES (1, 1, 10, 18000);
    """)
    viejo.commit()
    viejo.close()
    ConexionBD.reiniciar(str(ruta))
    try:
        ConexionBD().inicializar_esquema()
        ConexionBD().inicializar_esquema()                                       # idempotente
        with ConexionBD().sesion() as con:
            fila = con.execute("SELECT subtotal_cop, descuento_cop, impuesto_cop, total_pagar_cop FROM reserva").fetchone()
        assert tuple(fila) == (180000, 18000, 12960, 174960)
    finally:
        ConexionBD.reiniciar()

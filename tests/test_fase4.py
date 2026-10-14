"""Fase 4: patrón Decorator (Cobro) y su conexión al flujo real."""
import re
from itertools import permutations
from types import SimpleNamespace as Linea

import pytest
from fastapi.testclient import TestClient

from app import config
from app.datos.conexion import ConexionBD
from app.dependencias import auth_service, estadisticas_service, fachada, item_dao, producto_dao, reserva_service
from app.main import app
from app.negocio.patrones.estructurales.cobro_decorator import (Cobro, CobroBase, ConDescuento, ConImpuestoConsumo,
                                                               ConPropinaSugerida, armar_cadena, armar_cobro, desglose,
                                                               porcentaje_de)
from tests.conftest import proximo_dia

FABRICAS = {"d": ConDescuento, "i": ConImpuestoConsumo, "p": ConPropinaSugerida}


def items(*pares):
    """Ítems de prueba: (cantidad, precio_unitario_cop)."""
    return [Linea(cantidad=c, precio_unitario_cop=p) for c, p in pares]


def cadena(subtotal, orden):
    c: Cobro = CobroBase(items((1, subtotal)))
    for letra in orden:
        c = FABRICAS[letra](c)
    return c


# ---------- regla de redondeo ----------
@pytest.mark.parametrize("monto,tasa,esperado", [
    (100, 8, 8), (0, 8, 0), (4, 10, 0), (5, 10, 1), (15, 10, 2), (25, 10, 3),   # empates (x,5) suben: half-up
    (1001, 8, 80), (1006, 8, 80), (1007, 8, 81), (153000, 8, 12240),
])
def test_porcentaje_de_redondea_half_up_con_enteros(monto, tasa, esperado):
    assert porcentaje_de(monto, tasa) == esperado
    assert isinstance(porcentaje_de(monto, tasa), int)


def test_porcentaje_de_rechaza_negativos():
    with pytest.raises(ValueError):
        porcentaje_de(-1, 8)
    with pytest.raises(ValueError):
        porcentaje_de(100, -8)


# ---------- componente base ----------
def test_cobro_base_suma_precios_congelados():
    base = CobroBase(items((2, 18000), (1, 22000), (3, 1000)))
    assert base.monto_cop() == 61000 and base.descripcion() == "Subtotal del pre-pedido"


def test_pre_pedido_vacio():
    assert CobroBase([]).monto_cop() == 0
    d = desglose([], con_propina=True)
    assert d["subtotal_cop"] == d["total_cop"] == d["propina_sugerida_cop"] == 0
    assert [l["monto_cop"] for l in d["lineas"]] == [0, 0, 0]
    assert armar_cobro([]).monto_cop() == 0


# ---------- cada decorador por separado ----------
def test_con_impuesto_consumo():
    c = ConImpuestoConsumo(CobroBase(items((1, 100000))))
    assert c.monto_cop() == 108000 and c.tasa_pct == config.TASA_IMPUESTO_CONSUMO_PCT
    assert c.descripcion() == "Subtotal del pre-pedido → Impuesto al consumo (8 %)"


def test_con_propina_sugerida():
    c = ConPropinaSugerida(CobroBase(items((1, 100000))))
    assert c.monto_cop() == 110000 and c.descripcion().endswith("Propina sugerida (10 %)")


def test_con_descuento():
    c = ConDescuento(CobroBase(items((1, 100000))))
    assert c.monto_cop() == 90000 and c.descripcion().endswith("Descuento por pedido grande (10 %)")


def test_tasa_propia_y_validacion():
    assert ConImpuestoConsumo(CobroBase(items((1, 1000))), 19).monto_cop() == 1190
    assert ConDescuento(CobroBase(items((1, 1000))), 0).monto_cop() == 1000
    for mala in (-1, 101, 8.5, "8"):
        with pytest.raises(ValueError):
            ConImpuestoConsumo(CobroBase([]), mala)


def test_las_tasas_son_configurables(monkeypatch):
    monkeypatch.setattr(config, "TASA_IMPUESTO_CONSUMO_PCT", 19)
    monkeypatch.setattr(config, "TASA_PROPINA_SUGERIDA_PCT", 0)
    assert ConImpuestoConsumo(CobroBase(items((1, 1000)))).monto_cop() == 1190
    assert ConPropinaSugerida(CobroBase(items((1, 1000)))).monto_cop() == 1000


# ---------- composición y orden ----------
def test_composicion_apilada_con_montos_exactos():
    c = ConPropinaSugerida(ConImpuestoConsumo(ConDescuento(CobroBase(items((1, 170000))))))
    assert c.monto_cop() == 181764          # 170000 -17000 = 153000; +12240 = 165240; +16524 = 181764
    assert c.descripcion() == ("Subtotal del pre-pedido → Descuento por pedido grande (10 %) → "
                               "Impuesto al consumo (8 %) → Propina sugerida (10 %)")


def test_el_orden_no_importa_con_montos_redondos():
    for subtotal in (150000, 152000, 170000, 1000000):
        assert len({cadena(subtotal, o).monto_cop() for o in permutations("dip")}) == 1


def test_el_orden_solo_cambia_por_redondeo():
    """Los factores (1-d), (1+t), (1+p) conmutan; el redondeo por paso puede mover el total 1 o 2 pesos."""
    resultados = {"".join(o): cadena(5, o).monto_cop() for o in permutations("dip")}
    assert resultados["dip"] == 4 and resultados["ipd"] == 5          # el orden SÍ cambia el resultado, por redondeo
    peor = max(max(r := [cadena(s, o).monto_cop() for o in permutations("dip")]) - min(r) for s in range(1, 3000))
    assert 1 <= peor <= 2


# ---------- cadena de producción ----------
def test_descuento_solo_desde_el_minimo():
    minimo = config.DESCUENTO_PEDIDO_GRANDE_MINIMO_COP
    assert [type(e).__name__ for e in armar_cadena(items((1, minimo - 1)))] == ["CobroBase", "ConImpuestoConsumo"]
    assert [type(e).__name__ for e in armar_cadena(items((1, minimo)))] == ["CobroBase", "ConDescuento", "ConImpuestoConsumo"]


def test_propina_es_opcional():
    sin, con = armar_cobro(items((1, 100000))), armar_cobro(items((1, 100000)), con_propina=True)
    assert (sin.monto_cop(), con.monto_cop()) == (108000, 118800)       # 108000 + 10 % = 118800
    assert "Propina" not in sin.descripcion() and "Propina" in con.descripcion()


def test_desglose_suma_exactamente_el_total():
    for subtotal in (0, 1, 5, 18000, 149999, 150000, 170000, 999999):
        for propina in (False, True):
            d = desglose(items((1, subtotal)), propina)
            assert sum(l["monto_cop"] for l in d["lineas"]) == d["total_cop"]
            assert all(isinstance(l["monto_cop"], int) for l in d["lineas"])
            assert d["total_con_propina_cop"] - armar_cobro(items((1, subtotal))).monto_cop() == d["propina_sugerida_cop"]


def test_desglose_de_ejemplo():
    d = desglose(items((9, 18000)), con_propina=True)       # 162000
    assert [(l["etiqueta"], l["monto_cop"]) for l in d["lineas"]] == [
        ("Subtotal del pre-pedido", 162000), ("Descuento por pedido grande (10 %)", -16200),
        ("Impuesto al consumo (8 %)", 11664), ("Propina sugerida (10 %)", 15746)]
    assert d["total_cop"] == 173210 and d["propina_sugerida_cop"] == 15746 and d["incluye_propina"]


# ---------- conexión al flujo real (web) ----------
def token(c, ruta="/login"):
    return re.search(r'name="csrf_token" value="([^"]+)"', c.get(ruta).text).group(1)


def entrar(email, pw):
    c = TestClient(app, follow_redirects=False)
    assert c.post("/login", data={"email": email, "password": pw, "csrf_token": token(c)}).status_code == 303
    return c


def agregar(c, producto_id, cantidad):
    h = {"X-CSRF-Token": token(c, "/carta")}
    r = c.post("/api/carrito/agregar", json={"producto_id": producto_id, "cantidad": cantidad}, headers=h)
    assert r.status_code == 200, r.text


def total_en(html):
    return re.search(r'id="cobro-total">([^<]+)<', html).group(1)


def cop(n):
    return "$" + f"{n:,}".replace(",", ".")


def reservar(c, **extra):
    datos = {"restaurante_id": "1", "fecha": proximo_dia(), "hora": "19:00", "personas": "2", "mesa_id": "1",
             "notas": "", "csrf_token": token(c, "/reservar?restaurante_id=1")}
    datos.update(extra)
    return c.post("/reservar", data=datos)


def test_total_de_la_pantalla_de_confirmacion_coincide_con_la_cadena(bd):
    c = entrar("cliente@demo.com", "Cliente123!")
    agregar(c, 1, 9)                                                # 9 × 18.000 = 162.000
    esperado = armar_cobro(items((9, 18000))).monto_cop()
    esperado_propina = armar_cobro(items((9, 18000)), con_propina=True).monto_cop()
    assert (esperado, esperado_propina) == (157464, 173210)
    pagina = c.get("/reservar?restaurante_id=1").text
    assert total_en(pagina) == cop(esperado) and "Descuento por pedido grande" in pagina
    assert 'id="propina"' in pagina and "checked" not in re.search(r'<input type="checkbox" id="propina"[^>]*>', pagina).group(0)
    con = c.get("/reservar?restaurante_id=1&propina=1").text
    assert total_en(con) == cop(esperado_propina)
    api = c.get("/api/cobro?propina=true").json()
    assert api["total_cop"] == esperado_propina and c.get("/api/cobro").json()["total_cop"] == esperado


def test_el_cliente_no_envia_montos_y_la_base_no_cambia(bd):
    c = entrar("cliente@demo.com", "Cliente123!")
    agregar(c, 1, 9)
    with ConexionBD().sesion() as con:
        columnas_antes = {t: [f[1] for f in con.execute(f"PRAGMA table_info({t})")] for t in ("reserva", "reserva_item")}
    r = reservar(c, total_cop="1", total="1", precio_unitario_cop="1", propina="1")     # montos falsos: se ignoran
    assert r.headers["location"] == "/mis-reservas"
    guardados = item_dao.listar_por_reserva(1)
    assert [(i.cantidad, i.precio_unitario_cop) for i in guardados] == [(9, 18000)]         # precio de la BD, congelado
    assert estadisticas_service.panel(1)["ingresos_cop"] == 162000                          # el KPI sigue siendo el subtotal
    with ConexionBD().sesion() as con:
        assert columnas_antes == {t: [f[1] for f in con.execute(f"PRAGMA table_info({t})")] for t in columnas_antes}
        assert "propina" not in str(columnas_antes)                                          # la propina no se guarda


def test_detalle_de_reserva_y_admin_muestran_el_total_a_pagar(bd):
    c = entrar("cliente@demo.com", "Cliente123!")
    agregar(c, 1, 9)
    reservar(c)
    mis = c.get("/mis-reservas").text
    assert "A pagar $157.464" in mis and "TOTAL A PAGAR" in mis and "$157.464" in mis
    assert "-$16.200" in mis and "Propina sugerida, opcional y no incluida" in mis and "$15.746" in mis
    adm = entrar("admin@demo.com", "Admin123!").get("/admin/reservas").text
    assert "$162.000" in adm and "A pagar: $157.464" in adm


def test_mensaje_de_confirmacion_usa_la_cadena(bd):
    c = entrar("cliente@demo.com", "Cliente123!")
    agregar(c, 1, 9)
    r = reservar(c, propina="1")
    assert r.status_code == 303
    assert "Total a pagar estimado: $173.210 (propina incluida)" in c.get("/mis-reservas").text


def test_reserva_sin_pre_pedido_no_muestra_cobro(bd):
    c = entrar("cliente@demo.com", "Cliente123!")
    assert 'id="cobro"' not in c.get("/reservar?restaurante_id=1").text
    assert c.get("/api/cobro").json()["total_cop"] == 0


def test_api_cobro_exige_cliente(bd):
    assert TestClient(app, follow_redirects=False).get("/api/cobro").status_code == 303
    assert entrar("admin@demo.com", "Admin123!").get("/api/cobro").status_code == 403


def test_enriquecer_usa_precios_congelados_aunque_cambie_el_precio(bd):
    cli = auth_service.autenticar("cliente@demo.com", "Cliente123!")
    reserva_service.crear_reserva(cli, {"restaurante_id": 1, "fecha": proximo_dia(), "hora": "19:00", "personas": 2,
                                        "mesa_id": 1, "notas": "", "items": [(1, 9)]})
    p = producto_dao.obtener_por_id(1)
    p.precio_cop = 99999
    producto_dao.actualizar(p)
    assert fachada.mis_reservas(cli)[0]["cobro"]["total_cop"] == 157464

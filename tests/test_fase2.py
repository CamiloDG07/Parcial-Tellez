"""Fase 2: registro, carta, pre-pedido, imágenes, estadísticas."""
import re
import sqlite3
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.datos.conexion import ConexionBD
from app.dependencias import (auth_service, carrito_service, carta_service, estadisticas_service, fachada,
                              item_dao, producto_dao, reserva_service)
from app.main import app
from app.negocio.excepciones import NoAutorizadoError, ReglaNegocioError
from app.negocio.imagenes import guardar_imagen
from tests.conftest import proximo_dia

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def datos(**extra):
    base = {"restaurante_id": 1, "fecha": proximo_dia(), "hora": "19:00", "personas": 2, "mesa_id": 1, "notas": ""}
    base.update(extra)
    return base


@pytest.fixture()
def cliente(bd):
    return auth_service.autenticar("cliente@demo.com", "Cliente123!")


@pytest.fixture()
def admin(bd):
    return auth_service.autenticar("admin@demo.com", "Admin123!")


def token(c, ruta="/login"):
    return re.search(r'name="csrf_token" value="([^"]+)"', c.get(ruta).text).group(1)


def entrar(email, pw):
    c = TestClient(app, follow_redirects=False)
    assert c.post("/login", data={"email": email, "password": pw, "csrf_token": token(c)}).status_code == 303
    return c


# ---------- seed de la carta ----------
def test_seed_carta_demo(bd):
    esperado = {1: [5, 4, 3], 5: [4, 5, 5]}          # pizzería y trattoria: cada una con su propia carta
    for rid, conteo in esperado.items():
        carta = carta_service.carta(rid)
        assert [len(s["productos"]) for s in carta] == conteo
        assert [s["categoria"].nombre for s in carta] == ["Entrada", "Plato fuerte", "Postre"]
    p = producto_dao.obtener_por_id(1)
    assert (p.nombre, p.precio_cop, p.imagen) == ("Bruschetta Clásica", 18000, "bruschetta-clasica.jpg")
    assert all(isinstance(x.precio_cop, int) for x in producto_dao.listar())


def test_esquema_usa_precio_cop_entero(bd):
    with ConexionBD().sesion() as con:
        columnas = [f[1] for f in con.execute("PRAGMA table_info(producto)")]
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO producto (restaurante_id, categoria_id, nombre, precio_cop) VALUES (1,1,'x',-5)")
    assert "precio_cop" in columnas and "precio_centavos" not in columnas


# ---------- registro ----------
def test_registro_crea_cliente_y_hace_login(bd):
    u = auth_service.registrar("Ana Prueba", " ANA@Correo.com ", "Clave12345", "Clave12345")
    assert u.rol == "cliente" and u.email == "ana@correo.com" and u.id
    assert auth_service.autenticar("ana@correo.com", "Clave12345").id == u.id


@pytest.mark.parametrize("campos,mensaje", [
    (("A", "a@b.co", "Clave12345", "Clave12345"), "nombre"),
    (("Ana", "no-es-correo", "Clave12345", "Clave12345"), "correo"),
    (("Ana", "a@b.co", "corta1", "corta1"), "contraseña"),
    (("Ana", "a@b.co", "sinnumeros", "sinnumeros"), "contraseña"),
    (("Ana", "a@b.co", "Clave12345", "Otra123456"), "confirmación"),
    (("Ana", "cliente@demo.com", "Clave12345", "Clave12345"), "Ya existe"),
])
def test_registro_valida(bd, campos, mensaje):
    with pytest.raises(ReglaNegocioError, match=mensaje):
        auth_service.registrar(*campos)


def test_registro_web_ignora_rol_enviado(bd):
    c = TestClient(app, follow_redirects=False)
    assert c.get("/registro").status_code == 200
    r = c.post("/registro", data={"nombre": "Eva", "email": "eva@x.co", "password": "Clave12345",
                                  "confirmacion": "Clave12345", "rol": "administrador", "csrf_token": token(c, "/registro")})
    assert r.status_code == 303 and r.headers["location"] == "/restaurantes"
    assert auth_service.autenticar("eva@x.co", "Clave12345").rol == "cliente"
    assert c.get("/admin").status_code == 403


# ---------- pre-pedido: carrito y builder ----------
def test_carrito_total_correcto(bd):
    sesion = {}
    carrito_service.agregar(sesion, 1, 2)        # 2 × 18.000
    carrito_service.agregar(sesion, 2, 1)        # 1 × 22.000
    carrito_service.agregar(sesion, 1, 1)        # suma a la línea existente
    r = carrito_service.resumen(sesion)
    assert r["cantidad"] == 4 and r["total_cop"] == 3 * 18000 + 22000 and r["restaurante_id"] == 1
    carrito_service.cambiar(sesion, 1, 0)
    assert carrito_service.resumen(sesion)["total_cop"] == 22000


def test_carrito_rechaza_otro_restaurante_y_no_disponible(admin):
    sesion = {}
    carrito_service.agregar(sesion, 1, 1)
    with pytest.raises(ReglaNegocioError, match="otro restaurante"):
        carrito_service.agregar(sesion, 13, 1)          # producto del restaurante 5
    carta_service.alternar_disponibilidad(admin, 3)
    with pytest.raises(ReglaNegocioError, match="no está disponible"):
        carrito_service.agregar(sesion, 3, 1)
    for n in (0, 21, -1):
        with pytest.raises(ReglaNegocioError, match="cantidad"):
            carrito_service.agregar(sesion, 1, n)


def test_reserva_con_items_guarda_total_y_precio_congelado(cliente, admin):
    r = reserva_service.crear_reserva(cliente, datos(items=[(1, 2), (2, 1), (1, 1)]))
    assert sorted((i.producto_id, i.cantidad) for i in r.items) == [(1, 3), (2, 1)]
    assert r.total_cop == 3 * 18000 + 22000
    guardados = item_dao.listar_por_reserva(r.id)
    assert sum(i.subtotal_cop for i in guardados) == 76000
    p = producto_dao.obtener_por_id(1)
    p.precio_cop = 99999
    producto_dao.actualizar(p)                           # cambiar el precio no altera lo ya reservado
    assert sum(i.subtotal_cop for i in item_dao.listar_por_reserva(r.id)) == 76000


def test_reserva_rechaza_producto_ajeno_o_no_disponible(cliente, admin):
    with pytest.raises(ReglaNegocioError, match="no pertenece"):
        reserva_service.crear_reserva(cliente, datos(items=[(13, 1)]))
    with pytest.raises(ReglaNegocioError, match="no pertenece"):
        reserva_service.crear_reserva(cliente, datos(items=[(9999, 1)]))
    carta_service.alternar_disponibilidad(admin, 1)
    with pytest.raises(ReglaNegocioError, match="no está disponible"):
        reserva_service.crear_reserva(cliente, datos(items=[(1, 1)]))
    with pytest.raises(ReglaNegocioError, match="cantidad"):
        reserva_service.crear_reserva(cliente, datos(items=[(2, 0)]))
    assert reserva_service.mis_reservas(cliente) == []   # nada quedó a medias


def test_cancelar_borra_los_items(cliente):
    r = reserva_service.crear_reserva(cliente, datos(items=[(1, 2), (2, 1)]))
    assert len(item_dao.listar_por_reserva(r.id)) == 2
    reserva_service.cancelar_reserva(cliente, r.id)
    assert item_dao.listar_por_reserva(r.id) == []
    assert reserva_service.obtener(cliente, r.id).estado == "CANCELADA"


def test_borrar_reserva_en_cascada_elimina_items(cliente):
    r = reserva_service.crear_reserva(cliente, datos(items=[(1, 1)]))
    with ConexionBD().sesion() as con:
        con.execute("DELETE FROM reserva WHERE id = ?", (r.id,))
        assert con.execute("SELECT COUNT(*) FROM reserva_item").fetchone()[0] == 0


def test_fachada_pre_pedido_vacia_el_carrito(cliente):
    sesion = {}
    fachada.carrito_agregar(sesion, 1, 2)
    r = fachada.reservar_con_pre_pedido(cliente, datos(), sesion)
    assert r.total_cop == 36000 and fachada.carrito_ver(sesion)["cantidad"] == 0
    fachada.carrito_agregar(sesion, 13, 1)               # carrito de otro restaurante (producto 13 = primer plato del restaurante 5)
    with pytest.raises(ReglaNegocioError, match="otro restaurante"):
        fachada.reservar_con_pre_pedido(cliente, datos(hora="14:00"), sesion)
    assert [f["total_cop"] for f in fachada.mis_reservas(cliente)] == [36000]


# ---------- imágenes ----------
def test_guardar_imagen_valida_tipo_tamano_y_nombre(tmp_path):
    n1, n2 = guardar_imagen(PNG, tmp_path), guardar_imagen(PNG, tmp_path)
    assert n1 != n2 and re.fullmatch(r"[0-9a-f]{32}\.png", n1) and (tmp_path / n1).read_bytes() == PNG
    assert guardar_imagen(b"\xff\xd8\xff\xe0" + b"0" * 10, tmp_path).endswith(".jpg")
    assert guardar_imagen(b"RIFF\x00\x00\x00\x00WEBPVP8 ", tmp_path).endswith(".webp")
    for malo, msg in ((b"MZ\x90\x00 ejecutable", "Formato"), (b"GIF89a....", "Formato"), (b"", "ninguna"),
                      (PNG + b"0" * (2 * 1024 * 1024), "2 MB")):
        with pytest.raises(ReglaNegocioError, match=msg):
            guardar_imagen(malo, tmp_path)


# ---------- panel: indicadores ----------
def test_estadisticas_kpis(cliente, bd):
    manana = date.today() + timedelta(days=1)
    reserva_service.crear_reserva(cliente, datos(fecha=manana.isoformat(), items=[(1, 2), (2, 1)]))
    r2 = reserva_service.crear_reserva(cliente, datos(fecha=manana.isoformat(), mesa_id=2, items=[(3, 1)]))
    reserva_service.cancelar_reserva(cliente, r2.id)     # cancelada: no cuenta
    p = estadisticas_service.panel(1)
    assert p["proximas"] == 1 and p["pendientes"] == 1
    assert p["ingresos_cop"] == 2 * 18000 + 22000
    assert p["top_productos"][0] == ("Bruschetta Clásica", 2)
    assert len(p["serie_14d"]) == 14 and p["serie_14d"][-1]["fecha"] == date.today().isoformat()
    assert estadisticas_service.ocupacion_pct(1, manana) == round(100 * 120 / (6 * 11 * 60))


def test_ocupacion_cero_si_cerrado(bd):
    assert estadisticas_service.ocupacion_pct(2, date.fromisoformat(proximo_dia(0))) == 0   # restaurante 2 cierra lunes


def test_seed_con_historial_alimenta_el_panel(tmp_path, monkeypatch):
    from app.datos import seed
    ConexionBD.reiniciar(str(tmp_path / "h.db"))
    monkeypatch.setattr(seed, "hashear_password", lambda p: "x")
    seed.sembrar(historial=True)
    p = estadisticas_service.panel(1)
    assert sum(d["n"] for d in p["serie_14d"]) > 10 and p["ingresos_cop"] > 0 and len(p["top_productos"]) == 5
    ConexionBD.reiniciar()


# ---------- web ----------
def test_flujo_web_registro_carta_pre_pedido_reserva_y_panel(bd):
    c = TestClient(app, follow_redirects=False)
    c.post("/registro", data={"nombre": "Eva", "email": "eva@x.co", "password": "Clave12345",
                              "confirmacion": "Clave12345", "csrf_token": token(c, "/registro")})
    carta = c.get("/carta?restaurante_id=1").text
    assert "Bruschetta Clásica" in carta and "$18.000" in carta and 'data-agregar="1"' in carta
    h = {"X-CSRF-Token": token(c, "/carta")}
    assert c.post("/api/carrito/agregar", json={"producto_id": 1, "cantidad": 2}).status_code == 403   # sin CSRF
    r = c.post("/api/carrito/agregar", json={"producto_id": 1, "cantidad": 2}, headers=h)
    assert r.json()["total_cop"] == 36000
    assert c.post("/api/carrito/agregar", json={"producto_id": 13, "cantidad": 1}, headers=h).status_code == 400
    assert c.get("/api/carrito").json()["cantidad"] == 2          # persiste en la sesión
    pagina = c.get("/reservar?restaurante_id=1").text
    assert "TOTAL ESTIMADO" in pagina and "$36.000" in pagina

    datos_form = {"restaurante_id": "1", "fecha": proximo_dia(), "hora": "19:00", "personas": "2", "mesa_id": "1",
                  "notas": "", "csrf_token": token(c, "/reservar?restaurante_id=1")}
    assert c.post("/reservar", data=datos_form).headers["location"] == "/mis-reservas"
    mis = c.get("/mis-reservas").text
    assert "$36.000" in mis and "2 × Bruschetta Clásica" in mis
    assert c.get("/api/carrito").json()["cantidad"] == 0          # se vació al confirmar

    adm = entrar("admin@demo.com", "Admin123!")
    assert "$36.000" in adm.get("/admin").text                     # ingreso estimado en el panel
    assert "$36.000" in adm.get("/admin/reservas").text

    t = token(c, "/mis-reservas")
    c.post("/mis-reservas/1/cancelar", data={"csrf_token": t})
    assert item_dao.listar_por_reserva(1) == []


def test_admin_crud_carta_con_imagen(bd):
    adm = entrar("admin@demo.com", "Admin123!")
    t = token(adm, "/admin/carta")
    nuevo = {"csrf_token": t, "categoria_id": "1", "nombre": "Pizza Nocturna", "precio_cop": "45000",
             "descripcion": "Con aceitunas", "disponible": "1"}
    adm.post("/admin/carta/productos", data=nuevo, files={"imagen": ("mala.png", b"MZ ejecutable", "image/png")})
    assert "Formato no permitido" in adm.get("/admin/carta").text
    assert all(p.nombre != "Pizza Nocturna" for p in producto_dao.listar())          # nada se creó

    adm.post("/admin/carta/productos", data=nuevo, files={"imagen": ("x.png", PNG, "image/png")})
    p = next(p for p in producto_dao.listar() if p.nombre == "Pizza Nocturna")
    assert p.precio_cop == 45000 and re.fullmatch(r"[0-9a-f]{32}\.png", p.imagen)
    assert adm.get(f"/static/uploads/{p.imagen}").status_code == 200

    adm.post("/admin/carta/productos", data={**nuevo, "nombre": "Sin foto", "precio_cop": "abc"})
    pag = adm.get("/admin/carta").text
    assert "número entero" in pag
    adm.post(f"/admin/carta/productos/{p.id}/disponibilidad", data={"csrf_token": t})
    assert "Pizza Nocturna" not in adm.get("/carta?restaurante_id=1").text            # agotado: oculto al público
    adm.post("/admin/carta/categorias", data={"csrf_token": t, "nombre": "Bebidas", "orden": "9"})
    assert "BEBIDAS" in adm.get("/admin/carta").text
    adm.post(f"/admin/carta/productos/{p.id}/eliminar", data={"csrf_token": t})
    assert all(x.id != p.id for x in producto_dao.listar())


def test_admin_ajeno_no_toca_la_carta(bd):
    otro = entrar("admin2@demo.com", "Admin123!")
    t = token(otro, "/admin/carta")
    otro.post("/admin/carta/productos/1/disponibilidad", data={"csrf_token": t})
    otro.post("/admin/carta/productos/1/eliminar", data={"csrf_token": t})
    assert producto_dao.obtener_por_id(1).disponible is True
    with pytest.raises(NoAutorizadoError):
        carta_service.eliminar_producto(auth_service.autenticar("admin2@demo.com", "Admin123!"), 1)


def test_cliente_no_entra_a_carta_admin(bd):
    c = entrar("cliente@demo.com", "Cliente123!")
    assert c.get("/admin/carta").status_code == 403
    assert c.post("/admin/carta/productos/1/eliminar", data={"csrf_token": token(c, "/carta")}).status_code == 403


def test_admin_reservas_busqueda_y_paginacion(cliente, bd):
    for i in range(12):
        reserva_service.crear_reserva(cliente, datos(fecha=proximo_dia(desde=2 + i), notas=f"nota-{i}"))
    adm = entrar("admin@demo.com", "Admin123!")
    p1, p2 = adm.get("/admin/reservas").text, adm.get("/admin/reservas?pagina=2").text
    assert "12 reserva(s) · página 1 de 2" in p1 and p1.count('class="estado ') == 10 and p2.count('class="estado ') == 2
    assert "nota-5" in adm.get("/admin/reservas?q=nota-5").text and "1 reserva(s)" in adm.get("/admin/reservas?q=nota-5").text
    assert "0 reserva" not in adm.get("/admin/reservas?q=cliente@demo").text
    assert "No hay reservas" in adm.get("/admin/reservas?q=zzzz").text
    assert "página 2 de 2" in adm.get("/admin/reservas?pagina=99").text          # se acota


# ---------- fotos de la carta ----------
def test_cada_plato_tiene_foto_y_credito(bd):
    import json
    from app import config
    creditos = json.loads((config.PLATOS_DIR / "CREDITOS.json").read_text(encoding="utf-8"))
    for p in producto_dao.listar():
        archivo = config.PLATOS_DIR / p.imagen
        assert archivo.is_file(), p.imagen
        assert archivo.stat().st_size < 250 * 1024, p.imagen
        assert creditos[p.imagen[:-4]]["autor"] and creditos[p.imagen[:-4]]["licencia"]


def test_avisos_flash_se_acumulan(bd):
    adm = entrar("admin@demo.com", "Admin123!")
    t = token(adm, "/admin/mesas")
    adm.post("/admin/mesas", data={"csrf_token": t, "numero": "-1", "capacidad": "2"})
    adm.post("/admin/mesas", data={"csrf_token": t, "numero": "abc", "capacidad": "2"})
    pagina = adm.get("/admin/mesas").text
    assert "mayores que cero" in pagina and "número entero" in pagina

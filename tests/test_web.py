"""Pruebas de extremo a extremo de la capa web: login, roles, CSRF y el flujo completo."""
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import proximo_dia


def token(cliente: TestClient, ruta: str = "/login") -> str:
    html = cliente.get(ruta).text
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def entrar(email: str, password: str) -> TestClient:
    c = TestClient(app, follow_redirects=False)
    r = c.post("/login", data={"email": email, "password": password, "csrf_token": token(c)})
    assert r.status_code == 303, r.text
    return c


@pytest.fixture()
def cliente_web(bd):
    with TestClient(app, follow_redirects=False) as c:    # `with` ejecuta el lifespan
        yield entrar("cliente@demo.com", "Cliente123!")


@pytest.fixture()
def admin_web(bd):
    return entrar("admin@demo.com", "Admin123!")


def reservar(c: TestClient, **extra):
    datos = {"restaurante_id": "1", "fecha": proximo_dia(), "hora": "19:00", "personas": "2", "mesa_id": "1",
             "notas": "", "csrf_token": token(c, "/reservar?restaurante_id=1")}
    datos.update(extra)
    return c.post("/reservar", data=datos)


def test_paginas_publicas(bd):
    c = TestClient(app)
    assert c.get("/").status_code == 200
    assert c.get("/login").status_code == 200
    assert c.get("/restaurantes").status_code == 200
    assert "Pizzería" in c.get("/restaurantes?cocina=Pizzería").text
    assert "Sushi" not in c.get("/restaurantes?cocina=Pizzería").text


def test_login_incorrecto(bd):
    c = TestClient(app, follow_redirects=False)
    r = c.post("/login", data={"email": "cliente@demo.com", "password": "mala", "csrf_token": token(c)})
    assert r.status_code == 401 and "Correo o contraseña incorrectos" in r.text
    assert c.get("/mis-reservas").headers["location"] == "/login"      # no quedó sesión iniciada


def test_login_redirige_segun_rol(bd):
    assert entrar("cliente@demo.com", "Cliente123!").get("/login").headers["location"] == "/restaurantes"
    assert entrar("admin@demo.com", "Admin123!").get("/login").headers["location"] == "/admin"


def test_login_sin_csrf_se_rechaza(bd):
    c = TestClient(app, follow_redirects=False)
    r = c.post("/login", data={"email": "cliente@demo.com", "password": "Cliente123!"})
    assert r.status_code == 403


def test_rutas_protegidas_sin_sesion(bd):
    c = TestClient(app, follow_redirects=False)
    for ruta in ("/mis-reservas", "/reservar", "/admin", "/admin/mesas", "/api/disponibilidad?restaurante_id=1&fecha=2030-01-01"):
        r = c.get(ruta)
        assert r.status_code == 303 and r.headers["location"] == "/login", ruta


def test_cliente_no_entra_a_admin(cliente_web):
    for ruta in ("/admin", "/admin/mesas", "/admin/horarios", "/admin/reservas"):
        r = cliente_web.get(ruta)
        assert r.status_code == 403 and "ACCESO DENEGADO" in r.text


def test_admin_no_reserva(admin_web):
    assert admin_web.get("/reservar").status_code == 403
    assert admin_web.get("/mis-reservas").status_code == 403


def test_api_disponibilidad(cliente_web):
    r = cliente_web.get(f"/api/disponibilidad?restaurante_id=1&fecha={proximo_dia()}&personas=2")
    cuerpo = r.json()
    assert r.status_code == 200 and cuerpo["abierto"] and len(cuerpo["mesas"]) == 6
    assert cliente_web.get("/api/disponibilidad?restaurante_id=1&fecha=basura&personas=2").status_code == 400
    assert cliente_web.get("/api/disponibilidad?restaurante_id=999&fecha=2030-01-01").status_code == 404


def test_flujo_completo_reserva_confirmacion_y_doble_reserva(cliente_web, admin_web):
    r = reservar(cliente_web)
    assert r.status_code == 303 and r.headers["location"] == "/mis-reservas"
    pagina = cliente_web.get("/mis-reservas").text
    assert "PENDIENTE" in pagina and "Slice Palace" in pagina

    # doble reserva de la misma mesa y hora → rechazada con mensaje amigable
    r2 = reservar(cliente_web, hora="20:00")
    assert r2.status_code == 303 and r2.headers["location"].startswith("/reservar?")
    assert "ya está reservada" in cliente_web.get(r2.headers["location"]).text

    # el admin ve la reserva y la confirma
    assert "cliente@demo.com" in admin_web.get("/admin/reservas").text
    t = token(admin_web, "/admin/reservas")
    admin_web.post("/admin/reservas/1/confirmar", data={"csrf_token": t})
    assert "CONFIRMADA" in cliente_web.get("/mis-reservas").text

    # el cliente cancela y la mesa vuelve a estar libre
    t = token(cliente_web, "/mis-reservas")
    cliente_web.post("/mis-reservas/1/cancelar", data={"csrf_token": t})
    assert "CANCELADA" in cliente_web.get("/mis-reservas").text
    assert reservar(cliente_web).headers["location"] == "/mis-reservas"


def test_reserva_con_mesa_automatica(cliente_web):
    r = reservar(cliente_web, mesa_id="", personas="5")
    assert r.headers["location"] == "/mis-reservas"
    assert "Sala de fiestas" in cliente_web.get("/mis-reservas").text or "Escenario" in cliente_web.get("/mis-reservas").text


def test_errores_de_validacion_en_servidor(cliente_web):
    for extra, mensaje in (({"fecha": "2020-01-01"}, "futuras"), ({"personas": "abc"}, "número entero"),
                           ({"personas": "9", "mesa_id": "1"}, "máximo"), ({"hora": "03:00"}, "horario")):
        r = reservar(cliente_web, **extra)
        assert r.status_code == 303
        assert mensaje in cliente_web.get(r.headers["location"]).text, extra


def test_admin_de_otro_restaurante_no_gestiona_ajenos(cliente_web, bd):
    reservar(cliente_web)
    otro = entrar("admin2@demo.com", "Admin123!")
    assert "cliente@demo.com" not in otro.get("/admin/reservas").text
    t = token(otro, "/admin/reservas")
    otro.post("/admin/reservas/1/confirmar", data={"csrf_token": t})
    assert "PENDIENTE" in cliente_web.get("/mis-reservas").text
    t = token(otro, "/admin/mesas")
    otro.post("/admin/mesas/1/editar", data={"csrf_token": t, "numero": "1", "capacidad": "9", "ubicacion": "x", "activa": "1"})
    assert "9 pax" not in cliente_web.get("/reservar?restaurante_id=1").text
    from app.dependencias import mesa_service
    assert mesa_service.obtener(1).capacidad == 2


def test_admin_crud_mesas_y_horarios(admin_web):
    t = token(admin_web, "/admin/mesas")
    admin_web.post("/admin/mesas", data={"csrf_token": t, "numero": "20", "capacidad": "4", "ubicacion": "Patio", "activa": "1"})
    assert "Patio" in admin_web.get("/admin/mesas").text
    # número duplicado → aviso de error, sin romper
    admin_web.post("/admin/mesas", data={"csrf_token": t, "numero": "20", "capacidad": "4", "ubicacion": "X"})
    assert "Ya existe la mesa 20" in admin_web.get("/admin/mesas").text
    from app.dependencias import mesa_service
    nueva = [m for m in mesa_service.listar(1) if m.numero == 20][0]
    admin_web.post(f"/admin/mesas/{nueva.id}/editar", data={"csrf_token": t, "numero": "20", "capacidad": "6", "ubicacion": "Patio", "activa": ""})
    m = mesa_service.obtener(nueva.id)
    assert (m.capacidad, m.activa) == (6, False)
    admin_web.post(f"/admin/mesas/{nueva.id}/eliminar", data={"csrf_token": t})
    assert all(x.numero != 20 for x in mesa_service.listar(1))

    t = token(admin_web, "/admin/horarios")
    admin_web.post("/admin/horarios", data={"csrf_token": t, "dia_semana": "0", "hora_apertura": "10:00", "hora_cierre": "20:00"})
    assert "10:00" in admin_web.get("/admin/horarios").text
    admin_web.post("/admin/horarios", data={"csrf_token": t, "dia_semana": "0", "hora_apertura": "20:00", "hora_cierre": "10:00"})
    assert "posterior a la de apertura" in admin_web.get("/admin/horarios").text


def test_error_amigable_sin_traza(bd):
    c = TestClient(app)
    r = c.get("/ruta-inexistente")
    assert r.status_code == 404 and "Traceback" not in r.text
    assert c.get("/reservar?restaurante_id=abc").status_code in (200, 303, 422)


def test_chips_de_cocina_en_directorio(bd):
    c = TestClient(app)
    html = c.get("/restaurantes").text
    for cocina in ("PIZZERÍA", "COLOMBIANA", "JAPONESA", "PARRILLA", "ITALIANA"):
        assert f">{cocina}</a>" in html
    activo = c.get("/restaurantes?cocina=Parrilla").text
    assert re.search(r'class="chip activo" href="/restaurantes\?cocina=Parrilla"', activo)
    assert "Cámara 04 Parrilla" in activo and "Backstage" not in activo


def test_aviso_del_restaurante_elegido_al_reservar(cliente_web):
    html = cliente_web.get("/reservar?restaurante_id=2").text
    assert "ESTÁS RESERVANDO EN" in html and "La Cocina del Turno Noche" in html
    assert "/carta?restaurante_id=2" in html
    assert "ESTÁS RESERVANDO EN" not in cliente_web.get("/reservar").text      # sin restaurante elegido no hay aviso


def test_autosembrar_siembra_bd_vacia_y_no_borra_existente(tmp_path, monkeypatch):
    from app import config
    from app.datos.conexion import ConexionBD
    ruta = str(tmp_path / "auto.db")
    ConexionBD.reiniciar(ruta)
    monkeypatch.setattr(config, "AUTOSEMBRAR", True)
    with TestClient(app) as c:                                   # el lifespan siembra la BD vacía
        assert "Slice Palace Medianoche" in c.get("/restaurantes").text
    with ConexionBD().sesion() as con:
        con.execute("UPDATE restaurante SET nombre = 'Editado' WHERE id = 1")
    with TestClient(app) as c:                                   # segundo arranque: no resiembra ni pisa datos
        assert "Editado" in c.get("/restaurantes").text

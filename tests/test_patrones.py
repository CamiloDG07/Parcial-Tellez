"""Una prueba (o más) por patrón de diseño."""
import logging
import threading
from datetime import date

import pytest

from app.datos.conexion import ConexionBD
from app.datos.dao import HorarioDAO, MesaDAO, ReservaDAO
from app.datos.modelos import Administrador, Cliente
from app.dependencias import auth_service, fachada, reserva_service, reserva_service_real, usuario_dao
from app.negocio.excepciones import NoAutorizadoError, ReglaNegocioError
from app.negocio.patrones.creacionales.reserva_builder import ReservaBuilder, ReservaDirector
from app.negocio.patrones.creacionales.usuario_factory import UsuarioFactory
from app.negocio.patrones.estructurales.reserva_proxy import ReservaServiceProxy
from app.negocio.servicios.reserva_service import IReservaService
from app.seguridad import hashear_password
from tests.conftest import proximo_dia


def datos(**extra):
    base = {"restaurante_id": 1, "fecha": proximo_dia(), "hora": "19:00", "personas": 2, "mesa_id": 1, "notas": ""}
    base.update(extra)
    return base


@pytest.fixture()
def cliente(bd):
    return auth_service.autenticar("cliente@demo.com", "Cliente123!")


@pytest.fixture()
def otro_cliente(bd):
    nuevo = UsuarioFactory.crear("cliente", {"nombre": "Otro", "email": "otro@demo.com",
                                             "password_hash": hashear_password("Otro12345!")})
    nuevo.id = usuario_dao.insertar(nuevo)
    return nuevo


# ---- Singleton ----
def test_singleton_misma_instancia(bd):
    assert ConexionBD() is ConexionBD()


def test_singleton_seguro_con_hilos(bd):
    ConexionBD.reiniciar()
    instancias = []
    hilos = [threading.Thread(target=lambda: instancias.append(ConexionBD())) for _ in range(20)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert len({id(i) for i in instancias}) == 1


def test_singleton_activa_claves_foraneas(bd):
    with ConexionBD().sesion() as con:
        assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1


# ---- Factory Method ----
def test_factory_crea_subclase_segun_rol():
    c = UsuarioFactory.crear("cliente", {"nombre": "A", "email": " A@X.com ", "password_hash": "h"})
    a = UsuarioFactory.crear("administrador", {"nombre": "B", "email": "b@x.com", "password_hash": "h"})
    assert isinstance(c, Cliente) and isinstance(a, Administrador)
    assert c.email == "a@x.com"
    assert c.ruta_inicio() == "/restaurantes" and a.ruta_inicio() == "/admin"
    assert "reservar" in c.permisos() and "reservar" not in a.permisos()
    assert "gestionar_mesas" in a.permisos()


def test_factory_rechaza_rol_desconocido():
    with pytest.raises(ReglaNegocioError):
        UsuarioFactory.crear("root", {"nombre": "x", "email": "x@x.com"})


def test_dao_y_login_usan_la_factory(bd):
    assert isinstance(usuario_dao.obtener_por_email("admin@demo.com"), Administrador)
    assert isinstance(auth_service.autenticar("cliente@demo.com", "Cliente123!"), Cliente)


# ---- Builder ----
def nuevo_builder():
    return ReservaBuilder(MesaDAO(), HorarioDAO(), ReservaDAO())


def test_builder_falla_sin_mesa(bd):
    with pytest.raises(ReglaNegocioError, match="mesa"):
        (nuevo_builder().para_cliente(1).en_restaurante(1).el_dia(proximo_dia())
         .a_las("19:00").para_personas(2).build())


def test_builder_interfaz_fluida_construye_reserva(bd):
    r = (nuevo_builder().para_cliente(1).en_restaurante(1).el_dia(date.fromisoformat(proximo_dia()))
         .a_las("19:00").para_personas(2).en_mesa(1).con_notas("  cumpleaños  ").build())
    assert (r.estado, r.notas, r.mesa_id, r.id) == ("PENDIENTE", "cumpleaños", 1, None)


def test_builder_valida_en_build(bd):
    with pytest.raises(ReglaNegocioError, match="futuras"):
        (nuevo_builder().para_cliente(1).en_restaurante(1).el_dia("2020-01-01")
         .a_las("19:00").para_personas(2).en_mesa(1).build())


def test_director_reserva_rapida(bd):
    r = ReservaDirector(nuevo_builder()).reserva_rapida(1, 1, proximo_dia(), "13:00", 1)
    assert r.num_personas == 2 and r.hora == "13:00"


def test_el_servicio_construye_por_el_builder(cliente, monkeypatch):
    llamadas = []
    original = ReservaBuilder.build
    monkeypatch.setattr(ReservaBuilder, "build", lambda self: (llamadas.append(1), original(self))[1])
    reserva_service.crear_reserva(cliente, datos())
    assert llamadas == [1]


# ---- Facade ----
def test_facade_usa_el_proxy_y_no_el_servicio_real():
    assert isinstance(fachada._reservas, ReservaServiceProxy)
    assert fachada._reservas is not reserva_service_real
    assert isinstance(fachada._reservas, IReservaService)


def test_facade_disponibilidad_y_reserva_con_mesa_automatica(cliente):
    disp = fachada.buscar_disponibilidad(1, proximo_dia(), 3)
    assert disp["abierto"] and disp["franjas"][0]["hora"] == "12:00" and disp["franjas"][-1]["hora"] == "21:00"
    # 3 personas → mesas de 4+ (ids 3,4,5,6)
    assert set(disp["franjas"][0]["mesas_libres"]) == {3, 4, 5, 6}
    r = fachada.reservar(cliente, datos(personas=3, mesa_id=None))
    assert r.mesa_id == 3                                   # la más ajustada (4 plazas, menor número)
    despues = fachada.buscar_disponibilidad(1, proximo_dia(), 3)
    franja = next(f for f in despues["franjas"] if f["hora"] == "19:00")
    assert 3 not in franja["mesas_libres"]


def test_facade_mis_reservas_y_cancelar(cliente):
    r = fachada.reservar(cliente, datos(mesa_id=None))
    assert [f["reserva"].id for f in fachada.mis_reservas(cliente)] == [r.id]
    fachada.cancelar(cliente, r.id)
    assert fachada.mis_reservas(cliente)[0]["reserva"].estado == "CANCELADA"


# ---- Proxy ----
def test_proxy_rechaza_cancelar_reserva_ajena(cliente, otro_cliente):
    r = reserva_service.crear_reserva(cliente, datos())
    with pytest.raises(NoAutorizadoError):
        reserva_service.cancelar_reserva(otro_cliente, r.id)
    assert reserva_service.obtener(cliente, r.id).estado == "PENDIENTE"


def test_proxy_rechaza_ver_reserva_ajena(cliente, otro_cliente):
    r = reserva_service.crear_reserva(cliente, datos())
    with pytest.raises(NoAutorizadoError):
        reserva_service.obtener(otro_cliente, r.id)


def test_proxy_admin_solo_gestiona_su_restaurante(cliente):
    r = reserva_service.crear_reserva(cliente, datos())            # restaurante 1
    admin2 = auth_service.autenticar("admin2@demo.com", "Admin123!")
    with pytest.raises(NoAutorizadoError):
        reserva_service.confirmar_reserva(admin2, r.id)
    with pytest.raises(NoAutorizadoError):
        reserva_service.listar_por_restaurante(admin2, 1)
    admin1 = auth_service.autenticar("admin@demo.com", "Admin123!")
    reserva_service.confirmar_reserva(admin1, r.id)
    assert reserva_service.obtener(admin1, r.id).estado == "CONFIRMADA"


def test_proxy_cliente_no_confirma_y_admin_no_reserva(cliente):
    r = reserva_service.crear_reserva(cliente, datos())
    with pytest.raises(NoAutorizadoError):
        reserva_service.confirmar_reserva(cliente, r.id)
    admin = auth_service.autenticar("admin@demo.com", "Admin123!")
    with pytest.raises(NoAutorizadoError):
        reserva_service.crear_reserva(admin, datos(hora="20:00"))


def test_proxy_registra_operaciones(cliente, otro_cliente, caplog):
    caplog.set_level(logging.INFO, logger="reservas.proxy")
    r = reserva_service.crear_reserva(cliente, datos())
    with pytest.raises(NoAutorizadoError):
        reserva_service.cancelar_reserva(otro_cliente, r.id)
    texto = caplog.text
    assert "PERMITIDO cliente#" in texto and "crear_reserva" in texto
    assert "DENEGADO cliente#" in texto and "cancelar_reserva" in texto

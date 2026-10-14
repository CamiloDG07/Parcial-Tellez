"""Reglas de negocio de las reservas (§3): horario, capacidad, solapamiento, estados."""
import pytest

from app.dependencias import auth_service, mesa_service, reserva_service
from app.negocio.excepciones import ReglaNegocioError
from tests.conftest import proximo_dia


@pytest.fixture()
def cliente(bd):
    return auth_service.autenticar("cliente@demo.com", "Cliente123!")


def datos(**extra):
    base = {"restaurante_id": 1, "fecha": proximo_dia(), "hora": "19:00", "personas": 2, "mesa_id": 1, "notas": ""}
    base.update(extra)
    return base


def test_reserva_valida_queda_pendiente(cliente):
    r = reserva_service.crear_reserva(cliente, datos())
    assert r.id and r.estado == "PENDIENTE" and r.mesa_id == 1


def test_rechaza_fecha_pasada(cliente):
    with pytest.raises(ReglaNegocioError, match="futuras"):
        reserva_service.crear_reserva(cliente, datos(fecha="2020-01-01"))


@pytest.mark.parametrize("hora", ["08:00", "11:30", "21:30", "22:30"])
def test_rechaza_fuera_de_horario(cliente, hora):
    """El restaurante 1 abre 12:00–23:00 y la reserva dura 120 min: la última hora válida es 21:00."""
    with pytest.raises(ReglaNegocioError, match="horario"):
        reserva_service.crear_reserva(cliente, datos(hora=hora))


def test_acepta_limites_del_horario(cliente):
    reserva_service.crear_reserva(cliente, datos(hora="12:00", mesa_id=1))
    reserva_service.crear_reserva(cliente, datos(hora="21:00", mesa_id=1))


def test_rechaza_dia_cerrado(cliente):
    mesa = mesa_service.listar(2)[0]          # restaurante 2 cierra los lunes
    with pytest.raises(ReglaNegocioError, match="cerrado"):
        reserva_service.crear_reserva(cliente, datos(restaurante_id=2, mesa_id=mesa.id, fecha=proximo_dia(0)))


def test_rechaza_capacidad_insuficiente(cliente):
    with pytest.raises(ReglaNegocioError, match="máximo"):
        reserva_service.crear_reserva(cliente, datos(personas=3, mesa_id=1))   # mesa 1 admite 2


def test_rechaza_mesa_inactiva(cliente, bd):
    admin = auth_service.autenticar("admin@demo.com", "Admin123!")
    mesa_service.actualizar(admin, 1, 1, 2, "Salón", False)
    with pytest.raises(ReglaNegocioError, match="no está activa"):
        reserva_service.crear_reserva(cliente, datos())


def test_rechaza_mesa_de_otro_restaurante(cliente):
    otra = mesa_service.listar(2)[0]
    with pytest.raises(ReglaNegocioError, match="no existe en este restaurante"):
        reserva_service.crear_reserva(cliente, datos(mesa_id=otra.id))


def test_rechaza_solapamiento(cliente):
    reserva_service.crear_reserva(cliente, datos(hora="19:00"))
    for hora in ("19:00", "18:00", "20:30", "19:30"):      # todas caen dentro de [19:00, 21:00) o lo cruzan
        with pytest.raises(ReglaNegocioError, match="ya está reservada"):
            reserva_service.crear_reserva(cliente, datos(hora=hora))


def test_reservas_contiguas_no_se_solapan(cliente):
    reserva_service.crear_reserva(cliente, datos(hora="19:00"))
    reserva_service.crear_reserva(cliente, datos(hora="21:00"))     # empieza justo cuando termina la otra
    reserva_service.crear_reserva(cliente, datos(hora="17:00"))     # termina justo cuando empieza la primera


def test_misma_hora_en_otra_mesa_si_es_posible(cliente):
    reserva_service.crear_reserva(cliente, datos(mesa_id=1))
    reserva_service.crear_reserva(cliente, datos(mesa_id=2))


def test_cancelada_libera_la_mesa(cliente):
    r = reserva_service.crear_reserva(cliente, datos())
    reserva_service.cancelar_reserva(cliente, r.id)
    reserva_service.crear_reserva(cliente, datos())                  # ya no se considera ocupada


def test_estados_no_permiten_reabrir(cliente):
    r = reserva_service.crear_reserva(cliente, datos())
    reserva_service.cancelar_reserva(cliente, r.id)
    admin = auth_service.autenticar("admin@demo.com", "Admin123!")
    with pytest.raises(ReglaNegocioError, match="No se puede pasar"):
        reserva_service.confirmar_reserva(admin, r.id)


def test_confirmar_cambia_estado(cliente):
    r = reserva_service.crear_reserva(cliente, datos())
    admin = auth_service.autenticar("admin@demo.com", "Admin123!")
    reserva_service.confirmar_reserva(admin, r.id)
    assert reserva_service.obtener(cliente, r.id).estado == "CONFIRMADA"

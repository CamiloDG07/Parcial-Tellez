"""Patrón Proxy de protección para el servicio de reservas."""
from __future__ import annotations

import logging

from app.datos.modelos import Mesa, Reserva, Usuario
from app.negocio.excepciones import NoAutorizadoError
from app.negocio.servicios.reserva_service import IReservaService
from app.negocio.servicios.restaurante_service import RestauranteService

log = logging.getLogger("reservas.proxy")


class ReservaServiceProxy(IReservaService):
    """PATRÓN ESTRUCTURAL · Proxy de protección (rol: Proxy).

    Implementa la misma interfaz `IReservaService` que el servicio real (RealSubject),
    comprueba rol y propiedad del recurso (regla 4) y registra cada operación antes de delegar.
    """

    def __init__(self, real: IReservaService, restaurantes: RestauranteService) -> None:
        self._real, self._restaurantes = real, restaurantes

    # --- utilidades ---
    def _registrar(self, actor: Usuario | None, operacion: str, detalle: str = "", permitido: bool = True) -> None:
        quien = f"{actor.rol}#{actor.id}" if actor else "anonimo"
        nivel = logging.INFO if permitido else logging.WARNING
        log.log(nivel, "%s %s %s %s", "PERMITIDO" if permitido else "DENEGADO", quien, operacion, detalle)

    def _denegar(self, actor: Usuario | None, operacion: str, detalle: str, mensaje: str) -> None:
        self._registrar(actor, operacion, detalle, permitido=False)
        raise NoAutorizadoError(mensaje)

    def _es_admin_del_restaurante(self, actor: Usuario, restaurante_id: int) -> bool:
        try:
            self._restaurantes.verificar_admin(actor, restaurante_id)
            return True
        except NoAutorizadoError:
            return False

    def _puede_gestionar(self, actor: Usuario, reserva: Reserva) -> bool:
        """Dueño de la reserva (cliente) o administrador del restaurante de la reserva."""
        if actor.rol == "cliente":
            return reserva.usuario_id == actor.id
        return self._es_admin_del_restaurante(actor, reserva.restaurante_id)

    # --- operaciones de la interfaz ---
    def crear_reserva(self, actor: Usuario, datos: dict) -> Reserva:
        if "reservar" not in actor.permisos():
            self._denegar(actor, "crear_reserva", str(datos.get("restaurante_id")),
                          "Solo los clientes pueden crear reservas.")
        self._registrar(actor, "crear_reserva", f"restaurante={datos.get('restaurante_id')}")
        return self._real.crear_reserva(actor, datos)

    def cancelar_reserva(self, actor: Usuario, reserva_id: int) -> None:
        reserva = self._real.obtener(actor, reserva_id)
        if not self._puede_gestionar(actor, reserva):
            self._denegar(actor, "cancelar_reserva", f"reserva={reserva_id}",
                          "No puedes cancelar esta reserva.")
        self._registrar(actor, "cancelar_reserva", f"reserva={reserva_id}")
        self._real.cancelar_reserva(actor, reserva_id)

    def confirmar_reserva(self, actor: Usuario, reserva_id: int) -> None:
        reserva = self._real.obtener(actor, reserva_id)
        if actor.rol != "administrador" or not self._es_admin_del_restaurante(actor, reserva.restaurante_id):
            self._denegar(actor, "confirmar_reserva", f"reserva={reserva_id}",
                          "Solo el administrador del restaurante puede confirmar reservas.")
        self._registrar(actor, "confirmar_reserva", f"reserva={reserva_id}")
        self._real.confirmar_reserva(actor, reserva_id)

    def obtener(self, actor: Usuario, reserva_id: int) -> Reserva:
        reserva = self._real.obtener(actor, reserva_id)
        if not self._puede_gestionar(actor, reserva):
            self._denegar(actor, "obtener", f"reserva={reserva_id}", "No puedes ver esta reserva.")
        return reserva

    def mis_reservas(self, actor: Usuario) -> list[Reserva]:
        self._registrar(actor, "mis_reservas")
        return self._real.mis_reservas(actor)

    def listar_por_restaurante(self, actor: Usuario, restaurante_id: int, fecha: str | None = None,
                               estado: str | None = None) -> list[Reserva]:
        if not self._es_admin_del_restaurante(actor, restaurante_id):
            self._denegar(actor, "listar_por_restaurante", f"restaurante={restaurante_id}",
                          "No administras este restaurante.")
        self._registrar(actor, "listar_por_restaurante", f"restaurante={restaurante_id}")
        return self._real.listar_por_restaurante(actor, restaurante_id, fecha, estado)

    def mesas_libres(self, restaurante_id: int, fecha: str, hora: str, personas: int) -> list[Mesa]:
        return self._real.mesas_libres(restaurante_id, fecha, hora, personas)

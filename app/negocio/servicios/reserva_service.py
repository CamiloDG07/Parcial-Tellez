"""Servicio de reservas e interfaz común con el Proxy."""
from __future__ import annotations

import threading
from abc import ABC, abstractmethod

from app import config
from app.datos.dao import ReservaDAO
from app.datos.modelos import Mesa, Reserva, Usuario
from app.negocio.excepciones import NoEncontradoError, ReglaNegocioError
from app.negocio.patrones.creacionales.reserva_builder import ReservaBuilder, hay_solape
from app.negocio.patrones.estructurales.cobro_decorator import instantanea
from app.negocio.servicios.restaurante_service import MesaService

TRANSICIONES = {
    "PENDIENTE": {"CONFIRMADA", "CANCELADA"},
    "CONFIRMADA": {"CANCELADA"},
    "CANCELADA": set(),
}


class IReservaService(ABC):
    """PATRÓN ESTRUCTURAL · Proxy (rol: Subject): interfaz común del servicio real y de su proxy."""

    @abstractmethod
    def crear_reserva(self, actor: Usuario, datos: dict) -> Reserva: ...

    @abstractmethod
    def cancelar_reserva(self, actor: Usuario, reserva_id: int) -> None: ...

    @abstractmethod
    def confirmar_reserva(self, actor: Usuario, reserva_id: int) -> None: ...

    @abstractmethod
    def obtener(self, actor: Usuario, reserva_id: int) -> Reserva: ...

    @abstractmethod
    def mis_reservas(self, actor: Usuario) -> list[Reserva]: ...

    @abstractmethod
    def listar_por_restaurante(self, actor: Usuario, restaurante_id: int, fecha: str | None = None,
                               estado: str | None = None) -> list[Reserva]: ...

    @abstractmethod
    def mesas_libres(self, restaurante_id: int, fecha: str, hora: str, personas: int) -> list[Mesa]: ...


class ReservaService(IReservaService):
    """PATRÓN ESTRUCTURAL · Proxy (rol: RealSubject). Contiene la lógica; NO comprueba permisos
    (eso lo hace `ReservaServiceProxy`). Construye cada reserva con `ReservaBuilder`."""

    # Dos defensas contra la doble reserva: el cerrojo (hilos de un proceso) y, sobre todo, la transacción
    # BEGIN IMMEDIATE de `insertar_si_libre` (varios procesos o conexiones).
    _cerrojo = threading.Lock()

    def __init__(self, dao: ReservaDAO, mesas: MesaService, builder_factory) -> None:
        self._dao, self._mesas, self._nuevo_builder = dao, mesas, builder_factory

    def crear_reserva(self, actor: Usuario, datos: dict) -> Reserva:
        constructor: ReservaBuilder = (self._nuevo_builder()
                                       .para_cliente(actor.id)
                                       .en_restaurante(datos.get("restaurante_id"))
                                       .el_dia(datos.get("fecha"))
                                       .a_las(datos.get("hora"))
                                       .para_personas(datos.get("personas"))
                                       .en_mesa(datos.get("mesa_id"))
                                       .con_notas(datos.get("notas", ""))
                                       .con_items(datos.get("items")))
        with self._cerrojo:
            reserva = constructor.build()
            for campo, valor in instantanea(reserva.items).items():      # cobro congelado al crear (auditable)
                setattr(reserva, campo, valor)
            nuevo_id = self._dao.insertar_si_libre(reserva, config.DURACION_RESERVA_MIN)
        if nuevo_id is None:                        # otra reserva ganó la mesa entre la validación y el guardado
            raise ReglaNegocioError("La mesa ya está reservada en ese horario.")
        reserva.id = nuevo_id
        return reserva

    def obtener(self, actor: Usuario, reserva_id: int) -> Reserva:
        reserva = self._dao.obtener_por_id(reserva_id)
        if reserva is None:
            raise NoEncontradoError("La reserva no existe.")
        return reserva

    def _cambiar(self, reserva_id: int, nuevo: str) -> None:
        reserva = self.obtener(None, reserva_id)  # type: ignore[arg-type]
        if nuevo not in TRANSICIONES[reserva.estado]:
            raise ReglaNegocioError(f"No se puede pasar de {reserva.estado} a {nuevo}.")
        self._dao.cambiar_estado(reserva_id, nuevo)

    def cancelar_reserva(self, actor: Usuario, reserva_id: int) -> None:
        self._cambiar(reserva_id, "CANCELADA")

    def confirmar_reserva(self, actor: Usuario, reserva_id: int) -> None:
        self._cambiar(reserva_id, "CONFIRMADA")

    def mis_reservas(self, actor: Usuario) -> list[Reserva]:
        return self._dao.listar_por_usuario(actor.id)

    def listar_por_restaurante(self, actor: Usuario, restaurante_id: int, fecha: str | None = None,
                               estado: str | None = None) -> list[Reserva]:
        return self._dao.listar_por_restaurante(restaurante_id, fecha or None, estado or None)

    def mesas_libres(self, restaurante_id: int, fecha: str, hora: str, personas: int) -> list[Mesa]:
        """Mesas activas con capacidad suficiente y sin solapamiento en esa franja."""
        ocupadas = {r.mesa_id for r in self._dao.listar_activas_por_restaurante_y_fecha(restaurante_id, fecha)
                    if hay_solape(r.hora, hora)}
        return [m for m in self._mesas.listar(restaurante_id)
                if m.activa and m.capacidad >= personas and m.id not in ocupadas]

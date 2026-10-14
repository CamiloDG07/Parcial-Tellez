"""Patrón Builder para construir reservas válidas."""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Callable

from app import config
from app.datos.dao import HorarioDAO, MesaDAO, ProductoDAO, ReservaDAO
from app.datos.modelos import Reserva, ReservaItem
from app.negocio.excepciones import ReglaNegocioError


def a_minutos(hora: str) -> int:
    h, m = hora.split(":")[:2]
    return int(h) * 60 + int(m)


def hay_solape(hora_a: str, hora_b: str, duracion: int = config.DURACION_RESERVA_MIN) -> bool:
    """Dos reservas de duración fija se solapan si sus intervalos [inicio, inicio+duración) se cruzan."""
    a, b = a_minutos(hora_a), a_minutos(hora_b)
    return a < b + duracion and b < a + duracion


class ReservaBuilder:
    """PATRÓN CREACIONAL · Builder (rol: Builder + ConcreteBuilder).

    Interfaz fluida que acumula los datos de la reserva; `build()` (el paso final)
    valida TODAS las reglas de negocio y devuelve el producto `Reserva`.
    """

    def __init__(self, mesa_dao: MesaDAO, horario_dao: HorarioDAO, reserva_dao: ReservaDAO,
                 ahora: Callable[[], datetime] = datetime.now, producto_dao: ProductoDAO | None = None) -> None:
        self._mesa_dao, self._horario_dao, self._reserva_dao, self._ahora = mesa_dao, horario_dao, reserva_dao, ahora
        self._producto_dao = producto_dao
        self._pedido: list[tuple[int, int]] = []
        self._usuario_id: int | None = None
        self._restaurante_id: int | None = None
        self._fecha: date | str | None = None
        self._hora: str | None = None
        self._personas: int | None = None
        self._mesa_id: int | None = None
        self._notas = ""

    # --- pasos del constructor (interfaz fluida) ---
    def para_cliente(self, usuario_id: int) -> "ReservaBuilder":
        self._usuario_id = usuario_id
        return self

    def en_restaurante(self, restaurante_id: int) -> "ReservaBuilder":
        self._restaurante_id = restaurante_id
        return self

    def el_dia(self, fecha: date | str) -> "ReservaBuilder":
        self._fecha = fecha
        return self

    def a_las(self, hora: str) -> "ReservaBuilder":
        self._hora = hora
        return self

    def para_personas(self, personas: int) -> "ReservaBuilder":
        self._personas = personas
        return self

    def en_mesa(self, mesa_id: int) -> "ReservaBuilder":
        self._mesa_id = mesa_id
        return self

    def con_notas(self, notas: str) -> "ReservaBuilder":
        self._notas = (notas or "").strip()[:300]
        return self

    def con_items(self, items: list[tuple[int, int]] | None) -> "ReservaBuilder":
        """Pre-pedido: lista de (producto_id, cantidad). Los precios se leen de la BD en `build()`."""
        self._pedido = list(items or [])
        return self

    # --- construcción ---
    def build(self) -> Reserva:
        faltan = [n for n, v in (("cliente", self._usuario_id), ("restaurante", self._restaurante_id),
                                 ("fecha", self._fecha), ("hora", self._hora),
                                 ("número de personas", self._personas), ("mesa", self._mesa_id)) if v in (None, "")]
        if faltan:
            raise ReglaNegocioError("Falta indicar: " + ", ".join(faltan) + ".")

        try:
            fecha = self._fecha if isinstance(self._fecha, date) else date.fromisoformat(str(self._fecha))
            h, m = str(self._hora).split(":")[:2]
            hora_t = time(int(h), int(m))
        except (ValueError, TypeError):
            raise ReglaNegocioError("La fecha o la hora no tienen un formato válido.") from None
        hora = hora_t.strftime("%H:%M")
        if not isinstance(self._personas, int) or self._personas <= 0:
            raise ReglaNegocioError("El número de personas debe ser mayor que cero.")

        # Regla 1: futura y dentro del horario del restaurante
        if datetime.combine(fecha, hora_t) <= self._ahora():
            raise ReglaNegocioError("La fecha y hora de la reserva deben ser futuras.")
        horario = self._horario_dao.obtener_por_dia(self._restaurante_id, fecha.weekday())
        if horario is None:
            raise ReglaNegocioError("El restaurante está cerrado ese día.")
        inicio, fin = a_minutos(horario.hora_apertura), a_minutos(horario.hora_cierre)
        if not (inicio <= a_minutos(hora) and a_minutos(hora) + config.DURACION_RESERVA_MIN <= fin):
            raise ReglaNegocioError(
                f"La hora debe estar dentro del horario ({horario.hora_apertura}–{horario.hora_cierre}) "
                f"y dejar {config.DURACION_RESERVA_MIN} min antes del cierre.")

        # Regla 2: mesa del restaurante, activa y con capacidad suficiente
        mesa = self._mesa_dao.obtener_por_id(self._mesa_id)
        if mesa is None or mesa.restaurante_id != self._restaurante_id:
            raise ReglaNegocioError("La mesa no existe en este restaurante.")
        if not mesa.activa:
            raise ReglaNegocioError("La mesa seleccionada no está activa.")
        if mesa.capacidad < self._personas:
            raise ReglaNegocioError(f"La mesa {mesa.numero} admite {mesa.capacidad} personas como máximo.")

        # Regla 3: sin solapamientos (las canceladas se ignoran en el DAO)
        for existente in self._reserva_dao.listar_activas_por_mesa_y_fecha(mesa.id, fecha.isoformat()):
            if hay_solape(existente.hora, hora):
                raise ReglaNegocioError("La mesa ya está reservada en ese horario.")

        # Pre-pedido: productos del mismo restaurante, disponibles; el precio sale de la BD, nunca del navegador
        items = self._construir_items()

        return Reserva(id=None, usuario_id=self._usuario_id, restaurante_id=self._restaurante_id,
                       mesa_id=mesa.id, fecha=fecha.isoformat(), hora=hora, num_personas=self._personas,
                       estado="PENDIENTE", notas=self._notas,
                       creado_en=self._ahora().isoformat(timespec="seconds"), items=items)

    def _construir_items(self) -> list[ReservaItem]:
        if not self._pedido:
            return []
        if self._producto_dao is None:
            raise ReglaNegocioError("No se puede validar el pre-pedido.")
        acumulado: dict[int, int] = {}
        for producto_id, cantidad in self._pedido:
            if not isinstance(cantidad, int) or not 1 <= cantidad <= 20:
                raise ReglaNegocioError("La cantidad de cada plato debe estar entre 1 y 20.")
            acumulado[producto_id] = acumulado.get(producto_id, 0) + cantidad
        if len(acumulado) > 30 or any(c > 20 for c in acumulado.values()):
            raise ReglaNegocioError("El pre-pedido es demasiado grande.")
        items = []
        for producto_id, cantidad in acumulado.items():
            producto = self._producto_dao.obtener_por_id(producto_id)
            if producto is None or producto.restaurante_id != self._restaurante_id:
                raise ReglaNegocioError("Hay un producto que no pertenece a este restaurante.")
            if not producto.disponible:
                raise ReglaNegocioError(f"«{producto.nombre}» no está disponible.")
            items.append(ReservaItem(None, None, producto.id, cantidad, producto.precio_cop))
        return items


class ReservaDirector:
    """PATRÓN CREACIONAL · Builder (rol: Director): receta predefinida de "reserva rápida"."""

    def __init__(self, builder: ReservaBuilder) -> None:
        self._builder = builder

    def reserva_rapida(self, usuario_id: int, restaurante_id: int, fecha: date | str,
                       hora: str, mesa_id: int) -> Reserva:
        """Mesa para 2 personas sin notas."""
        return (self._builder.para_cliente(usuario_id).en_restaurante(restaurante_id)
                .el_dia(fecha).a_las(hora).para_personas(2).en_mesa(mesa_id).build())

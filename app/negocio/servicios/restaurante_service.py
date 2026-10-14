"""Servicios de restaurantes, mesas y horarios."""
from __future__ import annotations

import sqlite3
from datetime import date

from app import config
from app.datos.dao import HorarioDAO, MesaDAO, RestauranteDAO
from app.datos.modelos import Horario, Mesa, Restaurante, Usuario
from app.negocio.excepciones import NoAutorizadoError, NoEncontradoError, ReglaNegocioError
from app.negocio.patrones.creacionales.reserva_builder import a_minutos


class RestauranteService:
    def __init__(self, dao: RestauranteDAO) -> None:
        self._dao = dao

    def buscar(self, nombre: str = "", tipo_cocina: str = "", ciudad: str = "") -> list[Restaurante]:
        return self._dao.buscar(nombre.strip(), tipo_cocina.strip(), ciudad.strip())

    def obtener(self, restaurante_id: int) -> Restaurante:
        r = self._dao.obtener_por_id(restaurante_id)
        if r is None:
            raise NoEncontradoError("El restaurante no existe.")
        return r

    def del_administrador(self, actor: Usuario) -> Restaurante:
        r = self._dao.obtener_por_admin(actor.id) if actor.id else None
        if r is None:
            raise NoEncontradoError("Tu usuario no administra ningún restaurante.")
        return r

    def filtros(self) -> tuple[list[str], list[str]]:
        return self._dao.listar_cocinas_y_ciudades()

    def verificar_admin(self, actor: Usuario, restaurante_id: int) -> Restaurante:
        """Regla 4: un administrador solo gestiona su restaurante."""
        r = self.obtener(restaurante_id)
        if actor.rol != "administrador" or r.admin_id != actor.id:
            raise NoAutorizadoError("No administras este restaurante.")
        return r


class MesaService:
    def __init__(self, dao: MesaDAO, restaurantes: RestauranteService) -> None:
        self._dao, self._restaurantes = dao, restaurantes

    def listar(self, restaurante_id: int) -> list[Mesa]:
        return self._dao.listar_por_restaurante(restaurante_id)

    def obtener(self, mesa_id: int) -> Mesa:
        m = self._dao.obtener_por_id(mesa_id)
        if m is None:
            raise NoEncontradoError("La mesa no existe.")
        return m

    def _validar(self, numero: int, capacidad: int) -> None:
        if numero <= 0 or capacidad <= 0:
            raise ReglaNegocioError("El número de mesa y la capacidad deben ser mayores que cero.")
        if capacidad > 30:
            raise ReglaNegocioError("La capacidad máxima por mesa es 30.")

    def crear(self, actor: Usuario, restaurante_id: int, numero: int, capacidad: int,
              ubicacion: str, activa: bool) -> int:
        self._restaurantes.verificar_admin(actor, restaurante_id)
        self._validar(numero, capacidad)
        if self._dao.obtener_por_numero(restaurante_id, numero):
            raise ReglaNegocioError(f"Ya existe la mesa {numero} en este restaurante.")
        return self._dao.insertar(Mesa(None, restaurante_id, numero, capacidad, ubicacion.strip()[:60], activa))

    def actualizar(self, actor: Usuario, mesa_id: int, numero: int, capacidad: int,
                   ubicacion: str, activa: bool) -> None:
        mesa = self.obtener(mesa_id)
        self._restaurantes.verificar_admin(actor, mesa.restaurante_id)
        self._validar(numero, capacidad)
        otra = self._dao.obtener_por_numero(mesa.restaurante_id, numero)
        if otra and otra.id != mesa.id:
            raise ReglaNegocioError(f"Ya existe la mesa {numero} en este restaurante.")
        mesa.numero, mesa.capacidad, mesa.ubicacion, mesa.activa = numero, capacidad, ubicacion.strip()[:60], activa
        self._dao.actualizar(mesa)

    def eliminar(self, actor: Usuario, mesa_id: int) -> None:
        mesa = self.obtener(mesa_id)
        self._restaurantes.verificar_admin(actor, mesa.restaurante_id)
        try:
            self._dao.eliminar(mesa_id)
        except sqlite3.IntegrityError:
            raise ReglaNegocioError("La mesa tiene reservas asociadas; desactívala en lugar de eliminarla.") from None


class HorarioService:
    def __init__(self, dao: HorarioDAO, restaurantes: RestauranteService) -> None:
        self._dao, self._restaurantes = dao, restaurantes

    def listar(self, restaurante_id: int) -> list[Horario]:
        return self._dao.listar_por_restaurante(restaurante_id)

    def obtener_por_dia(self, restaurante_id: int, dia: int) -> Horario | None:
        return self._dao.obtener_por_dia(restaurante_id, dia)

    def guardar(self, actor: Usuario, restaurante_id: int, dia: int, apertura: str, cierre: str) -> None:
        """Crea o reemplaza el horario de ese día (UNIQUE restaurante+día)."""
        self._restaurantes.verificar_admin(actor, restaurante_id)
        if not 0 <= dia <= 6:
            raise ReglaNegocioError("Día de la semana inválido.")
        try:
            ok = a_minutos(apertura) < a_minutos(cierre)
        except (ValueError, AttributeError):
            raise ReglaNegocioError("Las horas deben tener el formato HH:MM.") from None
        if not ok:
            raise ReglaNegocioError("La hora de cierre debe ser posterior a la de apertura.")
        existente = self._dao.obtener_por_dia(restaurante_id, dia)
        if existente:
            existente.hora_apertura, existente.hora_cierre = apertura, cierre
            self._dao.actualizar(existente)
        else:
            self._dao.insertar(Horario(None, restaurante_id, dia, apertura, cierre))

    def eliminar(self, actor: Usuario, horario_id: int) -> None:
        h = self._dao.obtener_por_id(horario_id)
        if h is None:
            raise NoEncontradoError("El horario no existe.")
        self._restaurantes.verificar_admin(actor, h.restaurante_id)
        self._dao.eliminar(horario_id)

    def franjas(self, restaurante_id: int, fecha: date) -> list[str]:
        """Horas de inicio ofrecidas ese día: cada PASO_FRANJA_MIN, dejando DURACION_RESERVA_MIN antes del cierre."""
        h = self._dao.obtener_por_dia(restaurante_id, fecha.weekday())
        if h is None:
            return []
        inicio, fin = a_minutos(h.hora_apertura), a_minutos(h.hora_cierre)
        return [f"{m // 60:02d}:{m % 60:02d}"
                for m in range(inicio, fin - config.DURACION_RESERVA_MIN + 1, config.PASO_FRANJA_MIN)]

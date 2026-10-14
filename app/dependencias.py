"""Raíz de composición: construye y conecta DAO, servicios, proxy y fachada."""
from __future__ import annotations

from app.datos.dao import HorarioDAO, MesaDAO, ReservaDAO, RestauranteDAO, UsuarioDAO
from app.negocio.patrones.creacionales.reserva_builder import ReservaBuilder
from app.negocio.patrones.creacionales.usuario_factory import UsuarioFactory
from app.negocio.patrones.estructurales.reserva_facade import ReservaFacade
from app.negocio.patrones.estructurales.reserva_proxy import ReservaServiceProxy
from app.negocio.servicios.auth_service import AuthService
from app.negocio.servicios.reserva_service import ReservaService
from app.negocio.servicios.restaurante_service import HorarioService, MesaService, RestauranteService

usuario_dao = UsuarioDAO(UsuarioFactory.crear)      # Factory Method inyectado en el DAO
restaurante_dao = RestauranteDAO()
mesa_dao = MesaDAO()
horario_dao = HorarioDAO()
reserva_dao = ReservaDAO()

auth_service = AuthService(usuario_dao)
restaurante_service = RestauranteService(restaurante_dao)
mesa_service = MesaService(mesa_dao, restaurante_service)
horario_service = HorarioService(horario_dao, restaurante_service)

reserva_service_real = ReservaService(
    reserva_dao, mesa_service,
    builder_factory=lambda: ReservaBuilder(mesa_dao, horario_dao, reserva_dao))
reserva_service = ReservaServiceProxy(reserva_service_real, restaurante_service)   # los controladores solo ven el proxy

fachada = ReservaFacade(reserva_service, restaurante_service, mesa_service, horario_service, auth_service)

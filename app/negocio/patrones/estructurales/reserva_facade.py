"""Patrón Facade: punto único de entrada para los controladores del cliente."""
from __future__ import annotations

from datetime import date

from app.datos.modelos import Reserva, Restaurante, Usuario
from app.negocio.excepciones import ReglaNegocioError
from app.negocio.servicios.auth_service import AuthService
from app.negocio.servicios.reserva_service import IReservaService
from app.negocio.servicios.restaurante_service import HorarioService, MesaService, RestauranteService


class ReservaFacade:
    """PATRÓN ESTRUCTURAL · Facade (rol: Facade).

    Orquesta `RestauranteService`, `MesaService`, `HorarioService` y el servicio de reservas
    (recibido como `IReservaService`: en producción es el `ReservaServiceProxy`, nunca el real)
    detrás de cuatro operaciones simples: buscar_disponibilidad, reservar, cancelar y mis_reservas.
    """

    def __init__(self, reservas: IReservaService, restaurantes: RestauranteService,
                 mesas: MesaService, horarios: HorarioService, usuarios: AuthService) -> None:
        self._reservas, self._restaurantes = reservas, restaurantes
        self._mesas, self._horarios, self._usuarios = mesas, horarios, usuarios

    @staticmethod
    def _parsear_fecha(texto: str) -> date:
        try:
            return date.fromisoformat(texto)
        except (ValueError, TypeError):
            raise ReglaNegocioError("La fecha no tiene un formato válido (AAAA-MM-DD).") from None

    # --- catálogo ---
    def listar_restaurantes(self, nombre: str = "", tipo_cocina: str = "", ciudad: str = "") -> list[Restaurante]:
        return self._restaurantes.buscar(nombre, tipo_cocina, ciudad)

    def obtener_restaurante(self, restaurante_id: int) -> Restaurante:
        return self._restaurantes.obtener(restaurante_id)

    def filtros_restaurantes(self) -> tuple[list[str], list[str]]:
        return self._restaurantes.filtros()

    def resumen_restaurante(self, restaurante: Restaurante) -> dict:
        """Datos para las tarjetas: aforo total (suma de capacidades de mesas activas)."""
        mesas = [m for m in self._mesas.listar(restaurante.id) if m.activa]
        return {"restaurante": restaurante, "aforo": sum(m.capacidad for m in mesas), "num_mesas": len(mesas)}

    # --- operaciones principales ---
    def buscar_disponibilidad(self, restaurante_id: int, fecha: str, personas: int) -> dict:
        """Franjas del día con las mesas libres de cada una, más el plano completo de mesas."""
        self._restaurantes.obtener(restaurante_id)
        if personas <= 0:
            raise ReglaNegocioError("El número de personas debe ser mayor que cero.")
        dia = self._parsear_fecha(fecha)
        franjas = []
        for hora in self._horarios.franjas(restaurante_id, dia):
            libres = self._reservas.mesas_libres(restaurante_id, dia.isoformat(), hora, personas)
            franjas.append({"hora": hora, "mesas_libres": [m.id for m in libres]})
        return {
            "restaurante_id": restaurante_id, "fecha": dia.isoformat(), "personas": personas,
            "abierto": bool(franjas),
            "mesas": [{"id": m.id, "numero": m.numero, "capacidad": m.capacidad,
                       "ubicacion": m.ubicacion, "activa": m.activa}
                      for m in self._mesas.listar(restaurante_id)],
            "franjas": franjas,
        }

    def reservar(self, actor: Usuario, datos: dict) -> Reserva:
        """Crea la reserva; si no se eligió mesa, asigna la libre más ajustada a la capacidad."""
        datos = dict(datos)
        if not datos.get("mesa_id"):
            datos["mesa_id"] = self._mesa_automatica(datos)
        return self._reservas.crear_reserva(actor, datos)

    def _mesa_automatica(self, datos: dict) -> int:
        try:
            libres = self._reservas.mesas_libres(int(datos["restaurante_id"]), str(datos["fecha"]),
                                                 str(datos["hora"]), int(datos["personas"]))
        except (KeyError, TypeError, ValueError):
            raise ReglaNegocioError("Completa restaurante, fecha, hora y personas.") from None
        if not libres:
            raise ReglaNegocioError("No hay mesas libres para esa fecha, hora y número de personas.")
        return min(libres, key=lambda m: (m.capacidad, m.numero)).id

    def cancelar(self, actor: Usuario, reserva_id: int) -> None:
        self._reservas.cancelar_reserva(actor, reserva_id)

    def mis_reservas(self, actor: Usuario) -> list[dict]:
        return self.enriquecer(self._reservas.mis_reservas(actor))

    # --- apoyo a las vistas ---
    def enriquecer(self, reservas: list[Reserva]) -> list[dict]:
        """Adjunta restaurante, mesa y cliente a cada reserva para mostrarla."""
        restaurantes, mesas, usuarios = {}, {}, {}
        filas = []
        for r in reservas:
            if r.restaurante_id not in restaurantes:
                restaurantes[r.restaurante_id] = self._restaurantes.obtener(r.restaurante_id)
            if r.mesa_id not in mesas:
                mesas[r.mesa_id] = self._mesas.obtener(r.mesa_id)
            if r.usuario_id not in usuarios:
                usuarios[r.usuario_id] = self._usuarios.obtener(r.usuario_id)
            filas.append({"reserva": r, "restaurante": restaurantes[r.restaurante_id],
                          "mesa": mesas[r.mesa_id], "cliente": usuarios[r.usuario_id]})
        return filas

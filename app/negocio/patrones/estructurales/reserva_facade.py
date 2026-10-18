"""Patrón Facade: punto único de entrada para los controladores del cliente."""
from __future__ import annotations

from datetime import date

from app.datos.modelos import Reserva, ReservaItem, Restaurante, Usuario
from app.negocio.patrones.estructurales.cobro_decorator import desglose, desglose_guardado
from app.negocio.excepciones import ReglaNegocioError
from app.negocio.servicios.auth_service import AuthService
from app.negocio.servicios.carta_service import CarritoService, CartaService
from app.negocio.servicios.reserva_service import IReservaService
from app.negocio.servicios.restaurante_service import HorarioService, MesaService, RestauranteService


class ReservaFacade:
    """PATRÓN ESTRUCTURAL · Facade (rol: Facade).

    Orquesta `RestauranteService`, `MesaService`, `HorarioService` y el servicio de reservas
    (recibido como `IReservaService`: en producción es el `ReservaServiceProxy`, nunca el real)
    detrás de cuatro operaciones simples: buscar_disponibilidad, reservar, cancelar y mis_reservas.
    """

    def __init__(self, reservas: IReservaService, restaurantes: RestauranteService,
                 mesas: MesaService, horarios: HorarioService, usuarios: AuthService,
                 carta: CartaService, carrito: CarritoService) -> None:
        self._reservas, self._restaurantes = reservas, restaurantes
        self._mesas, self._horarios, self._usuarios, self._carta = mesas, horarios, usuarios, carta
        self._carrito = carrito

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

    def contar_proximas(self, actor: Usuario, hoy: str) -> int:
        """Reservas no canceladas desde `hoy` (insignia de la barra superior)."""
        return sum(1 for r in self._reservas.mis_reservas(actor) if r.estado != "CANCELADA" and r.fecha >= hoy)

    def mis_reservas(self, actor: Usuario) -> list[dict]:
        return self.enriquecer(self._reservas.mis_reservas(actor))

    def detalle_reserva(self, actor: Usuario, reserva_id: int) -> dict:
        """Una reserva enriquecida. Pasa por el Proxy: solo la ve su dueño o el administrador del restaurante."""
        return self.enriquecer([self._reservas.obtener(actor, reserva_id)])[0]

    def carta_de(self, restaurante_id: int) -> list[dict]:
        """Carta pública (solo productos disponibles) agrupada por categoría."""
        return self._carta.carta(restaurante_id, solo_disponibles=True)

    # --- pre-pedido (carrito en la sesión del cliente) ---
    def carrito_ver(self, sesion) -> dict:
        return self._carrito.resumen(sesion)

    def carrito_agregar(self, sesion, producto_id: int, cantidad: int) -> dict:
        self._carrito.agregar(sesion, producto_id, cantidad)
        return self._carrito.resumen(sesion)

    def carrito_cambiar(self, sesion, producto_id: int, cantidad: int) -> dict:
        self._carrito.cambiar(sesion, producto_id, cantidad)
        return self._carrito.resumen(sesion)

    def carrito_vaciar(self, sesion) -> dict:
        self._carrito.vaciar(sesion)
        return self._carrito.resumen(sesion)

    def cobro_pre_pedido(self, sesion, con_propina: bool = False) -> dict:
        """Total a pagar del pre-pedido en curso (carrito de la sesión), armado con la cadena de decoradores.
        El cliente solo decide si incluye la propina; los montos se calculan aquí."""
        lineas = self._carrito.resumen(sesion)["lineas"]
        items = [ReservaItem(None, None, l["producto_id"], l["cantidad"], l["precio_cop"]) for l in lineas]
        return desglose(items, con_propina)

    def cobro_de_reserva(self, reserva: Reserva, con_propina: bool = False) -> dict:
        """Total a pagar de una reserva ya creada: la instantánea guardada al crearla (no recalcula con tasas nuevas).
        Si no tiene pre-pedido vigente (p. ej. cancelada) el cobro es cero."""
        if reserva.items and reserva.total_pagar_cop:
            return desglose_guardado(reserva, con_propina)
        return desglose(reserva.items, con_propina)

    def reservar_con_pre_pedido(self, actor: Usuario, datos: dict, sesion) -> Reserva:
        """Reserva usando el carrito de la sesión (debe ser del mismo restaurante); lo vacía al confirmar."""
        datos = dict(datos)
        datos["items"] = self._carrito.items_para_reserva(sesion, int(datos["restaurante_id"]))
        reserva = self.reservar(actor, datos)
        self._carrito.vaciar(sesion)
        return reserva

    # --- apoyo a las vistas ---
    def enriquecer(self, reservas: list[Reserva]) -> list[dict]:
        """Adjunta restaurante, mesa y cliente a cada reserva para mostrarla."""
        restaurantes, mesas, usuarios = {}, {}, {}
        detalles = self._carta.detalles_de([r.id for r in reservas])      # una consulta para todos los pre-pedidos
        filas = []
        for r in reservas:
            if r.restaurante_id not in restaurantes:
                restaurantes[r.restaurante_id] = self._restaurantes.obtener(r.restaurante_id)
            if r.mesa_id not in mesas:
                mesas[r.mesa_id] = self._mesas.obtener(r.mesa_id)
            if r.usuario_id not in usuarios:
                usuarios[r.usuario_id] = self._usuarios.obtener(r.usuario_id)
            detalle = detalles[r.id]
            filas.append({"reserva": r, "restaurante": restaurantes[r.restaurante_id],
                          "mesa": mesas[r.mesa_id], "cliente": usuarios[r.usuario_id],
                          "detalle": detalle, "total_cop": sum(d["item"].subtotal_cop for d in detalle),
                          # total a pagar (sin propina: la elección de propina no se guarda) y propina sugerida
                          "cobro": (desglose_guardado(r) if detalle and r.total_pagar_cop
                                    else desglose([d["item"] for d in detalle], False))})
        return filas

"""Indicadores y series para el panel del administrador."""
from __future__ import annotations

from datetime import date, timedelta

from app import config
from app.datos.dao import HorarioDAO, MesaDAO, ReservaDAO, ReservaItemDAO
from app.negocio.patrones.creacionales.reserva_builder import a_minutos


class EstadisticasService:
    def __init__(self, reservas: ReservaDAO, mesas: MesaDAO, horarios: HorarioDAO, items: ReservaItemDAO) -> None:
        self._reservas, self._mesas, self._horarios, self._items = reservas, mesas, horarios, items

    def ocupacion_pct(self, restaurante_id: int, dia: date) -> int:
        """Porcentaje de las horas-mesa del día ya reservadas: (reservas activas × duración) / (mesas activas × horas abiertas)."""
        horario = self._horarios.obtener_por_dia(restaurante_id, dia.weekday())
        mesas_activas = [m for m in self._mesas.listar_por_restaurante(restaurante_id) if m.activa]
        if horario is None or not mesas_activas:
            return 0
        capacidad_min = len(mesas_activas) * (a_minutos(horario.hora_cierre) - a_minutos(horario.hora_apertura))
        reservadas = len(self._reservas.listar_activas_por_restaurante_y_fecha(restaurante_id, dia.isoformat()))
        return min(100, round(100 * reservadas * config.DURACION_RESERVA_MIN / capacidad_min))

    def panel(self, restaurante_id: int, hoy: date | None = None) -> dict:
        hoy = hoy or date.today()
        hoy_iso = hoy.isoformat()
        todas = self._reservas.listar_por_restaurante(restaurante_id)
        activas = [r for r in todas if r.estado != "CANCELADA"]
        desde = hoy - timedelta(days=13)
        por_dia = self._reservas.contar_por_dia(restaurante_id, desde.isoformat(), hoy_iso)
        serie = [{"fecha": (desde + timedelta(days=i)).isoformat(),
                  "n": por_dia.get((desde + timedelta(days=i)).isoformat(), 0)} for i in range(14)]
        return {
            "reservas_hoy": sum(1 for r in activas if r.fecha == hoy_iso),
            "proximas": sum(1 for r in activas if r.fecha >= hoy_iso),
            "pendientes": sum(1 for r in todas if r.estado == "PENDIENTE"),
            "ocupacion_pct": self.ocupacion_pct(restaurante_id, hoy),
            "ingresos_cop": self._items.ingresos_estimados(restaurante_id, hoy_iso),
            "serie_14d": serie,
            "top_productos": self._items.top_productos(restaurante_id, 5),
        }

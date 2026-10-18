"""Indicadores y series para el panel del administrador."""
from __future__ import annotations

from datetime import date, timedelta

from app import config
from app.datos.dao import HorarioDAO, MesaDAO, ReservaDAO, ReservaItemDAO
from app.negocio.patrones.creacionales.reserva_builder import a_minutos


FRANJAS_CALOR = ((11, 13), (13, 15), (15, 17), (17, 19), (19, 21), (21, 24))   # bandas de 2 h (la última llega al cierre)
ESTADOS_ORDEN = ("PENDIENTE", "CONFIRMADA", "CANCELADA")


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

    @staticmethod
    def por_estado(reservas) -> dict[str, int]:
        """Cantidad de reservas por estado (siempre con las tres claves)."""
        conteo = {e: 0 for e in ESTADOS_ORDEN}
        for r in reservas:
            conteo[r.estado] = conteo.get(r.estado, 0) + 1
        return conteo

    @staticmethod
    def mapa_calor(reservas) -> dict:
        """Reservas no canceladas por día de la semana (lunes=0) y banda horaria de 2 h, con la intensidad de cada celda."""
        celdas = [[0] * len(FRANJAS_CALOR) for _ in range(7)]
        for r in reservas:
            if r.estado == "CANCELADA":
                continue
            hora = a_minutos(r.hora) // 60
            for j, (ini, fin) in enumerate(FRANJAS_CALOR):
                if ini <= hora < fin:
                    celdas[date.fromisoformat(r.fecha).weekday()][j] += 1
                    break
        maximo = max((n for fila in celdas for n in fila), default=0)
        return {"celdas": celdas, "maximo": maximo,
                "franjas": [f"{ini:02d}–{fin:02d}" for ini, fin in FRANJAS_CALOR]}

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
            "por_estado": self.por_estado(todas),
            "mapa_calor": self.mapa_calor(todas),
        }

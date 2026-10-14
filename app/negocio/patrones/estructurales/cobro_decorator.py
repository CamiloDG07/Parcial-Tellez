"""Patrón Decorator: cálculo del "total a pagar" de un pre-pedido.

Todo el cálculo se hace en el servidor y en pesos colombianos ENTEROS (sin centavos).
Este módulo NO escribe nada en la base de datos: `reserva_item.precio_unitario_cop` y los ingresos
estimados siguen siendo el subtotal.

REGLA DE REDONDEO ÚNICA (`porcentaje_de`): cada decorador calcula su ajuste como
``(monto_del_componente_envuelto * tasa_pct + 50) // 100``, es decir, el porcentaje redondeado
al peso más cercano con los empates hacia arriba ("half up"), usando solo aritmética entera.
Se redondea el AJUSTE de cada decorador (no el total final), de modo que cada línea del desglose
es un entero exacto y la suma de las líneas siempre es igual al total.

¿IMPORTA EL ORDEN? Matemáticamente no: descuento, impuesto y propina son factores multiplicativos
(1 - d, 1 + t, 1 + p) y los factores conmutan. Con el redondeo por paso sí puede cambiar el resultado
en uno o dos pesos (la prueba `test_el_orden_solo_cambia_por_redondeo` lo demuestra). Por eso el orden
de producción queda fijado en `armar_cadena`: descuento → impuesto al consumo → propina sugerida.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Protocol

from app import config


class _Linea(Protocol):
    cantidad: int
    precio_unitario_cop: int


def porcentaje_de(monto_cop: int, tasa_pct: int) -> int:
    """Porcentaje entero de un monto entero, redondeado half-up al peso (regla única de redondeo)."""
    if monto_cop < 0 or tasa_pct < 0:
        raise ValueError("El monto y la tasa deben ser no negativos.")
    return (monto_cop * tasa_pct + 50) // 100


class Cobro(ABC):
    """PATRÓN ESTRUCTURAL · Decorator (rol: Component). Interfaz común de la base y de los decoradores."""

    etiqueta: str          # nombre corto de ESTE componente (para el desglose)

    @abstractmethod
    def monto_cop(self) -> int:
        """Monto acumulado en pesos enteros hasta este componente."""

    @abstractmethod
    def descripcion(self) -> str:
        """Descripción acumulada de la cadena, p. ej. 'Subtotal → Descuento (10 %) → Impuesto al consumo (8 %)'."""


class CobroBase(Cobro):
    """Decorator · rol: ConcreteComponent. Subtotal del pre-pedido: suma de `cantidad × precio_unitario_cop`
    (precios ya congelados en cada ítem)."""

    etiqueta = "Subtotal del pre-pedido"

    def __init__(self, items: Iterable[_Linea]) -> None:
        self._subtotal = sum(i.cantidad * i.precio_unitario_cop for i in items)
        if self._subtotal < 0:
            raise ValueError("El subtotal no puede ser negativo.")

    def monto_cop(self) -> int:
        return self._subtotal

    def descripcion(self) -> str:
        return self.etiqueta


class CobroDecorador(Cobro, ABC):
    """Decorator · rol: Decorator (clase base). Envuelve a otro `Cobro` y delega en él."""

    def __init__(self, envuelto: Cobro, tasa_pct: int) -> None:
        if not isinstance(tasa_pct, int) or not 0 <= tasa_pct <= 100:
            raise ValueError("La tasa debe ser un entero entre 0 y 100.")
        self._envuelto, self._tasa = envuelto, tasa_pct

    @property
    def tasa_pct(self) -> int:
        return self._tasa

    def _ajuste_cop(self) -> int:
        """Ajuste (siempre >= 0) = porcentaje del monto del componente envuelto, con la regla única de redondeo."""
        return porcentaje_de(self._envuelto.monto_cop(), self._tasa)

    def descripcion(self) -> str:
        return f"{self._envuelto.descripcion()} → {self.etiqueta}"


class ConDescuento(CobroDecorador):
    """Decorator · rol: ConcreteDecorator. Resta `tasa_pct` % del monto envuelto."""

    def __init__(self, envuelto: Cobro, tasa_pct: int | None = None) -> None:
        tasa_pct = config.DESCUENTO_PEDIDO_GRANDE_PCT if tasa_pct is None else tasa_pct     # se lee al construir (configurable)
        super().__init__(envuelto, tasa_pct)
        self.etiqueta = f"Descuento por pedido grande ({tasa_pct} %)"

    def monto_cop(self) -> int:
        return self._envuelto.monto_cop() - self._ajuste_cop()


class ConImpuestoConsumo(CobroDecorador):
    """Decorator · rol: ConcreteDecorator. Suma `tasa_pct` % de impuesto al consumo (tasa supuesta, configurable)."""

    def __init__(self, envuelto: Cobro, tasa_pct: int | None = None) -> None:
        tasa_pct = config.TASA_IMPUESTO_CONSUMO_PCT if tasa_pct is None else tasa_pct     # se lee al construir (configurable)
        super().__init__(envuelto, tasa_pct)
        self.etiqueta = f"Impuesto al consumo ({tasa_pct} %)"

    def monto_cop(self) -> int:
        return self._envuelto.monto_cop() + self._ajuste_cop()


class ConPropinaSugerida(CobroDecorador):
    """Decorator · rol: ConcreteDecorator. Suma `tasa_pct` % de propina sugerida (voluntaria; tasa supuesta)."""

    def __init__(self, envuelto: Cobro, tasa_pct: int | None = None) -> None:
        tasa_pct = config.TASA_PROPINA_SUGERIDA_PCT if tasa_pct is None else tasa_pct     # se lee al construir (configurable)
        super().__init__(envuelto, tasa_pct)
        self.etiqueta = f"Propina sugerida ({tasa_pct} %)"

    def monto_cop(self) -> int:
        return self._envuelto.monto_cop() + self._ajuste_cop()


def armar_cadena(items: Iterable[_Linea], con_propina: bool = False) -> list[Cobro]:
    """Cadena de producción, de la base al componente más externo (cada elemento envuelve al anterior).

    Orden fijo: Base → [Descuento si el subtotal llega al mínimo] → Impuesto al consumo → [Propina si se pide].
    """
    etapas: list[Cobro] = [CobroBase(list(items))]
    if etapas[0].monto_cop() >= config.DESCUENTO_PEDIDO_GRANDE_MINIMO_COP > 0:
        etapas.append(ConDescuento(etapas[-1]))
    etapas.append(ConImpuestoConsumo(etapas[-1]))
    if con_propina:
        etapas.append(ConPropinaSugerida(etapas[-1]))
    return etapas


def armar_cobro(items: Iterable[_Linea], con_propina: bool = False) -> Cobro:
    """El `Cobro` completo (la cadena de decoradores ya armada)."""
    return armar_cadena(items, con_propina)[-1]


def desglose(items: Iterable[_Linea], con_propina: bool = False) -> dict:
    """Líneas del desglose + totales, para las vistas. Cada línea es el aporte de un componente de la cadena
    (la suma de las líneas es exactamente `total_cop`). La propina no incluida se informa como sugerencia."""
    items = list(items)
    etapas = armar_cadena(items, con_propina)
    lineas, previo = [], 0
    for etapa in etapas:
        lineas.append({"etiqueta": etapa.etiqueta, "monto_cop": etapa.monto_cop() - previo})
        previo = etapa.monto_cop()
    con = armar_cadena(items, True)[-1].monto_cop()
    sin = armar_cadena(items, False)[-1].monto_cop()
    return {"lineas": lineas, "subtotal_cop": etapas[0].monto_cop(), "total_cop": etapas[-1].monto_cop(),
            "incluye_propina": con_propina, "propina_sugerida_cop": con - sin,
            "total_con_propina_cop": con, "descripcion": etapas[-1].descripcion()}

"""Límite de intentos fallidos de inicio de sesión (en memoria, de un solo proceso)."""
from __future__ import annotations

import threading
import time
from typing import Callable, Hashable


class LimitadorIntentos:
    """Bloquea una clave (p. ej. IP + correo) tras `max_fallos` fallos dentro de `ventana_s` segundos.

    El bloqueo dura `bloqueo_s`. Un inicio de sesión correcto borra los fallos de esa clave.
    Es una defensa sencilla contra la fuerza bruta: no se comparte entre procesos ni sobrevive a un reinicio.
    """

    def __init__(self, max_fallos: int = 5, ventana_s: int = 300, bloqueo_s: int = 300,
                 reloj: Callable[[], float] = time.monotonic) -> None:
        self._max, self._ventana, self._bloqueo, self._reloj = max_fallos, ventana_s, bloqueo_s, reloj
        self._fallos: dict[Hashable, list[float]] = {}
        self._bloqueados: dict[Hashable, float] = {}
        self._cerrojo = threading.Lock()

    def segundos_bloqueo(self, clave: Hashable) -> int:
        """Segundos que faltan para que la clave pueda intentar de nuevo (0 si no está bloqueada)."""
        with self._cerrojo:
            hasta = self._bloqueados.get(clave)
            if hasta is None:
                return 0
            restante = hasta - self._reloj()
            if restante <= 0:
                del self._bloqueados[clave]
                self._fallos.pop(clave, None)
                return 0
            return int(restante) + 1

    def registrar_fallo(self, clave: Hashable) -> None:
        with self._cerrojo:
            ahora = self._reloj()
            recientes = [t for t in self._fallos.get(clave, []) if ahora - t < self._ventana] + [ahora]
            self._fallos[clave] = recientes
            if len(recientes) >= self._max:
                self._bloqueados[clave] = ahora + self._bloqueo

    def limpiar(self, clave: Hashable) -> None:
        with self._cerrojo:
            self._fallos.pop(clave, None)
            self._bloqueados.pop(clave, None)

    def reiniciar(self) -> None:
        with self._cerrojo:
            self._fallos.clear()
            self._bloqueados.clear()

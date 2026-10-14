"""Modelos del dominio (dataclasses). Producto de las fábricas y los builders."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Usuario:
    """PATRÓN Factory Method · rol: Product (clase base abstracta del producto)."""
    id: int | None
    nombre: str
    email: str
    password_hash: str
    rol: str = ""

    def permisos(self) -> frozenset[str]:
        return frozenset()

    def ruta_inicio(self) -> str:
        return "/"


@dataclass
class Cliente(Usuario):
    """Factory Method · rol: ConcreteProduct."""
    rol: str = "cliente"

    def permisos(self) -> frozenset[str]:
        return frozenset({"reservar", "ver_restaurantes", "cancelar_propia", "ver_propias"})

    def ruta_inicio(self) -> str:
        return "/restaurantes"


@dataclass
class Administrador(Usuario):
    """Factory Method · rol: ConcreteProduct."""
    rol: str = "administrador"

    def permisos(self) -> frozenset[str]:
        return frozenset({"gestionar_mesas", "gestionar_horarios", "gestionar_reservas", "ver_restaurantes"})

    def ruta_inicio(self) -> str:
        return "/admin"


@dataclass
class Restaurante:
    id: int | None
    nombre: str
    direccion: str
    ciudad: str
    tipo_cocina: str
    descripcion: str
    admin_id: int


@dataclass
class Mesa:
    id: int | None
    restaurante_id: int
    numero: int
    capacidad: int
    ubicacion: str = ""
    activa: bool = True


@dataclass
class Horario:
    id: int | None
    restaurante_id: int
    dia_semana: int
    hora_apertura: str
    hora_cierre: str


@dataclass
class Reserva:
    id: int | None
    usuario_id: int
    restaurante_id: int
    mesa_id: int
    fecha: str            # ISO AAAA-MM-DD
    hora: str             # HH:MM
    num_personas: int
    estado: str = "PENDIENTE"
    notas: str = ""
    creado_en: str = ""

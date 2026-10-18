"""Modelos del dominio (dataclasses). Producto de las fábricas y los builders."""
from __future__ import annotations

from dataclasses import dataclass, field


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
    # Instantánea del cobro al crear la reserva (columnas de `reserva`; ver `cobro_decorator.instantanea`)
    subtotal_cop: int = 0
    descuento_pct: int = 0
    descuento_cop: int = 0
    impuesto_pct: int = 0
    impuesto_cop: int = 0
    total_pagar_cop: int = 0
    items: list["ReservaItem"] = field(default_factory=list)   # pre-pedido (no es columna de `reserva`)

    @property
    def total_cop(self) -> int:
        return sum(i.subtotal_cop for i in self.items)


@dataclass
class Categoria:
    id: int | None
    restaurante_id: int
    nombre: str
    orden: int = 0


@dataclass
class Producto:
    id: int | None
    restaurante_id: int
    categoria_id: int
    nombre: str
    descripcion: str
    precio_cop: int          # pesos colombianos enteros
    imagen: str = ""
    disponible: bool = True


@dataclass
class ReservaItem:
    id: int | None
    reserva_id: int | None
    producto_id: int
    cantidad: int
    precio_unitario_cop: int   # precio congelado al reservar

    @property
    def subtotal_cop(self) -> int:
        return self.cantidad * self.precio_unitario_cop

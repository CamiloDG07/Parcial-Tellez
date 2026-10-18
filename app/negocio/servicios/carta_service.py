"""Servicios de la carta (categorías y productos) y del pre-pedido (carrito en sesión)."""
from __future__ import annotations

import sqlite3
from typing import MutableMapping

from app.datos.dao import CategoriaDAO, ProductoDAO, ReservaItemDAO
from app.datos.modelos import Categoria, Producto, Reserva, Usuario
from app.negocio.excepciones import NoEncontradoError, ReglaNegocioError
from app.negocio.servicios.restaurante_service import RestauranteService

MAX_CANTIDAD = 20


class CartaService:
    def __init__(self, categorias: CategoriaDAO, productos: ProductoDAO, items: ReservaItemDAO,
                 restaurantes: RestauranteService) -> None:
        self._cat, self._prod, self._items, self._restaurantes = categorias, productos, items, restaurantes

    # ---------- lectura ----------
    def carta(self, restaurante_id: int, solo_disponibles: bool = True) -> list[dict]:
        """Categorías con sus productos (las categorías vacías se omiten en la vista pública)."""
        productos = self._prod.listar_por_restaurante(restaurante_id, solo_disponibles)
        resultado = []
        for categoria in self._cat.listar_por_restaurante(restaurante_id):
            propios = [p for p in productos if p.categoria_id == categoria.id]
            if propios or not solo_disponibles:
                resultado.append({"categoria": categoria, "productos": propios})
        return resultado

    def categorias(self, restaurante_id: int) -> list[Categoria]:
        return self._cat.listar_por_restaurante(restaurante_id)

    def obtener_producto(self, producto_id: int) -> Producto:
        p = self._prod.obtener_por_id(producto_id)
        if p is None:
            raise NoEncontradoError("El producto no existe.")
        return p

    def detalle_items(self, reserva_id: int) -> list[dict]:
        """Pre-pedido de una reserva con el nombre de cada producto."""
        filas = []
        for item in self._items.listar_por_reserva(reserva_id):
            producto = self._prod.obtener_por_id(item.producto_id)
            filas.append({"item": item, "nombre": producto.nombre if producto else "(producto eliminado)"})
        return filas

    def detalles_de(self, reserva_ids: list[int]) -> dict[int, list[dict]]:
        """Pre-pedido de VARIAS reservas con una sola consulta (misma forma que `detalle_items`)."""
        por_reserva = self._items.listar_con_nombre(list(reserva_ids))
        return {rid: [{"item": item, "nombre": nombre} for item, nombre in por_reserva.get(rid, [])]
                for rid in reserva_ids}

    # ---------- categorías (admin) ----------
    def crear_categoria(self, actor: Usuario, restaurante_id: int, nombre: str, orden: int) -> int:
        self._restaurantes.verificar_admin(actor, restaurante_id)
        nombre = (nombre or "").strip()
        if not 2 <= len(nombre) <= 40:
            raise ReglaNegocioError("El nombre de la categoría debe tener entre 2 y 40 caracteres.")
        if self._cat.obtener_por_nombre(restaurante_id, nombre):
            raise ReglaNegocioError("Ya existe una categoría con ese nombre.")
        return self._cat.insertar(Categoria(None, restaurante_id, nombre, orden))

    def actualizar_categoria(self, actor: Usuario, categoria_id: int, nombre: str, orden: int) -> None:
        c = self._categoria(categoria_id)
        self._restaurantes.verificar_admin(actor, c.restaurante_id)
        nombre = (nombre or "").strip()
        if not 2 <= len(nombre) <= 40:
            raise ReglaNegocioError("El nombre de la categoría debe tener entre 2 y 40 caracteres.")
        otra = self._cat.obtener_por_nombre(c.restaurante_id, nombre)
        if otra and otra.id != c.id:
            raise ReglaNegocioError("Ya existe una categoría con ese nombre.")
        c.nombre, c.orden = nombre, orden
        self._cat.actualizar(c)

    def eliminar_categoria(self, actor: Usuario, categoria_id: int) -> None:
        c = self._categoria(categoria_id)
        self._restaurantes.verificar_admin(actor, c.restaurante_id)
        if self._prod.contar_por_categoria(categoria_id):
            raise ReglaNegocioError("La categoría tiene productos; muévelos o elimínalos primero.")
        self._cat.eliminar(categoria_id)

    def _categoria(self, categoria_id: int) -> Categoria:
        c = self._cat.obtener_por_id(categoria_id)
        if c is None:
            raise NoEncontradoError("La categoría no existe.")
        return c

    # ---------- productos (admin) ----------
    def _validar_producto(self, restaurante_id: int, categoria_id: int, nombre: str, descripcion: str,
                          precio_cop: int) -> tuple[str, str]:
        nombre, descripcion = (nombre or "").strip(), (descripcion or "").strip()
        if not 2 <= len(nombre) <= 80:
            raise ReglaNegocioError("El nombre del producto debe tener entre 2 y 80 caracteres.")
        if len(descripcion) > 300:
            raise ReglaNegocioError("La descripción admite hasta 300 caracteres.")
        if not 0 <= precio_cop <= 10_000_000:
            raise ReglaNegocioError("El precio debe ser un entero entre 0 y 10.000.000 COP.")
        categoria = self._cat.obtener_por_id(categoria_id)
        if categoria is None or categoria.restaurante_id != restaurante_id:
            raise ReglaNegocioError("La categoría no pertenece a este restaurante.")
        return nombre, descripcion

    def crear_producto(self, actor: Usuario, restaurante_id: int, categoria_id: int, nombre: str,
                       descripcion: str, precio_cop: int, imagen: str, disponible: bool) -> int:
        self._restaurantes.verificar_admin(actor, restaurante_id)
        nombre, descripcion = self._validar_producto(restaurante_id, categoria_id, nombre, descripcion, precio_cop)
        return self._prod.insertar(Producto(None, restaurante_id, categoria_id, nombre, descripcion,
                                            precio_cop, imagen, disponible))

    def actualizar_producto(self, actor: Usuario, producto_id: int, categoria_id: int, nombre: str,
                            descripcion: str, precio_cop: int, imagen: str | None, disponible: bool) -> None:
        p = self.obtener_producto(producto_id)
        self._restaurantes.verificar_admin(actor, p.restaurante_id)
        p.nombre, p.descripcion = self._validar_producto(p.restaurante_id, categoria_id, nombre, descripcion, precio_cop)
        p.categoria_id, p.precio_cop, p.disponible = categoria_id, precio_cop, disponible
        if imagen:
            p.imagen = imagen
        self._prod.actualizar(p)

    def alternar_disponibilidad(self, actor: Usuario, producto_id: int) -> None:
        p = self.obtener_producto(producto_id)
        self._restaurantes.verificar_admin(actor, p.restaurante_id)
        p.disponible = not p.disponible
        self._prod.actualizar(p)

    def eliminar_producto(self, actor: Usuario, producto_id: int) -> None:
        p = self.obtener_producto(producto_id)
        self._restaurantes.verificar_admin(actor, p.restaurante_id)
        try:
            self._prod.eliminar(producto_id)
        except sqlite3.IntegrityError:
            raise ReglaNegocioError("El producto está en pre-pedidos de reservas; márcalo como no disponible.") from None


class CarritoService:
    """Pre-pedido guardado en la sesión del cliente: {"restaurante_id": n, "items": {"producto_id": cantidad}}.

    Solo guarda ids y cantidades; nombres y precios se leen siempre de la base de datos."""

    CLAVE = "carrito"

    def __init__(self, productos: ProductoDAO) -> None:
        self._prod = productos

    def _datos(self, sesion: MutableMapping) -> dict:
        return sesion.setdefault(self.CLAVE, {"restaurante_id": None, "items": {}})

    def agregar(self, sesion: MutableMapping, producto_id: int, cantidad: int) -> None:
        if not 1 <= cantidad <= MAX_CANTIDAD:
            raise ReglaNegocioError(f"La cantidad debe estar entre 1 y {MAX_CANTIDAD}.")
        producto = self._prod.obtener_por_id(producto_id)
        if producto is None:
            raise NoEncontradoError("El producto no existe.")
        if not producto.disponible:
            raise ReglaNegocioError(f"«{producto.nombre}» no está disponible.")
        datos = self._datos(sesion)
        if datos["items"] and datos["restaurante_id"] != producto.restaurante_id:
            raise ReglaNegocioError("Tu pre-pedido es de otro restaurante. Vacíalo para empezar uno nuevo.")
        datos["restaurante_id"] = producto.restaurante_id
        clave = str(producto_id)
        nueva = datos["items"].get(clave, 0) + cantidad
        if nueva > MAX_CANTIDAD:
            raise ReglaNegocioError(f"Máximo {MAX_CANTIDAD} unidades por plato.")
        datos["items"][clave] = nueva
        sesion[self.CLAVE] = datos     # reasigna para que la sesión firmada detecte el cambio

    def cambiar(self, sesion: MutableMapping, producto_id: int, cantidad: int) -> None:
        datos = self._datos(sesion)
        clave = str(producto_id)
        if clave not in datos["items"]:
            raise NoEncontradoError("Ese plato no está en tu pre-pedido.")
        if cantidad <= 0:
            del datos["items"][clave]
        elif cantidad > MAX_CANTIDAD:
            raise ReglaNegocioError(f"Máximo {MAX_CANTIDAD} unidades por plato.")
        else:
            datos["items"][clave] = cantidad
        if not datos["items"]:
            datos["restaurante_id"] = None
        sesion[self.CLAVE] = datos

    def vaciar(self, sesion: MutableMapping) -> None:
        sesion[self.CLAVE] = {"restaurante_id": None, "items": {}}

    def resumen(self, sesion: MutableMapping) -> dict:
        """Vista del carrito con datos frescos de la BD; descarta platos eliminados o no disponibles."""
        datos = self._datos(sesion)
        lineas, total, cantidad = [], 0, 0
        for clave, n in list(datos["items"].items()):
            p = self._prod.obtener_por_id(int(clave))
            if p is None or not p.disponible:
                del datos["items"][clave]
                continue
            subtotal = n * p.precio_cop
            lineas.append({"producto_id": p.id, "nombre": p.nombre, "precio_cop": p.precio_cop, "cantidad": n,
                           "subtotal_cop": subtotal, "imagen": p.imagen})
            total += subtotal
            cantidad += n
        if not datos["items"]:
            datos["restaurante_id"] = None
        sesion[self.CLAVE] = datos
        return {"restaurante_id": datos["restaurante_id"], "lineas": lineas, "total_cop": total, "cantidad": cantidad}

    def items_para_reserva(self, sesion: MutableMapping, restaurante_id: int) -> list[tuple[int, int]]:
        """Pares (producto_id, cantidad) para `ReservaBuilder.con_items`; exige que el carrito sea de ese restaurante."""
        resumen = self.resumen(sesion)
        if not resumen["lineas"]:
            return []
        if resumen["restaurante_id"] != restaurante_id:
            raise ReglaNegocioError("Tu pre-pedido es de otro restaurante. Vacíalo o cambia de restaurante.")
        return [(l["producto_id"], l["cantidad"]) for l in resumen["lineas"]]

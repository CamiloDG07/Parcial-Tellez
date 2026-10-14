# Guion del video (9–10 min)

Orden: **código por capas → DAO → diagrama de clases de control (patrones) → patrones creacionales → patrones estructurales → app en ejecución → cierre.**
Ten abiertos: el editor en la raíz del proyecto, `docs/diagramas/*.png`, y la app en `http://127.0.0.1:8000` (`python -m app.datos.seed --reset && uvicorn app.main:app`).

| Tiempo | Bloque |
|---|---|
| 0:00–0:40 | 1. Presentación |
| 0:40–2:10 | 2. Arquitectura de tres capas |
| 2:10–3:20 | 3. Capa de datos: DAO y diagrama de clases DAO |
| 3:20–4:00 | 4. Diagrama de clases de control (patrones) |
| 4:00–6:00 | 5. Patrones creacionales (Singleton, Factory Method, Builder) |
| 6:00–7:20 | 6. Patrones estructurales (Facade, Proxy) |
| 7:20–9:20 | 7. Demostración en ejecución |
| 9:20–10:00 | 8. Pruebas y cierre |

## 1. Presentación (0:40)
- Proyecto: reservas de restaurantes **MIDNIGHT DINER** (marca ficticia), FastAPI + Jinja2 + SQLite sin ORM, para Patrones de Diseño de Software.
- Roles: `cliente` y `administrador`. Pantalla: `docs/capturas/02_inicio_1440.png` o la app abierta en el inicio.
- Decir: la carta parte del menú de PIZZATRO (JuanPZ28), usada con su autorización.

## 2. Arquitectura de tres capas (1:30)
Mostrar `docs/diagramas/arquitectura_tres_capas.png` y luego el árbol de `app/`:
- **Presentación** (`app/presentacion/`): `controladores/` (`auth_controller.py`, `cliente_controller.py`, `admin_controller.py`, `api_controller.py`), `templates/` Jinja2 (la Vista) y `static/`.
- **Negocio** (`app/negocio/`): `servicios/`, `patrones/creacionales/`, `patrones/estructurales/`, `excepciones.py`.
- **Datos** (`app/datos/`): `modelos/` (dataclasses), `dao/`, `conexion.py`, `schema.sql`, `seed.py`.
- Regla de dependencias: presentación → negocio → datos. Un controlador del cliente solo habla con la fachada; un DAO no importa negocio (por eso `UsuarioDAO` recibe la fábrica por inyección).
- Mostrar `app/dependencias.py`: es la raíz de composición, donde se ve quién recibe a quién (`fachada` ← `reserva_service` (proxy) ← `reserva_service_real`).

## 3. Capa de datos y DAO (1:10)
Mostrar `docs/diagramas/diagrama_dao.png` y `app/datos/dao/__init__.py`:
- `BaseDAO[T]` (abstracta, genérica): `obtener_por_id`, `listar`, `insertar`, `actualizar`, `eliminar`; cada subclase define `tabla`, `columnas` y `_desde_fila`.
- DAO concretos: `UsuarioDAO.obtener_por_email`, `RestauranteDAO.buscar`, `MesaDAO.listar_por_restaurante`, `HorarioDAO.obtener_por_dia`, `ReservaDAO` (`listar_activas_por_mesa_y_fecha`, `insertar_con_items`, `cambiar_estado`), `CategoriaDAO`, `ProductoDAO`, `ReservaItemDAO` (`top_productos`, `ingresos_estimados`).
- SQL siempre parametrizado (`?`). Dinero en `precio_cop` entero.
- Mostrar de pasada `docs/diagramas/modelo_relacional.png` y `schema.sql` (PK, FK, UNIQUE, CHECK; `reserva_item` con `ON DELETE CASCADE`).

## 4. Diagrama de clases de control (0:40)
Mostrar `docs/diagramas/diagrama_control_patrones.png` y recorrerlo de izquierda a derecha:
- Izquierda: `UsuarioFactory` → `FabricaUsuario` → `FabricaCliente`/`FabricaAdministrador` → `Cliente`/`Administrador`.
- Centro/derecha: `ClienteController` → `ReservaFacade` → `IReservaService` ← `ReservaServiceProxy` → `ReservaService` → `ReservaBuilder`; `ConexionBD` como Singleton bajo los DAO.

## 5. Patrones creacionales (2:00)
**Singleton — `ConexionBD`** · `app/datos/conexion.py`
- Una sola instancia, segura con hilos: `__new__` con `_lock` y doble verificación; entrega conexiones con `PRAGMA foreign_keys = ON` y el gestor `sesion()` (commit/rollback). `reiniciar()` sirve para pruebas.
- Prueba: `tests/test_patrones.py::test_singleton_misma_instancia` y `test_singleton_seguro_con_hilos` (20 hilos, una instancia).

**Factory Method — `FabricaUsuario` / `UsuarioFactory`** · `app/negocio/patrones/creacionales/usuario_factory.py`
- `FabricaUsuario` (Creator) define `crear` y el método fábrica abstracto `_instanciar`; `FabricaCliente` y `FabricaAdministrador` (ConcreteCreator) producen `Cliente`/`Administrador` (en `app/datos/modelos/__init__.py`), con `permisos()` y `ruta_inicio()` distintos.
- Se usa en el flujo real: `UsuarioDAO._desde_fila` (inyectada en `dependencias.py`), `AuthService.registrar` y el login que redirige con `usuario.ruta_inicio()`.
- Prueba: `test_factory_crea_subclase_segun_rol`, `test_factory_rechaza_rol_desconocido`.

**Builder — `ReservaBuilder` (+ `ReservaDirector`)** · `app/negocio/patrones/creacionales/reserva_builder.py`
- Interfaz fluida: `.para_cliente().en_restaurante().el_dia().a_las().para_personas().en_mesa().con_notas().con_items().build()`.
- `build()` valida todas las reglas (futuro, horario del día, capacidad, mesa activa, sin solapamiento, productos del restaurante y disponibles) y lanza `ReglaNegocioError`. Los precios salen de la BD.
- `ReservaService.crear_reserva` **siempre** construye por el Builder. `ReservaDirector.reserva_rapida` es la receta predefinida.
- Prueba: `test_builder_falla_sin_mesa`, `test_el_servicio_construye_por_el_builder`, `tests/test_reglas_negocio.py`.

## 6. Patrones estructurales (1:20)
**Facade — `ReservaFacade`** · `app/negocio/patrones/estructurales/reserva_facade.py`
- Punto único del cliente: `buscar_disponibilidad`, `reservar`, `reservar_con_pre_pedido`, `cancelar`, `mis_reservas`, `carrito_*`. Orquesta `RestauranteService`, `MesaService`, `HorarioService`, `CartaService`, `CarritoService`.
- Mostrar `cliente_controller.py`: la ruta `POST /reservar` queda delgada.
- Prueba: `test_facade_usa_el_proxy_y_no_el_servicio_real`.

**Proxy de protección — `ReservaServiceProxy`** · `app/negocio/patrones/estructurales/reserva_proxy.py`
- Implementa `IReservaService` (`app/negocio/servicios/reserva_service.py`) igual que `ReservaService` (RealSubject); comprueba rol y propiedad (el cliente solo toca lo suyo; el admin solo su restaurante) y registra con `logging` cada operación (`PERMITIDO`/`DENEGADO`). La fachada recibe el proxy, nunca el servicio real.
- Prueba: `test_proxy_rechaza_cancelar_reserva_ajena`, `test_proxy_admin_solo_gestiona_su_restaurante`, `test_proxy_registra_operaciones`.

## 7. Demostración (2:00)
Credenciales: `cliente@demo.com / Cliente123!`, `admin@demo.com / Admin123!`.
1. **Cliente** (ventana 1): iniciar sesión → redirige a `/restaurantes` (Factory Method). Mostrar el filtro por cocina.
2. `/carta?restaurante_id=1`: pestaña POSTRE, buscar "tira", agregar ×2 (animación al carrito, insignia), abrir el cajón y ver el total.
3. `/reservar?restaurante_id=1`: recorrer los 5 pasos. En el paso 2 intentar avanzar sin hora (error). Elegir hora, mesa en el plano (libre = verde, ocupada = rojo), ver el pre-pedido y confirmar con una nota.
4. `/mis-reservas`: estado `PENDIENTE` y detalle del pre-pedido con total.
5. Repetir la misma mesa y hora → mensaje "La mesa ya está reservada" (Builder). Probar una hora de madrugada → rechazo por horario.
6. **Administrador** (ventana 2): `/admin` con KPIs, gráfico de 14 días y productos más pedidos. `/admin/reservas`: buscar "eva", confirmar. Volver al cliente: pasa a `CONFIRMADA`.
7. Mostrar `/admin/mesas` y `/admin/horarios` (CRUD) y `/admin/carta` (subir imagen; probar un archivo que no sea imagen).
8. Seguridad: como cliente abrir `/admin` → "ACCESO DENEGADO" (guarda de rol del controlador). En la terminal del servidor se ven las líneas `reservas.proxy PERMITIDO cliente#… crear_reserva`. El `DENEGADO` del proxy (cliente que cancela la reserva de otro) no se puede provocar desde la interfaz: mostrarlo con `pytest tests/test_patrones.py -k proxy -v`.

## 8. Pruebas y cierre (0:40)
- Ejecutar `pytest -q`: 78 pruebas (reglas de negocio, una por patrón, web por rol, Fase 2).
- Cierre: tres capas + DAO; creacionales **Singleton, Factory Method y Builder**; estructurales **Facade y Proxy**; la lógica de negocio solo se construye por el Builder y solo se alcanza a través del Proxy.
- Mencionar limitaciones con honestidad: el formulario de reserva necesita JavaScript; el cerrojo contra doble reserva es de un solo proceso; no se probó con varios workers.

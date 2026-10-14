# MIDNIGHT DINER — reservas de restaurantes

Aplicación web de reservas (parcial CR-2, Patrones de Diseño de Software, Universidad Sergio Arboleda).
FastAPI + Jinja2 + SQLite (`sqlite3`, sin ORM) en **tres capas** (presentación → negocio → datos) con DAO y patrones de diseño.
Marca ficticia (`BRAND_NAME` en `app/config.py`); todo el arte es CSS/SVG propio.

## Cómo correrlo (3 comandos)

```bash
python -m venv .venv && .venv/Scripts/activate        # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python -m app.datos.seed && uvicorn app.main:app --reload     # http://127.0.0.1:8000
```

Pruebas: `pytest -q`.  Variables: `SECRET_KEY` (firma de la sesión; el valor por defecto es solo para desarrollo) y `RESERVAS_DB` (ruta de la base).

## Usuarios de demostración

| Rol | Correo | Contraseña | Restaurante |
|---|---|---|---|
| cliente | `cliente@demo.com` | `Cliente123!` | — |
| administrador | `admin@demo.com` | `Admin123!` | Freddy's Slice Palace (id 1) |
| administrador | `admin2@demo.com` … `admin5@demo.com` | `Admin123!` | restaurantes 2 a 5 |

## Arquitectura

```
app/
├── presentacion/  controladores (auth, cliente, admin, api) · templates Jinja2 · static
├── negocio/       servicios · patrones/creacionales · patrones/estructurales · excepciones
├── datos/         modelos (dataclasses) · dao · conexion (Singleton) · schema.sql · seed
├── dependencias.py  raíz de composición (conecta DAO → servicios → proxy → fachada)
└── seguridad.py     hash de contraseñas (scrypt, librería estándar)
```

Los controladores del cliente solo hablan con `ReservaFacade`; la fachada recibe `ReservaServiceProxy`, nunca el servicio real. Un DAO no importa negocio: `UsuarioDAO` recibe la fábrica de usuarios por inyección.

## Patrones de diseño

| Patrón | Clase | Archivo |
|---|---|---|
| Singleton (creacional) | `ConexionBD` | `app/datos/conexion.py` |
| Factory Method (creacional) | `FabricaUsuario` / `UsuarioFactory` | `app/negocio/patrones/creacionales/usuario_factory.py` |
| Builder (creacional) | `ReservaBuilder` (+ `ReservaDirector`) | `app/negocio/patrones/creacionales/reserva_builder.py` |
| Facade (estructural) | `ReservaFacade` | `app/negocio/patrones/estructurales/reserva_facade.py` |
| Proxy de protección (estructural) | `ReservaServiceProxy` | `app/negocio/patrones/estructurales/reserva_proxy.py` |

Pruebas por patrón en `tests/test_patrones.py`. Diagramas Mermaid en `docs/`.

## Reglas de negocio

1. Fecha/hora futura y dentro del horario del restaurante; como la reserva dura 120 min, la última hora válida es `cierre − 120 min`.
2. Capacidad de la mesa ≥ personas y mesa activa.
3. Sin solapamientos en una mesa (las canceladas no cuentan).
4. El cliente solo ve y cancela lo suyo; el administrador solo gestiona su restaurante.
5. Estados: `PENDIENTE → CONFIRMADA | CANCELADA` (se permite además `CONFIRMADA → CANCELADA`).

## Créditos

Tipografías: Google Fonts (VT323, Press Start 2P, Bebas Neue, Inter; licencia OFL). Ilustraciones: SVG/CSS originales.
Sin material de Five Nights at Freddy's: la estética de "cámaras de seguridad" es una inspiración genérica.

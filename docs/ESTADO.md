# Estado del proyecto (pausa)

## Fase actual
- **Fase 1: completa** (tag `fase-1`). Tres capas, DAO, 5 patrones (Singleton, Factory Method, Builder, Facade, Proxy), login por rol, reservas con reglas de negocio, panel admin de mesas/horarios/reservas.
- **Fase 2: completa** (tag `fase-2`). Registro, carta (`carta_demo.json`, `precio_cop` entero), pre-pedido en sesión, reserva con pre-pedido, CRUD de carta con subida de imagen validada, KPIs, gráfico de 14 días, top de productos, tabla de reservas con filtros/búsqueda/paginación, fotos con créditos.
- **Fase 3: completa** (tag `fase-3`). Animaciones, asistente de reserva por pasos, modal propio, esqueletos, contadores y barras animadas; verificadas con `tools/e2e_capturas.py`.
- **Fase 4 (Decorator `PrecioDecorator`): no iniciada** (opcional).

## Falta (por prioridad)
1. `docs/guion_video.md` (no escrito) y PNG de los diagramas Mermaid (no intentado).
2. Plantilla externa de restaurante: **no se usó**; el CSS es propio (decisión no consultada con el usuario).
3. Opcional: Fase 4.
4. Opcional: conservar el filtro `q` al confirmar/cancelar desde `/admin/reservas` (hoy la redirección lo pierde).

## Cómo arrancar
```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
python -m app.datos.seed && uvicorn app.main:app --reload     # http://127.0.0.1:8000
pytest -q
```
E2E con navegador (necesita `python -m playwright install chromium`):
```bash
RESERVAS_DB=$PWD/demo_e2e.db python -m app.datos.seed --reset
RESERVAS_DB=$PWD/demo_e2e.db uvicorn app.main:app --port 8765
python tools/e2e_capturas.py http://localhost:8765 docs/capturas     # borra y regenera docs/capturas
```
Las fotos de platos se regeneran con `python tools/descargar_fotos.py` (requiere Pillow e internet).

## Credenciales demo
| Rol | Correo | Contraseña |
|---|---|---|
| cliente | `cliente@demo.com` | `Cliente123!` |
| administrador (restaurante 1) | `admin@demo.com` | `Admin123!` |
| administradores 2 a 5 | `admin2@demo.com` … `admin5@demo.com` | `Admin123!` |
| invitados con historial (seed) | `invitado1@demo.com` … `invitado3@demo.com` | `Invitado123!` |

## Archivos a medias
- Ninguno. El proyecto arranca y las pruebas pasan.

## Verificado ejecutándolo
- `pytest -q`: **78 pruebas pasan, 0 fallan** (reglas de negocio, patrones, web, Fase 2).
- `tools/e2e_capturas.py` (Playwright/Chromium, base recién sembrada) completo, sin errores: login, registro con error y éxito, carta (pestañas, búsqueda, agregar), cajón del pre-pedido, los 5 pasos del asistente (con error de validación de hora), reserva con pre-pedido ($56.000), doble reserva y reserva a las 03:00 rechazadas, cliente en `/admin` (403), vistas de admin, confirmación de reserva y modal de cancelación. 44 capturas en `docs/capturas/` (22 vistas a 1440 y 375 px).
- HTML sin etiquetas rotas ni atributos pegados y sin scroll horizontal a 375/1440 px en las páginas revisadas; consola sin errores propios (solo los 4xx provocados a propósito).
- `prefers-reduced-motion: reduce`: 0 platos ocultos, 0 animaciones infinitas activas, el punto REC sin animación.
- Destellos: 6 animaciones infinitas, la más rápida de 2000 ms (el límite exige >= 333 ms).
- Rendimiento: **56 fps de promedio, p95 de 33 ms** (Chromium headless, render por software, scroll + vuelo al carrito + cajón). Antes del ajuste (se quitó `mix-blend-mode` y se redujo la capa de ruido `.crt-ruido`) el mismo escenario daba 31 fps.
- Se revisaron a ojo las capturas del asistente (paso mesa a 1440 px, error de hora a 375 px) y del modal.
- Sin JavaScript: la carta y los 5 paneles se ven completos, pero no cargan las horas, así que **no se puede reservar sin JS**.
- Las 26 fotos pesan < 250 KB y tienen crédito (prueba automática); diagramas coherentes con el código (nombres de métodos y las 8 tablas).

## No verificado
- FPS en una GPU real o en un portátil medio: solo se midió en Chromium headless con render por software.
- La animación "vuela al carrito" se ejecuta, pero no se observó cuadro a cuadro.
- Que los diagramas Mermaid rendericen (no se pasaron por el renderizador).
- Capturas de pasos 4 y 5 del asistente y de la carta a 375 px: generadas, no revisadas a ojo una por una.
- Concurrencia: el cerrojo contra doble reserva solo protege un proceso; no se probó con varios workers.
- Sin limitación de intentos de login; cookie de sesión sin `Secure` (desarrollo en HTTP).
- La foto de "Semifreddo al limón" es de un semifreddo de avellana (aproximada). Las fotos vienen de Wikimedia Commons, no de Unsplash/Pexels/Pixabay.
- Rúbrica del profesor: no consultada.

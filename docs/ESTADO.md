# Estado del proyecto (entrega, 18-oct-2026)

## Fase actual
- **Fase 1: completa** (tag `fase-1`). Tres capas, DAO, 5 patrones (Singleton, Factory Method, Builder, Facade, Proxy), login por rol, reservas con reglas de negocio, panel admin de mesas/horarios/reservas.
- **Fase 2: completa** (tag `fase-2`). Registro, carta (`cartas_demo/<id>.json`, `precio_cop` entero), pre-pedido en sesión, reserva con pre-pedido, CRUD de carta con subida de imagen validada, KPIs, gráfico de 14 días, top de productos, tabla de reservas con filtros/búsqueda/paginación, fotos con créditos.
- **Fase 3: completa** (tag `fase-3`). Animaciones, asistente de reserva por pasos, modal propio, esqueletos, contadores y barras animadas; verificadas con `tools/e2e_capturas.py`.
- **Fase 4: Decorator `Cobro`** (rama `fase-4-decorator`, tag `fase-4`). `app/negocio/patrones/estructurales/cobro_decorator.py`; conectado al paso 5, `/api/cobro`, "Mis reservas" y la tabla del admin. Sin cambios en el esquema ni en los KPIs.

- **Fase 5 (UI y robustez, paquete CR-2) y Fase 6 (entrega)**: rama `fase-6-entrega` (desde `fase-5-fotos`). Aplicado el paquete de la otra instancia (46 archivos), cartas por restaurante en `cartas_demo/` (5 restaurantes, 62 platos, 62 fotos con crédito), fotos nuevas de Wikimedia Commons, README, guion, E2E y capturas regenerados. Detalle en `README.md` (sección Fase 5 y 6), `docs/CAMBIOS_FOTOS.md` y `docs/DESPLIEGUE.md`. **El paquete añadió columnas de instantánea del cobro a la tabla `reserva`** (cambio de esquema; ver README).

## Falta (por prioridad)
0. Despliegue en Render: `docs/DESPLIEGUE.md` (sección «Probado / no probado» dice si se llegó a probar en una URL pública).
1. Decidir si se usa una plantilla externa de restaurante: **no se usó**; el CSS es propio (nunca se consultó con el usuario).
2. Confirmar con el profesor las tasas (8 % impuesto, 10 % propina, 10 % de descuento desde $150.000): son supuestos configurables en `app/config.py`, no verificados contra la norma.
3. Opcional: conservar el filtro `q` al confirmar/cancelar desde `/admin/reservas` (hoy la redirección lo pierde).

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
- `pytest -q`: **154 pruebas pasan, 0 fallan** (reglas de negocio, patrones, web, Fases 2, 4 y 5, cartas por restaurante).
- `tools/e2e_capturas.py` (Playwright/Chromium, base recién sembrada) completo, sin errores: login, registro con error y éxito, carta (pestañas, búsqueda, agregar), cajón del pre-pedido, los 5 pasos del asistente (con error de validación de hora), reserva con pre-pedido ($56.000), doble reserva y reserva a las 03:00 rechazadas, cliente en `/admin` (403), vistas de admin, confirmación de reserva y modal de cancelación. 44 capturas en `docs/capturas/` (22 vistas a 1440 y 375 px).
- HTML sin etiquetas rotas ni atributos pegados y sin scroll horizontal a 375/1440 px en las páginas revisadas; consola sin errores propios (solo los 4xx provocados a propósito).
- `prefers-reduced-motion: reduce`: 0 platos ocultos, 0 animaciones infinitas activas, el punto REC sin animación.
- Destellos: 6 animaciones infinitas, la más rápida de 2000 ms (el límite exige >= 333 ms).
- Rendimiento: **56 a 60 fps de promedio (p95 de 17 a 33 ms según la corrida)** (Chromium headless, render por software, scroll + vuelo al carrito + cajón). Antes del ajuste (se quitó `mix-blend-mode` y se redujo la capa de ruido `.crt-ruido`) el mismo escenario daba 31 fps.
- Se revisaron a ojo las capturas del asistente (paso mesa a 1440 px, error de hora a 375 px) y del modal.
- Sin JavaScript: la carta y los 5 paneles se ven completos, pero no cargan las horas, así que **no se puede reservar sin JS**.
- Las 62 fotos (5 cartas) pesan < 250 KB, tienen versión `@400` y crédito (prueba automática); el README tiene una fila por foto con autor, licencia y enlace a Wikimedia Commons (comprobado con un script contra `CREDITOS.json`) y el crédito a PIZZATRO (JuanPZ28) por la carta.
- Diagramas coherentes con el código (nombres de métodos y las 8 tablas) y **exportados a PNG** con `mermaid-cli` + el Chromium de Playwright: `docs/diagramas/*.png` (4 archivos, vistos a ojo: DAO y control/patrones). El de patrones se pasó a orientación vertical por legibilidad.
- Capturas de los pasos 4 y 5 del asistente revisadas a 1440 y 375 px; en el paso 5 la caja de notas tocaba el botón de confirmar: corregido con CSS y recapturado. El E2E ahora también captura el paso 5 (`12b_…`).
- E2E repetido con el cambio: sin errores de HTML ni de consola, 60 fps de promedio y p95 de 16,8 ms (mismas condiciones: Chromium headless, render por software).
- `docs/guion_video.md` escrito (8 a 10 min); sus nombres de archivos, clases y pruebas se tomaron del código y de `tests/test_patrones.py`.

- Fase 4: `tests/test_fase4.py` (32 pruebas): cada decorador por separado, composición con montos exactos, redondeo half-up, orden (6 permutaciones: solo difiere 1–2 pesos por redondeo; con montos redondos es idéntico), propina opcional, pre-pedido vacío, tasas configurables, el total de la pantalla de confirmación y de `/api/cobro` coincide con la cadena, el cliente no puede enviar montos, el esquema y `ingresos_cop` no cambian.
- E2E con el Decorator: 8 cannoli + 1 bruschetta (restaurante 1) = $170.000 → a pagar $165.240 → con propina $181.764 (el total se recalcula al marcar la casilla); mensaje de confirmación y detalle en "Mis reservas" con desglose; capturas `12b`, `12c`, `13`; HTML y consola sin errores; 60 fps de promedio en el mismo escenario.
- Diagrama `diagrama_control_patrones.mmd` con el Decorator, nombres de clases y métodos comprobados contra el código y PNG re-exportado.

## No verificado
- **Las tasas del Decorator no están verificadas contra la normativa vigente** (son supuestos configurables).
- FPS en una GPU real o en un portátil medio: solo se midió en Chromium headless con render por software.
- La animación "vuela al carrito" se ejecuta, pero no se observó cuadro a cuadro.
- Capturas de otras pantallas (carta a 375 px, vistas de admin, registro): generadas, no revisadas a ojo una por una.
- El guion del video no se ha ensayado ni cronometrado; los tiempos son estimados.
- Concurrencia: el cerrojo contra doble reserva solo protege un proceso; no se probó con varios workers.
- Sin limitación de intentos de login; cookie de sesión sin `Secure` (desarrollo en HTTP).
- La foto de "Semifreddo al limón" es de un semifreddo de avellana (aproximada). Las fotos vienen de Wikimedia Commons, no de Unsplash/Pexels/Pixabay.
- Rúbrica del profesor: no consultada.

## Entrega (fase 6)
- Instalación limpia (venv nuevo con `requirements.txt` y otro con `requirements-prod.txt`), `seed --reset`, arranque con uvicorn y reserva completa por HTTP; E2E de Playwright sin fallos (50 capturas en `docs/capturas`).
- `limonada-de-coco` y `churrasco-de-res` son las fotos menos fieles al nombre del plato (ver `docs/CAMBIOS_FOTOS.md`).

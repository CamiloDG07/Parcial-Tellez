# Estado del proyecto (pausa)

## Fase actual
- **Fase 1: completa** (tag `fase-1`). Tres capas, DAO, 5 patrones (Singleton, Factory Method, Builder, Facade, Proxy), login por rol, reservas con reglas de negocio, panel admin de mesas/horarios/reservas.
- **Fase 2: completa** (tag `fase-2`). Registro, carta (`carta_demo.json`, precios `precio_cop` enteros), pre-pedido en sesión, reserva con pre-pedido (`ReservaBuilder.con_items`), CRUD de categorías/productos con subida de imagen validada, KPIs, gráfico de 14 días, top de productos, tabla de reservas con filtros/búsqueda/paginación, fotos de platos con créditos.
- **Fase 3: parcial, SIN tag.** Escrito pero con verificación incompleta: animaciones (`static/js/efectos.js` + sección "Fase 3" de `tema.css`), asistente de reserva por pasos (`reservar.js`, `reservar.html`), modal de confirmación propio, esqueletos de carga, contadores y barras animadas.
- **Fase 4 (Decorator `PrecioDecorator`): no iniciada.**

## Falta (por prioridad)
1. Terminar de verificar la Fase 3 en navegador: relanzar `tools/e2e_capturas.py` (ver abajo). La corrida anterior llegó a generar las 22 capturas y falló solo en el último bloque (FPS/destellos) por un error del script, ya corregido pero **no reejecutado**.
2. Revisar a ojo las capturas nuevas del asistente por pasos (`docs/capturas/09_…` a `12_…`) y el modal (`22_…`); no se han mirado.
3. Probar el asistente con JavaScript deshabilitado y con `prefers-reduced-motion` (el script lo comprueba, pero no se ejecutó con éxito).
4. Medir FPS (el script lo hace; el resultado aún no existe) y, si pasa, cerrar con commit y tag `fase-3`.
5. `docs/guion_video.md` (no escrito) y PNG de los diagramas Mermaid (no intentado).
6. Plantilla externa de restaurante: **no se usó**; el CSS es propio (decisión no consultada).
7. Opcional: Fase 4.

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
- `tools/e2e_capturas.py`: último bloque (destellos y FPS) corregido pero sin reejecutar.
- Ningún archivo de la aplicación está a medias; el proyecto arranca y las pruebas pasan.

## Verificado ejecutándolo
- `pytest -q`: **78 pruebas pasan, 0 fallan** (reglas de negocio, patrones, web, Fase 2), corrida al pausar.
- Recorrido Playwright de la Fase 1 (cliente y admin: login, reserva con mesa, doble reserva rechazada, cliente fuera de `/admin`, confirmación): pasó; sin etiquetas HTML rotas ni scroll horizontal a 375 y 1440 px; consola sin errores propios.
- Recorrido Playwright de la Fase 2 (registro con error y éxito, carta con pestañas y búsqueda, pre-pedido, reserva con pre-pedido, total en "Mis reservas", panel con ingresos y 14 barras): pasó; consola solo con el 400 provocado en el registro.
- Tras añadir la Fase 3, la corrida de `tools/e2e_capturas.py` completó login, registro, carta, cajón del pre-pedido, los 5 pasos del asistente, doble reserva y reserva a las 03:00 rechazadas, vistas de admin, confirmación y modal, y generó 44 capturas (22 vistas × 2 anchos).
- Las 26 fotos pesan < 250 KB y tienen crédito (prueba `test_cada_plato_tiene_foto_y_credito`); revisadas a ojo en hoja de contacto.
- Diagramas: los nombres de métodos de `diagrama_dao.mmd` y `diagrama_control_patrones.mmd` existen en el código; las 8 tablas de `schema.sql` están en `modelo_relacional.mmd`.

## No verificado
- Resultado del último bloque del E2E: destellos por segundo, FPS, `prefers-reduced-motion` y comportamiento sin JavaScript.
- Que las capturas del asistente por pasos, el modal y la animación "vuela al carrito" se vean bien (no las he mirado; la animación solo se ejecutó, no se observó).
- Que los diagramas Mermaid rendericen (no se pasaron por el renderizador).
- Concurrencia: el cerrojo contra doble reserva solo protege un proceso; no se probó con varios workers.
- Sin limitación de intentos de login; cookie de sesión sin `Secure` (desarrollo en HTTP).
- La foto de "Semifreddo al limón" es de un semifreddo de avellana (aproximada).
- Las fotos vienen de Wikimedia Commons, no de Unsplash/Pexels/Pixabay.
- Rúbrica del profesor: no consultada.

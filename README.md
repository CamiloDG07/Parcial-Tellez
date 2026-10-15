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

Pruebas: `pytest -q`.  E2E con navegador y capturas: `python tools/e2e_capturas.py http://localhost:8765 docs/capturas` (ver `docs/ESTADO.md`).

Documentación: diagramas Mermaid en `docs/*.mmd` y PNG en `docs/diagramas/` (se regeneran con `tools/mmdc`: `npm install --prefix tools/mmdc @mermaid-js/mermaid-cli`, ver `tools/exportar_diagramas.sh`); capturas en `docs/capturas/`; guion del video en `docs/guion_video.md`.  Variables: `SECRET_KEY` (firma de la sesión; el valor por defecto es solo para desarrollo) y `RESERVAS_DB` (ruta de la base).

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

### Fase 2 (carta, pre-pedido, registro y panel)

- **Registro** público en `/registro` (el rol siempre es `cliente`; los administradores solo existen por seed).
- **Carta** por restaurante en `/carta` (pestañas por categoría y búsqueda). Dinero en **pesos colombianos enteros** (`precio_cop`, sin centavos).
- **Pre-pedido**: carrito guardado en la sesión (cajón lateral), se confirma junto con la reserva vía `ReservaBuilder.con_items(...)`. El precio sale siempre de la base de datos y queda congelado en `reserva_item.precio_unitario_cop`. Cancelar la reserva elimina sus ítems (y borrar una reserva los elimina en cascada).
- **Administrador**: CRUD de categorías y productos con subida de imagen (solo JPG/PNG/WebP detectados por su cabecera, máx. 2 MB, nombre aleatorio), activar/agotar productos, panel con KPIs, gráfico de 14 días y top de productos (SVG/CSS propios) y tabla de reservas con filtros, búsqueda y paginación.
- **Ocupación %** = (reservas activas de hoy × 120 min) / (mesas activas × minutos abiertos hoy). **Ingresos estimados** = suma de pre-pedidos de reservas no canceladas desde hoy.

### Fase 3 (animaciones y pulido)

Todo en CSS y JavaScript vanilla (`static/js/efectos.js`, sección "Fase 3" de `static/css/tema.css`), sin librerías:
aparición al hacer scroll (`IntersectionObserver`), entrada de página, asistente de reserva por pasos con transición
(fecha → hora → mesa → pre-pedido → confirmar), animación "vuela al carrito" (Web Animations API) con insignia que rebota,
pulso suave en las mesas libres, esqueletos de carga, toasts, modal de confirmación propio (`<dialog>`), cajón del pre-pedido,
contadores animados y barras que crecen en el panel. Con `prefers-reduced-motion: reduce` no se anima nada. La animación
infinita más rápida dura 2 s (límite de seguridad: 3 destellos/s). El formulario de reserva necesita JavaScript para
cargar las horas disponibles.

### Fase 4 (Decorator: total a pagar)

`ReservaFacade` arma una cadena de decoradores sobre el subtotal del pre-pedido para mostrar el **total a pagar** en el paso 5
del asistente, en "Mis reservas" y en el panel del administrador. Orden fijo: descuento → impuesto al consumo → propina sugerida
(opcional, casilla en el formulario). Todo en pesos enteros, con una única regla de redondeo (`porcentaje_de`: porcentaje al peso
más cercano, empates hacia arriba, aritmética entera). El cálculo es solo del servidor y **no se guarda nada nuevo**:
`reserva_item.precio_unitario_cop` y los ingresos estimados siguen siendo el subtotal.

Tasas (supuestos de demostración, configurables en `app/config.py`; **no se han verificado contra la normativa vigente**):
`TASA_IMPUESTO_CONSUMO_PCT = 8`, `TASA_PROPINA_SUGERIDA_PCT = 10`, `DESCUENTO_PEDIDO_GRANDE_PCT = 10` desde
`DESCUENTO_PEDIDO_GRANDE_MINIMO_COP = 150000`. Ejemplo: subtotal $170.000 → descuento −$17.000 → impuesto +$12.240 → **$165.240**;
con propina +$16.524 → **$181.764**.

Los controladores del cliente solo hablan con `ReservaFacade`; la fachada recibe `ReservaServiceProxy`, nunca el servicio real. Un DAO no importa negocio: `UsuarioDAO` recibe la fábrica de usuarios por inyección.

## Patrones de diseño

| Patrón | Clase | Archivo |
|---|---|---|
| Singleton (creacional) | `ConexionBD` | `app/datos/conexion.py` |
| Factory Method (creacional) | `FabricaUsuario` / `UsuarioFactory` | `app/negocio/patrones/creacionales/usuario_factory.py` |
| Builder (creacional) | `ReservaBuilder` (+ `ReservaDirector`) | `app/negocio/patrones/creacionales/reserva_builder.py` |
| Facade (estructural) | `ReservaFacade` | `app/negocio/patrones/estructurales/reserva_facade.py` |
| Proxy de protección (estructural) | `ReservaServiceProxy` | `app/negocio/patrones/estructurales/reserva_proxy.py` |
| Decorator (estructural) | `Cobro`, `CobroBase`, `CobroDecorador`, `ConDescuento`, `ConImpuestoConsumo`, `ConPropinaSugerida` | `app/negocio/patrones/estructurales/cobro_decorator.py` |

Pruebas por patrón en `tests/test_patrones.py` (Decorator: `tests/test_fase4.py`). Diagramas Mermaid en `docs/`.

## Reglas de negocio

1. Fecha/hora futura y dentro del horario del restaurante; como la reserva dura 120 min, la última hora válida es `cierre − 120 min`.
2. Capacidad de la mesa ≥ personas y mesa activa.
3. Sin solapamientos en una mesa (las canceladas no cuentan).
4. El cliente solo ve y cancela lo suyo; el administrador solo gestiona su restaurante.
5. Estados: `PENDIENTE → CONFIRMADA | CANCELADA` (se permite además `CONFIRMADA → CANCELADA`).

## Atribución de la carta

La carta (`carta_demo.json`: 26 platos, 3 categorías, precios en COP) parte del menú del repositorio **PIZZATRO** de **JuanPZ28**, usado con su autorización; solo se tomaron nombres, descripciones y precios (sin imágenes ni diseño). El seed la carga en los dos restaurantes de cocina italiana (ids 1 y 5).

## Créditos

- Tipografías: Google Fonts (VT323, Press Start 2P, Bebas Neue, Inter; licencia OFL). Ilustraciones: SVG/CSS originales.
- Sin material de Five Nights at Freddy's: la estética de "cámaras de seguridad" es una inspiración genérica.
- Fotos de los platos: descargadas de **Wikimedia Commons** con `tools/descargar_fotos.py` (licencias CC0 / dominio público / CC BY / CC BY-SA, verificadas por la API). Recortadas a 16:10 y comprimidas (< 250 KB). Al reutilizarlas se debe mantener esta atribución; las CC BY-SA obligan a compartir las adaptaciones con la misma licencia.

| Plato (archivo) | Foto en Wikimedia Commons | Autor | Licencia |
|---|---|---|---|
| `bruschetta-clasica.jpg` | [A typical Maltese bruschetta with fresh Mediterranean ingredients.jpg](https://commons.wikimedia.org/wiki/File:A_typical_Maltese_bruschetta_with_fresh_Mediterranean_ingredients.jpg) | Patrickfarrugia | CC BY-SA 4.0 |
| `ensalada-caprese.jpg` | [Insalata caprese in Israel.jpg](https://commons.wikimedia.org/wiki/File:Insalata_caprese_in_Israel.jpg) | בר | CC BY-SA 3.0 |
| `carpaccio-di-manzo.jpg` | [Carpaccio Cipriani.jpg](https://commons.wikimedia.org/wiki/File:Carpaccio_Cipriani.jpg) | Nurban | CC0 |
| `calamares-fritti.jpg` | [Fried Calamari Rings.jpg](https://commons.wikimedia.org/wiki/File:Fried_Calamari_Rings.jpg) | Maksym Kozlenko | CC BY-SA 4.0 |
| `arancini-di-risotto.jpg` | [Arancini 002.jpg](https://commons.wikimedia.org/wiki/File:Arancini_002.jpg) | No machine-readable author provided. Gmelfi assumed (based on copyrigh | Public domain |
| `focaccia-al-rosmarino.jpg` | [Rosemary Focaccia.jpg](https://commons.wikimedia.org/wiki/File:Rosemary_Focaccia.jpg) | Parkerman &amp; Christie from San Diego, USA | CC BY 2.0 |
| `zuppa-minestrone.jpg` | [Minestrone soup.jpg](https://commons.wikimedia.org/wiki/File:Minestrone_soup.jpg) | Katrin Morenz from Aachen, Deutschland | CC BY-SA 2.0 |
| `burrata-con-tomates-cherry.jpg` | [Burrata2.jpg](https://commons.wikimedia.org/wiki/File:Burrata2.jpg) | Popo le Chien | CC0 |
| `antipasto-misto.jpg` | [Antipasto Platter.jpg](https://commons.wikimedia.org/wiki/File:Antipasto_Platter.jpg) | Alpha from Melbourne, Australia | CC BY-SA 2.0 |
| `pizza-margherita.jpg` | [Margherita Originale.JPG](https://commons.wikimedia.org/wiki/File:Margherita_Originale.JPG) | Mario56 | CC BY-SA 3.0 |
| `pizza-pepperoni.jpg` | [Pepperoni Pizza from Fellini’s Pizza.jpg](https://commons.wikimedia.org/wiki/File:Pepperoni_Pizza_from_Fellini%E2%80%99s_Pizza.jpg) | BullDawg2021 | CC BY 4.0 |
| `pizza-quattro-formaggi.jpg` | [Four cheese pizza.jpg](https://commons.wikimedia.org/wiki/File:Four_cheese_pizza.jpg) | Shreya13jain | CC BY-SA 4.0 |
| `spaghetti-alla-carbonara.jpg` | [Espaguetis carbonara.jpg](https://commons.wikimedia.org/wiki/File:Espaguetis_carbonara.jpg) | Javier Somoza | CC BY-SA 4.0 |
| `fettuccine-alfredo.jpg` | [Chicken fettuccine alfredo.JPG](https://commons.wikimedia.org/wiki/File:Chicken_fettuccine_alfredo.JPG) | Dllu | CC BY-SA 4.0 |
| `lasagna-alla-bolognese.jpg` | [Meaty Lasagna 8of8 (8736299782).jpg](https://commons.wikimedia.org/wiki/File:Meaty_Lasagna_8of8_(8736299782).jpg) | Breville USA | CC BY 2.0 |
| `gnocchi-al-pesto.jpg` | [Gnocchi al pesto 02.jpg](https://commons.wikimedia.org/wiki/File:Gnocchi_al_pesto_02.jpg) | Postcrosser | CC BY-SA 4.0 |
| `risotto-ai-funghi.jpg` | [Mushroom Risotto (4789415965).jpg](https://commons.wikimedia.org/wiki/File:Mushroom_Risotto_(4789415965).jpg) | Katrin Gilger | CC BY-SA 2.0 |
| `pollo-alla-parmigiana.jpg` | [Chicken parmigiana.jpg](https://commons.wikimedia.org/wiki/File:Chicken_parmigiana.jpg) | Tristan Kenney | CC BY 2.0 |
| `tiramisu.jpg` | [Dolce Tiramisù monoporzione.jpg](https://commons.wikimedia.org/wiki/File:Dolce_Tiramis%C3%B9_monoporzione.jpg) | Anna.Massini | CC BY 4.0 |
| `panna-cotta.jpg` | [Panna Cotta with cream and garnish.jpg](https://commons.wikimedia.org/wiki/File:Panna_Cotta_with_cream_and_garnish.jpg) | hiro | CC BY-SA 2.0 |
| `cannoli-siciliani.jpg` | [Cannoli in a box.jpg](https://commons.wikimedia.org/wiki/File:Cannoli_in_a_box.jpg) | Quinn Dombrowski from Berkeley, USA | CC BY-SA 2.0 |
| `affogato-al-caffe.jpg` | [Affogato.JPG](https://commons.wikimedia.org/wiki/File:Affogato.JPG) | VR38DETT | Public domain |
| `torta-caprese.jpg` | [Torta caprese with confectioner's sugar and chocolate sauce (7830104492).jpg](https://commons.wikimedia.org/wiki/File:Torta_caprese_with_confectioner%27s_sugar_and_chocolate_sauce_(7830104492).jpg) | Fabrizio Pucci | CC BY 2.0 |
| `semifreddo-al-limone.jpg` | [Semifreddo nocciola.jpg](https://commons.wikimedia.org/wiki/File:Semifreddo_nocciola.jpg) | Daniele2399 | CC BY-SA 4.0 |
| `zeppole.jpg` | [Zeppole stacked on a plate.jpg](https://commons.wikimedia.org/wiki/File:Zeppole_stacked_on_a_plate.jpg) | Luca Sartoni | CC BY-SA 2.0 |
| `torta-della-nonna.jpg` | [Torta della nonna.jpg](https://commons.wikimedia.org/wiki/File:Torta_della_nonna.jpg) | fugzu from Pistoia, Italia | CC BY 2.0 |
#   P a r c i a l - T e l l e z  
 
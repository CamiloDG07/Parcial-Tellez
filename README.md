# MIDNIGHT DINER — reservas de restaurantes

Aplicación web de reservas (parcial CR-2, Patrones de Diseño de Software, Universidad Sergio Arboleda).
FastAPI + Jinja2 + SQLite (`sqlite3`, sin ORM) en **tres capas** (presentación → negocio → datos) con DAO y patrones de diseño.
Marca ficticia (`BRAND_NAME` en `app/config.py`), sin material de terceros salvo las fotos de platos, con sus créditos (ver «Créditos»); el arte de la interfaz es CSS/SVG propio.

## Cómo correrlo (3 comandos)

```bash
python -m venv .venv && .venv/Scripts/activate        # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python -m app.datos.seed && uvicorn app.main:app --reload     # http://127.0.0.1:8000
```

Pruebas: `pytest -q` (154 pruebas pasan).  E2E con navegador y capturas: `python tools/e2e_capturas.py http://localhost:8765 docs/capturas` (ver `docs/ESTADO.md`).

Documentación: diagramas Mermaid en `docs/*.mmd` y PNG en `docs/diagramas/` (se regeneran con `tools/mmdc`: `npm install --prefix tools/mmdc @mermaid-js/mermaid-cli`, ver `tools/exportar_diagramas.sh`); capturas en `docs/capturas/`; guion del video en `docs/guion_video.md`.  Variables: `SECRET_KEY` (firma de la sesión; el valor por defecto es solo para desarrollo), `RESERVAS_DB` (ruta de la base), `HTTPS_ONLY=1` (cookie `Secure` y cabecera HSTS) y `AUTOSEMBRAR=1` (siembra los datos demo al arrancar si la base está vacía). **Despliegue en Render (y por qué no en Vercel): `docs/DESPLIEGUE.md`.**

## Usuarios de demostración

| Rol | Correo | Contraseña | Restaurante |
|---|---|---|---|
| cliente | `cliente@demo.com` | `Cliente123!` | — |
| administrador | `admin@demo.com` | `Admin123!` | Slice Palace Medianoche (id 1) |
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
- **Carta** por restaurante en `/carta` (pestañas por categoría y búsqueda); cada restaurante tiene su propia carta en `cartas_demo/<id>.json` (ver más abajo). Dinero en **pesos colombianos enteros** (`precio_cop`, sin centavos).
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

### Fase 5 y 6 (pulido, robustez y entrega)

- **Interfaz**: plano de mesas por zonas (círculo, cuadrado y rectángulo según la capacidad, operable con teclado), «Mis reservas» en tarjetas con filtros Próximas/Pasadas/Canceladas, comprobante imprimible (`/mis-reservas/{id}/comprobante`) y descarga `.ics` para el calendario, portadas SVG por tipo de cocina en la lista de restaurantes, páginas 404/error con el tema, y en el panel de administración dona de reservas por estado, mapa de calor de ocupación por día y franja, y exportación CSV.
- **Robustez**: reserva con comprobación de solape e inserción en una sola transacción `BEGIN IMMEDIATE` (a prueba de varios procesos), límite de 5 intentos fallidos de login por IP y correo (bloqueo de 5 min, en memoria), SQLite en modo WAL con `busy_timeout`, cabeceras de seguridad y CSP, `Cache-Control` para `/static`, y carga de datos por lote en `ReservaFacade.enriquecer`.
- **Cambio de esquema (Fase 5)**: la tabla `reserva` guarda una instantánea del cobro al crear la reserva (`subtotal_cop`, `descuento_pct`, `descuento_cop`, `impuesto_pct`, `impuesto_cop`, `total_pagar_cop`) para que un cambio posterior de las tasas no altere lo que se le cobró a cada cliente; las bases antiguas se migran al arrancar. La propina sigue siendo voluntaria y no se guarda.
- **Cartas por restaurante** (`cartas_demo/<id>.json`, ver `cartas_demo/LEEME.md`): 1 Slice Palace Medianoche (pizzería, 12 platos), 2 La Cocina del Turno Noche (colombiana, 11), 3 Pasillo Este Sushi (japonesa, 13), 4 Cámara 04 Parrilla (parrilla, 12), 5 Backstage Pasta & Vino (italiana, 14): 62 platos y 62 fotos, ninguna repetida entre restaurantes. `tests/test_cartas_demo.py` exige que cada restaurante tenga carta con al menos 10 platos y 3 categorías, y que cada foto exista, pese menos de 250 KB, tenga su versión `@400` y su crédito. Los cambios de fotos y los platos quitados están en `docs/CAMBIOS_FOTOS.md`.

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

## Atribución de las cartas

Las cartas de los restaurantes 1 y 5 parten del menú del repositorio **PIZZATRO** de **JuanPZ28**, usado con su autorización; solo se tomaron nombres, descripciones y precios (sin imágenes ni diseño), repartidos entre la pizzería y la trattoria. Las cartas 2, 3 y 4 (colombiana, japonesa y parrilla) son texto propio del proyecto con precios de demostración. El seed carga `cartas_demo/<id>.json` en el restaurante con ese id.

## Créditos

- Tipografías: Google Fonts (VT323, Press Start 2P, Bebas Neue, Inter; licencia OFL). Ilustraciones: SVG/CSS originales.
- Marca ficticia, sin material de terceros salvo las fotos de platos, con sus créditos.
- Fotos de los platos: descargadas de **Wikimedia Commons** con `tools/descargar_fotos.py` (licencias CC0 / dominio público / CC BY / CC BY-SA, verificadas por la API). Recortadas a 16:10 centrando el plato, con auto-contraste y nitidez suaves, a 800×500 (< 250 KB) más una versión `@400` para `srcset`. Al reutilizarlas se debe mantener esta atribución; las CC BY-SA obligan a compartir las adaptaciones con la misma licencia.

| Plato (archivo) | Foto en Wikimedia Commons | Autor | Licencia |
|---|---|---|---|
| `bruschetta-clasica.jpg` | [Bruschetta at The Bar at MacArthur Place - Sarah Stierch.jpg](https://commons.wikimedia.org/wiki/File:Bruschetta_at_The_Bar_at_MacArthur_Place_-_Sarah_Stierch.jpg) | Missvain | CC BY 4.0 |
| `ensalada-caprese.jpg` | [Caprese salad in homemade.jpg](https://commons.wikimedia.org/wiki/File:Caprese_salad_in_homemade.jpg) | spiralmushroom | CC BY 2.0 |
| `carpaccio-di-manzo.jpg` | [Beef Carpaccio (3466985953).jpg](https://commons.wikimedia.org/wiki/File:Beef_Carpaccio_(3466985953).jpg) | Mack Male from Edmonton, AB, Canada | CC BY-SA 2.0 |
| `calamares-fritti.jpg` | [Calamari fritti in Izola Isola (52976884396).jpg](https://commons.wikimedia.org/wiki/File:Calamari_fritti_in_Izola_Isola_(52976884396).jpg) | domjisch from Graz, Austria | CC BY 2.0 |
| `arancini-di-risotto.jpg` | [Arancini 002.jpg](https://commons.wikimedia.org/wiki/File:Arancini_002.jpg) | No machine-readable author provided. Gmelfi assumed (based on copyright claims). | Public domain |
| `focaccia-al-rosmarino.jpg` | [Rosemary Focaccia.jpg](https://commons.wikimedia.org/wiki/File:Rosemary_Focaccia.jpg) | Parkerman &amp; Christie from San Diego, USA | CC BY 2.0 |
| `zuppa-minestrone.jpg` | [Minestrone soup.jpg](https://commons.wikimedia.org/wiki/File:Minestrone_soup.jpg) | Katrin Morenz from Aachen, Deutschland | CC BY-SA 2.0 |
| `burrata-con-tomates-cherry.jpg` | [Burrata salad with cherry tomatoes and rocket from La Mensa Grill and Bar Plaza88.jpg](https://commons.wikimedia.org/wiki/File:Burrata_salad_with_cherry_tomatoes_and_rocket_from_La_Mensa_Grill_and_Bar_Plaza88.jpg) | Peachyeung316 | CC BY-SA 4.0 |
| `antipasto-misto.jpg` | [Antipasto Misto Con Bruschette.jpg](https://commons.wikimedia.org/wiki/File:Antipasto_Misto_Con_Bruschette.jpg) | AlMare (usuario de Commons) | CC BY 2.0 |
| `pizza-margherita.jpg` | [Margherita Originale.JPG](https://commons.wikimedia.org/wiki/File:Margherita_Originale.JPG) | Mario56 | CC BY-SA 3.0 |
| `pizza-pepperoni.jpg` | [Pepperoni Pizza from Fellini’s Pizza.jpg](https://commons.wikimedia.org/wiki/File:Pepperoni_Pizza_from_Fellini%E2%80%99s_Pizza.jpg) | BullDawg2021 | CC BY 4.0 |
| `pizza-quattro-formaggi.jpg` | [Four Cheese - Pizza 500 2023-11-10.jpg](https://commons.wikimedia.org/wiki/File:Four_Cheese_-_Pizza_500_2023-11-10.jpg) | Andy Li | CC0 |
| `spaghetti-alla-carbonara.jpg` | [Espaguetis carbonara.jpg](https://commons.wikimedia.org/wiki/File:Espaguetis_carbonara.jpg) | Javier Somoza | CC BY-SA 4.0 |
| `fettuccine-alfredo.jpg` | [Fettuccine Alfredo.jpg](https://commons.wikimedia.org/wiki/File:Fettuccine_Alfredo.jpg) | Robert Banh | CC BY 2.0 |
| `lasagna-alla-bolognese.jpg` | [Meaty Lasagna 8of8 (8736299782).jpg](https://commons.wikimedia.org/wiki/File:Meaty_Lasagna_8of8_(8736299782).jpg) | Breville USA | CC BY 2.0 |
| `gnocchi-al-pesto.jpg` | [Gnocchi with pesto (3269919059).jpg](https://commons.wikimedia.org/wiki/File:Gnocchi_with_pesto_(3269919059).jpg) | Karen and Brad Emerson | CC BY 2.0 |
| `risotto-ai-funghi.jpg` | [Risotto Champignons.jpg](https://commons.wikimedia.org/wiki/File:Risotto_Champignons.jpg) | PixelBrûlé | CC BY-SA 4.0 |
| `pollo-alla-parmigiana.jpg` | [Tony's of North Beach - December 2022 - Sarah Stierch 05.jpg](https://commons.wikimedia.org/wiki/File:Tony%27s_of_North_Beach_-_December_2022_-_Sarah_Stierch_05.jpg) | Missvain | CC BY 4.0 |
| `tiramisu.jpg` | [Tiramisu - Bistro Don Giovanni - Sarah Stierch 2018 02.jpg](https://commons.wikimedia.org/wiki/File:Tiramisu_-_Bistro_Don_Giovanni_-_Sarah_Stierch_2018_02.jpg) | Missvain | CC BY 4.0 |
| `panna-cotta.jpg` | [Panna Cotta with cream and garnish.jpg](https://commons.wikimedia.org/wiki/File:Panna_Cotta_with_cream_and_garnish.jpg) | hiro | CC BY-SA 2.0 |
| `cannoli-siciliani.jpg` | [Tiny sicilian cannoli at lunch (5071817409).jpg](https://commons.wikimedia.org/wiki/File:Tiny_sicilian_cannoli_at_lunch_(5071817409).jpg) | judywitts | CC BY 2.0 |
| `affogato-al-caffe.jpg` | [Vinoteca, Smithfield, London (4485849609).jpg](https://commons.wikimedia.org/wiki/File:Vinoteca,_Smithfield,_London_(4485849609).jpg) | Ewan Munro from London, UK | CC BY-SA 2.0 |
| `torta-caprese.jpg` | [Tortacapresespot.jpeg](https://commons.wikimedia.org/wiki/File:Tortacapresespot.jpeg) | Mgdongarra | CC0 |
| `semifreddo-al-limone.jpg` | [Semifreddo nocciola.jpg](https://commons.wikimedia.org/wiki/File:Semifreddo_nocciola.jpg) | Daniele2399 | CC BY-SA 4.0 |
| `zeppole.jpg` | [Zeppole stacked on a plate.jpg](https://commons.wikimedia.org/wiki/File:Zeppole_stacked_on_a_plate.jpg) | Luca Sartoni | CC BY-SA 2.0 |
| `torta-della-nonna.jpg` | [Torta della nonna.jpg](https://commons.wikimedia.org/wiki/File:Torta_della_nonna.jpg) | fugzu from Pistoia, Italia | CC BY 2.0 |
| `empanadas-colombianas.jpg` | [Empanada colombiana.jpg](https://commons.wikimedia.org/wiki/File:Empanada_colombiana.jpg) | Francesc Fort | CC BY-SA 4.0 |
| `arepa-con-queso.jpg` | [Arepa de chocolo.jpg](https://commons.wikimedia.org/wiki/File:Arepa_de_chocolo.jpg) | Nelson Fernando Sotelo Castro | CC BY 2.0 |
| `patacones.jpg` | [Patacones - Barranquilla.jpg](https://commons.wikimedia.org/wiki/File:Patacones_-_Barranquilla.jpg) | Jdvillalobos | CC BY 3.0 |
| `ajiaco-santafereno.jpg` | [Ajiaco la puerta falsa.jpg](https://commons.wikimedia.org/wiki/File:Ajiaco_la_puerta_falsa.jpg) | Cesar.cely | CC BY-SA 4.0 |
| `bandeja-paisa.jpg` | [Bandeja paisa, plato Colombiano.jpg](https://commons.wikimedia.org/wiki/File:Bandeja_paisa,_plato_Colombiano.jpg) | Wilfredor | CC0 |
| `sancocho-de-gallina.jpg` | [Sancocho cruzado de gallina, rabo y costilla con arepa.jpg](https://commons.wikimedia.org/wiki/File:Sancocho_cruzado_de_gallina,_rabo_y_costilla_con_arepa.jpg) | Rodolfo pimentel | CC BY-SA 4.0 |
| `brevas-en-almibar.jpg` | [Incir Kompostosu (Fig in Syrup).JPG](https://commons.wikimedia.org/wiki/File:Incir_Kompostosu_(Fig_in_Syrup).JPG) | Miansari66 | CC0 |
| `limonada-de-coco.jpg` | [Coconut Drink (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Coconut_Drink_(Unsplash).jpg) | Alexander Mils alexandermils | CC0 |
| `cafe-colombiano.jpg` | [A small cup of coffee.JPG](https://commons.wikimedia.org/wiki/File:A_small_cup_of_coffee.JPG) | Julius Schorzman | CC BY-SA 2.0 |
| `agua-de-panela.jpg` | [Aguapanela-Colombiana-3-2.jpg](https://commons.wikimedia.org/wiki/File:Aguapanela-Colombiana-3-2.jpg) | Mappa Stellae | CC BY-SA 4.0 |
| `chocolate-con-queso.jpg` | [Colombian classic - hot chocolate with arepa and cheese (in porcelain with pink flowers).jpg](https://commons.wikimedia.org/wiki/File:Colombian_classic_-_hot_chocolate_with_arepa_and_cheese_(in_porcelain_with_pink_flowers).jpg) | Quinn Comendant | CC BY-SA 2.0 |
| `edamame.jpg` | [Edamame by jark.jpg](https://commons.wikimedia.org/wiki/File:Edamame_by_jark.jpg) | jark | CC BY-SA 2.0 |
| `gyozas-de-cerdo.jpg` | [Pork gyoza - Massachusetts.jpg](https://commons.wikimedia.org/wiki/File:Pork_gyoza_-_Massachusetts.jpg) | Daderot | CC0 |
| `tempura-de-camaron.jpg` | [Tempura Prawns at Southport Surf Life Saving Club, Main Beach, Queensland.jpg](https://commons.wikimedia.org/wiki/File:Tempura_Prawns_at_Southport_Surf_Life_Saving_Club,_Main_Beach,_Queensland.jpg) | Kgbo | CC BY-SA 4.0 |
| `sopa-miso.jpg` | [Miso Soup 001.jpg](https://commons.wikimedia.org/wiki/File:Miso_Soup_001.jpg) | Ocdp | CC0 |
| `ramen-tonkotsu.jpg` | [Tonkotsu Ramen - Goemon Ramen Bar 2023-06-06.jpg](https://commons.wikimedia.org/wiki/File:Tonkotsu_Ramen_-_Goemon_Ramen_Bar_2023-06-06.jpg) | Andy Li | CC0 |
| `california-roll.jpg` | [California Sushi mit Kaviar (26545022496).jpg](https://commons.wikimedia.org/wiki/File:California_Sushi_mit_Kaviar_(26545022496).jpg) | Tim Reckmann from Hamm, Deutschland | CC BY 2.0 |
| `sashimi-de-salmon.jpg` | [Salmon sashimi Yuichiro Haga.jpeg](https://commons.wikimedia.org/wiki/File:Salmon_sashimi_Yuichiro_Haga.jpeg) | Yuichiro Haga | CC BY 2.0 |
| `nigiri-de-salmon.jpg` | [Nigiri Sushi (25966163204).jpg](https://commons.wikimedia.org/wiki/File:Nigiri_Sushi_(25966163204).jpg) | Tim Reckmann from Hamm, Deutschland | CC BY 2.0 |
| `yakisoba-de-pollo.jpg` | [Chicken yakisoba Merelymel13.jpg](https://commons.wikimedia.org/wiki/File:Chicken_yakisoba_Merelymel13.jpg) | Merelymel13 | CC BY-SA 2.0 |
| `mochi-helado.jpg` | [Mochi Ice Cream.jpg](https://commons.wikimedia.org/wiki/File:Mochi_Ice_Cream.jpg) | Charles Nguyen | Public domain |
| `dorayaki.jpg` | [Dorayaki 004.jpg](https://commons.wikimedia.org/wiki/File:Dorayaki_004.jpg) | Ocdp | CC0 |
| `cheesecake-de-matcha.jpg` | [Olea Matcha Cheesecake with olive oil - Olea 2025-07-03.jpg](https://commons.wikimedia.org/wiki/File:Olea_Matcha_Cheesecake_with_olive_oil_-_Olea_2025-07-03.jpg) | Andy Li | CC0 |
| `te-verde-japones.jpg` | [2018 Uji lightly steamed sencha - first infusion.jpg](https://commons.wikimedia.org/wiki/File:2018_Uji_lightly_steamed_sencha_-_first_infusion.jpg) | Difference engine | CC BY-SA 4.0 |
| `provoleta-a-la-parrilla.jpg` | [Provoleta con cazuela (porción).jpg](https://commons.wikimedia.org/wiki/File:Provoleta_con_cazuela_(porci%C3%B3n).jpg) | Horacio Cambeiro | CC BY 3.0 |
| `chorizo-criollo.jpg` | [Chorizo a la parrilla de Argentina.jpg](https://commons.wikimedia.org/wiki/File:Chorizo_a_la_parrilla_de_Argentina.jpg) | Horacio Cambeiro | CC BY 3.0 |
| `mazorca-asada.jpg` | [Grilled Corn on the cob.JPG](https://commons.wikimedia.org/wiki/File:Grilled_Corn_on_the_cob.JPG) | Namitakhaire | CC BY-SA 4.0 |
| `churrasco-de-res.jpg` | [DFC 2244 Juicy grilled steak smothered in savory brown gravy served with roasted potatoes sautéed vegetables and a crisp mixed salad.jpg](https://commons.wikimedia.org/wiki/File:DFC_2244_Juicy_grilled_steak_smothered_in_savory_brown_gravy_served_with_roasted_potatoes_saut%C3%A9ed_vegetables_and_a_crisp_mixed_salad.jpg) | PattayaPatrol | CC BY-SA 4.0 |
| `picana-a-la-brasa.jpg` | [Picanha (14759358544).jpg](https://commons.wikimedia.org/wiki/File:Picanha_(14759358544).jpg) | Christian Benseler | CC BY 2.0 |
| `costillas-bbq.jpg` | [BBQ RIBS pork side ribs.jpg](https://commons.wikimedia.org/wiki/File:BBQ_RIBS_pork_side_ribs.jpg) | WorldwrestlingfederationVKM | CC BY-SA 3.0 |
| `pollo-a-las-brasas.jpg` | [Pollo a la brasa peruano.jpg](https://commons.wikimedia.org/wiki/File:Pollo_a_la_brasa_peruano.jpg) | Manuel González Olaechea | CC BY-SA 3.0 |
| `salmon-a-la-parrilla.jpg` | [Grilled plated salmon fillet.jpg](https://commons.wikimedia.org/wiki/File:Grilled_plated_salmon_fillet.jpg) | DanaTentis | CC0 |
| `brownie-con-helado.jpg` | [Walnut brownie with ice-cream.jpg](https://commons.wikimedia.org/wiki/File:Walnut_brownie_with_ice-cream.jpg) | Sirsendu.mohanta | CC BY-SA 4.0 |
| `flan-de-caramelo.jpg` | [Crème caramel at NB Steak JK.jpg](https://commons.wikimedia.org/wiki/File:Cr%C3%A8me_caramel_at_NB_Steak_JK.jpg) | Oleg Yunakov | CC BY-SA 4.0 |
| `copa-de-vino-tinto.jpg` | [A glass of red wine.jpg](https://commons.wikimedia.org/wiki/File:A_glass_of_red_wine.jpg) | Davide Restivo from Lenzburg, Aarau, Switzerland | CC BY-SA 2.0 |
| `limonada-de-hierbabuena.jpg` | [Homemade Mint Lemonade,Bangladesh.jpg](https://commons.wikimedia.org/wiki/File:Homemade_Mint_Lemonade,Bangladesh.jpg) | Evening42 | CC BY-SA 4.0 |
#   P a r c i a l - T e l l e z  
 
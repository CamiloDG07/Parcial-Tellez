# Cambios de fotos y cartas (Fase 6)

Comparación visual: `docs/fotos_antes_despues.png` (hoja de contactos por restaurante y pares antes → después de las fotos reemplazadas).
Todas las fotos vienen de **Wikimedia Commons**; archivo, autor y licencia salen de la API de Commons (`tools/descargar_fotos.py`), no se escribieron a mano. Solo CC0, dominio público, CC BY y CC BY-SA. No se usó Pexels, Unsplash ni Pixabay (Commons cubrió todos los platos y deja la licencia verificable por archivo). Una de las fotos (`limonada-de-coco`) es un archivo de Commons cuyo título menciona Unsplash; en Commons figura como CC0.
Todas se recortan a 8:5 centrando el plato, con auto-contraste y nitidez suaves y homogéneos: `<slug>.jpg` 800×500 (< 250 KB) y `<slug>@400.jpg` 400×250.

## Método de selección

1. `tools/buscar_candidatas.py` busca en Commons JPEG horizontales de al menos 1200 px con licencia permitida (descarta NC/ND) y arma una hoja de contactos por plato con 8 candidatas.
2. Se revisó cada hoja a ojo y se eligió la candidata que mejor cumple: el plato de la foto es el plato del nombre, buena luz y foco, plato protagonista, sin personas ni manos, sin logos ni texto, fondo limpio.
3. Si ninguna candidata servía, el plato se quitó de la carta (ver abajo). Las consultas usadas están en `tools/consultas_fotos.json`.

## Fotos nuevas (36)

| Plato (slug) | Foto en Commons | Autor | Licencia |
|---|---|---|---|
| **Restaurante 2: La Cocina del Turno Noche** | | | |
| `empanadas-colombianas` | [Empanada colombiana.jpg](https://commons.wikimedia.org/wiki/File:Empanada_colombiana.jpg) | Francesc Fort | CC BY-SA 4.0 |
| `arepa-con-queso` | [Arepa de chocolo.jpg](https://commons.wikimedia.org/wiki/File:Arepa_de_chocolo.jpg) | Nelson Fernando Sotelo Castro | CC BY 2.0 |
| `patacones` | [Patacones - Barranquilla.jpg](https://commons.wikimedia.org/wiki/File:Patacones_-_Barranquilla.jpg) | Jdvillalobos | CC BY 3.0 |
| `ajiaco-santafereno` | [Ajiaco la puerta falsa.jpg](https://commons.wikimedia.org/wiki/File:Ajiaco_la_puerta_falsa.jpg) | Cesar.cely | CC BY-SA 4.0 |
| `bandeja-paisa` | [Bandeja paisa, plato Colombiano.jpg](https://commons.wikimedia.org/wiki/File:Bandeja_paisa,_plato_Colombiano.jpg) | Wilfredor | CC0 |
| `sancocho-de-gallina` | [Sancocho cruzado de gallina, rabo y costilla con arepa.jpg](https://commons.wikimedia.org/wiki/File:Sancocho_cruzado_de_gallina,_rabo_y_costilla_con_arepa.jpg) | Rodolfo pimentel | CC BY-SA 4.0 |
| `brevas-en-almibar` | [Incir Kompostosu (Fig in Syrup).JPG](https://commons.wikimedia.org/wiki/File:Incir_Kompostosu_(Fig_in_Syrup).JPG) | Miansari66 | CC0 |
| `limonada-de-coco` | [Coconut Drink (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Coconut_Drink_(Unsplash).jpg) | Alexander Mils alexandermils | CC0 |
| `cafe-colombiano` | [A small cup of coffee.JPG](https://commons.wikimedia.org/wiki/File:A_small_cup_of_coffee.JPG) | Julius Schorzman | CC BY-SA 2.0 |
| `agua-de-panela` | [Aguapanela-Colombiana-3-2.jpg](https://commons.wikimedia.org/wiki/File:Aguapanela-Colombiana-3-2.jpg) | Mappa Stellae | CC BY-SA 4.0 |
| `chocolate-con-queso` | [Colombian classic - hot chocolate with arepa and cheese (in porcelain with pink flowers).jpg](https://commons.wikimedia.org/wiki/File:Colombian_classic_-_hot_chocolate_with_arepa_and_cheese_(in_porcelain_with_pink_flowers).jpg) | Quinn Comendant | CC BY-SA 2.0 |
| **Restaurante 3: Pasillo Este Sushi** | | | |
| `edamame` | [Edamame by jark.jpg](https://commons.wikimedia.org/wiki/File:Edamame_by_jark.jpg) | jark | CC BY-SA 2.0 |
| `gyozas-de-cerdo` | [Pork gyoza - Massachusetts.jpg](https://commons.wikimedia.org/wiki/File:Pork_gyoza_-_Massachusetts.jpg) | Daderot | CC0 |
| `tempura-de-camaron` | [Tempura Prawns at Southport Surf Life Saving Club, Main Beach, Queensland.jpg](https://commons.wikimedia.org/wiki/File:Tempura_Prawns_at_Southport_Surf_Life_Saving_Club,_Main_Beach,_Queensland.jpg) | Kgbo | CC BY-SA 4.0 |
| `sopa-miso` | [Miso Soup 001.jpg](https://commons.wikimedia.org/wiki/File:Miso_Soup_001.jpg) | Ocdp | CC0 |
| `ramen-tonkotsu` | [Tonkotsu Ramen - Goemon Ramen Bar 2023-06-06.jpg](https://commons.wikimedia.org/wiki/File:Tonkotsu_Ramen_-_Goemon_Ramen_Bar_2023-06-06.jpg) | Andy Li | CC0 |
| `california-roll` | [California Sushi mit Kaviar (26545022496).jpg](https://commons.wikimedia.org/wiki/File:California_Sushi_mit_Kaviar_(26545022496).jpg) | Tim Reckmann from Hamm, Deutschland | CC BY 2.0 |
| `sashimi-de-salmon` | [Salmon sashimi Yuichiro Haga.jpeg](https://commons.wikimedia.org/wiki/File:Salmon_sashimi_Yuichiro_Haga.jpeg) | Yuichiro Haga | CC BY 2.0 |
| `nigiri-de-salmon` | [Nigiri Sushi (25966163204).jpg](https://commons.wikimedia.org/wiki/File:Nigiri_Sushi_(25966163204).jpg) | Tim Reckmann from Hamm, Deutschland | CC BY 2.0 |
| `yakisoba-de-pollo` | [Chicken yakisoba Merelymel13.jpg](https://commons.wikimedia.org/wiki/File:Chicken_yakisoba_Merelymel13.jpg) | Merelymel13 | CC BY-SA 2.0 |
| `mochi-helado` | [Mochi Ice Cream.jpg](https://commons.wikimedia.org/wiki/File:Mochi_Ice_Cream.jpg) | Charles Nguyen | Public domain |
| `dorayaki` | [Dorayaki 004.jpg](https://commons.wikimedia.org/wiki/File:Dorayaki_004.jpg) | Ocdp | CC0 |
| `cheesecake-de-matcha` | [Olea Matcha Cheesecake with olive oil - Olea 2025-07-03.jpg](https://commons.wikimedia.org/wiki/File:Olea_Matcha_Cheesecake_with_olive_oil_-_Olea_2025-07-03.jpg) | Andy Li | CC0 |
| `te-verde-japones` | [2018 Uji lightly steamed sencha - first infusion.jpg](https://commons.wikimedia.org/wiki/File:2018_Uji_lightly_steamed_sencha_-_first_infusion.jpg) | Difference engine | CC BY-SA 4.0 |
| **Restaurante 4: Cámara 04 Parrilla** | | | |
| `provoleta-a-la-parrilla` | [Provoleta con cazuela (porción).jpg](https://commons.wikimedia.org/wiki/File:Provoleta_con_cazuela_(porci%C3%B3n).jpg) | Horacio Cambeiro | CC BY 3.0 |
| `chorizo-criollo` | [Chorizo a la parrilla de Argentina.jpg](https://commons.wikimedia.org/wiki/File:Chorizo_a_la_parrilla_de_Argentina.jpg) | Horacio Cambeiro | CC BY 3.0 |
| `mazorca-asada` | [Grilled Corn on the cob.JPG](https://commons.wikimedia.org/wiki/File:Grilled_Corn_on_the_cob.JPG) | Namitakhaire | CC BY-SA 4.0 |
| `churrasco-de-res` | [DFC 2244 Juicy grilled steak smothered in savory brown gravy served with roasted potatoes sautéed vegetables and a crisp mixed salad.jpg](https://commons.wikimedia.org/wiki/File:DFC_2244_Juicy_grilled_steak_smothered_in_savory_brown_gravy_served_with_roasted_potatoes_saut%C3%A9ed_vegetables_and_a_crisp_mixed_salad.jpg) | PattayaPatrol | CC BY-SA 4.0 |
| `picana-a-la-brasa` | [Picanha (14759358544).jpg](https://commons.wikimedia.org/wiki/File:Picanha_(14759358544).jpg) | Christian Benseler | CC BY 2.0 |
| `costillas-bbq` | [BBQ RIBS pork side ribs.jpg](https://commons.wikimedia.org/wiki/File:BBQ_RIBS_pork_side_ribs.jpg) | WorldwrestlingfederationVKM | CC BY-SA 3.0 |
| `pollo-a-las-brasas` | [Pollo a la brasa peruano.jpg](https://commons.wikimedia.org/wiki/File:Pollo_a_la_brasa_peruano.jpg) | Manuel González Olaechea | CC BY-SA 3.0 |
| `salmon-a-la-parrilla` | [Grilled plated salmon fillet.jpg](https://commons.wikimedia.org/wiki/File:Grilled_plated_salmon_fillet.jpg) | DanaTentis | CC0 |
| `brownie-con-helado` | [Walnut brownie with ice-cream.jpg](https://commons.wikimedia.org/wiki/File:Walnut_brownie_with_ice-cream.jpg) | Sirsendu.mohanta | CC BY-SA 4.0 |
| `flan-de-caramelo` | [Crème caramel at NB Steak JK.jpg](https://commons.wikimedia.org/wiki/File:Cr%C3%A8me_caramel_at_NB_Steak_JK.jpg) | Oleg Yunakov | CC BY-SA 4.0 |
| `copa-de-vino-tinto` | [A glass of red wine.jpg](https://commons.wikimedia.org/wiki/File:A_glass_of_red_wine.jpg) | Davide Restivo from Lenzburg, Aarau, Switzerland | CC BY-SA 2.0 |
| `limonada-de-hierbabuena` | [Homemade Mint Lemonade,Bangladesh.jpg](https://commons.wikimedia.org/wiki/File:Homemade_Mint_Lemonade,Bangladesh.jpg) | Evening42 | CC BY-SA 4.0 |

## Fotos reemplazadas en las cartas 1 y 5 (mismo slug)

| Plato (slug) | Foto nueva | Autor | Licencia | Foto anterior | Motivo |
|---|---|---|---|---|---|
| `carpaccio-di-manzo` | [Beef Carpaccio (3466985953).jpg](https://commons.wikimedia.org/wiki/File:Beef_Carpaccio_(3466985953).jpg) | Mack Male from Edmonton, AB, Canada | CC BY-SA 2.0 | Carpaccio Cipriani.jpg | La anterior tenía la mayonesa en zigzag, poco apetitosa; la nueva muestra carpaccio con rúcula y parmesano. |
| `burrata-con-tomates-cherry` | [Burrata salad with cherry tomatoes and rocket from La Mensa Grill and Bar Plaza88.jpg](https://commons.wikimedia.org/wiki/File:Burrata_salad_with_cherry_tomatoes_and_rocket_from_La_Mensa_Grill_and_Bar_Plaza88.jpg) | Peachyeung316 | CC BY-SA 4.0 | Burrata2.jpg | La anterior era una bola blanca sin tomates en el plato; la nueva es una burrata sobre rúcula con tomates cherry y balsámico. |
| `calamares-fritti` | [Calamari fritti in Izola Isola (52976884396).jpg](https://commons.wikimedia.org/wiki/File:Calamari_fritti_in_Izola_Isola_(52976884396).jpg) | domjisch from Graz, Austria | CC BY 2.0 | Fried Calamari Rings.jpg | Los aros anteriores parecían de cebolla; la nueva muestra calamares fritos variados con limón y salsa. |
| `cannoli-siciliani` | [Tiny sicilian cannoli at lunch (5071817409).jpg](https://commons.wikimedia.org/wiki/File:Tiny_sicilian_cannoli_at_lunch_(5071817409).jpg) | judywitts | CC BY 2.0 | Cannoli from Brocato's New Orleans 01.jpg | La anterior tenía mala luz; la nueva es de un plato blanco, con luz pareja. |
| `fettuccine-alfredo` | [Fettuccine Alfredo.jpg](https://commons.wikimedia.org/wiki/File:Fettuccine_Alfredo.jpg) | Robert Banh | CC BY 2.0 | Fiamma - Fettuccine with Alfredo Sauce.jpg | La anterior llevaba camarones y el plato no los menciona; la nueva es fettuccine Alfredo sin camarones. |
| `bruschetta-clasica` | [Bruschetta at The Bar at MacArthur Place - Sarah Stierch.jpg](https://commons.wikimedia.org/wiki/File:Bruschetta_at_The_Bar_at_MacArthur_Place_-_Sarah_Stierch.jpg) | Missvain | CC BY 4.0 | A typical Maltese bruschetta with fresh Mediterranean ingredients.jpg | El recorte anterior era pobre; la nueva es cenital, centrada, con tomate fresco y albahaca. |

## Fotos conservadas (revisadas con los mismos criterios)

- `torta-della-nonna`: se conserva. Es la torta con piñones y sí es el plato; no apareció una alternativa mejor con licencia libre (la búsqueda solo devolvió una candidata adicional, que no era el plato). Reconozco que a primera vista puede parecer pan.
- `torta-caprese`: se conserva la misma foto de Commons porque la única otra candidata mostraba una mano sosteniendo el plato; se aclara con un ajuste de gamma (`tools/fotos_centros.json`) para que no se vea tan oscura.
- `gnocchi-al-pesto`: se conserva (recorte manual con zoom). El resto de las fotos de las cartas 1 y 5 se conservan: ninguna candidata fue claramente mejor.

## Platos quitados o cambiados en las cartas nuevas (borradores `cartas_borrador/`)

| Carta | Plato del borrador | Qué pasó | Motivo |
|---|---|---|---|
| 2 | Morcilla con Arepa | Quitado | No hubo foto buena de morcilla colombiana con licencia libre (las candidatas eran morcilla española o con manos). |
| 2 | Sobrebarriga a la Criolla | Quitado | Solo había carne cruda o platos que no son sobrebarriga. |
| 2 | Obleas con Arequipe | Quitado | Las fotos eran puestos callejeros con personas y letreros. |
| 2 | Cuajada con Melao | Quitado | La cuajada de Commons es española (no se parece al plato colombiano) o aparece en empaques con marca. |
| 2 | Brevas con Arequipe | Cambiado a **Brevas en Almíbar** (`brevas-en-almibar`) | La foto es de higos (brevas) en almíbar con frutos secos; no tiene arequipe. Se renombró y se reescribió la descripción. |
| 2 | Patacones con Hogao | Cambiado a **Patacones** (`patacones`) | La foto no muestra hogao. |
| 2 | Agua de Panela con Limón | Cambiado a **Agua de Panela con Queso y Pan** (`agua-de-panela`) | La foto muestra panela con queso y pan, sin limón. |
| 2 | (nuevo) | Añadido **Chocolate con Queso y Arepa** (`chocolate-con-queso`), $12.000 | Foto clara de ese plato; sirve para llegar a 10 platos. Precio de demostración. |
| 2 | Limonada de Coco | Conservado | La foto es una bebida cremosa de coco en vaso con coco al lado; es una suposición razonable, no una foto de limonada de coco con certeza. |
| 3 | Nigiri Variado | Cambiado a **Nigiri de Salmón** (`nigiri-de-salmon`) | No hubo foto buena de un surtido; la foto es un nigiri de salmón. |
| 4 | Papas Criollas Salteadas | Quitado | Las fotos eran de papas en mercado o platos mezclados. |
| 4 | Punta de Anca | Quitado | La búsqueda no devolvió ninguna foto de ese corte. |
| 4 | Churrasco de Res | Conservado con foto de un bistec a la parrilla con salsa y papas | No es un churrasco típico argentino; es el bistec a la parrilla más reconocible que había. |

Resultado: carta 1 = 12 platos, carta 2 = 11, carta 3 = 13, carta 4 = 12, carta 5 = 14; 62 fotos en total (26 + 36).

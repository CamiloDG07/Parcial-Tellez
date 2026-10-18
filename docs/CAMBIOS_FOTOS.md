# Cambios de fotos (Fase 5)

Comparación en `docs/fotos_antes.png` y `docs/fotos_despues.png`. Todos los datos de archivo, autor y licencia salen de la API de Wikimedia Commons (`tools/descargar_fotos.py`); nada se escribió a mano.

## Fotos reemplazadas (11)

| Plato | Archivo anterior | Archivo nuevo | Autor | Licencia | Motivo |
|---|---|---|---|---|---|
| ensalada-caprese | Insalata caprese in Israel.jpg | [Caprese salad in homemade.jpg](https://commons.wikimedia.org/wiki/File:Caprese_salad_in_homemade.jpg) | spiralmushroom | CC BY 2.0 | Cambio extra: la anterior tenía texto escrito en el plato; la nueva no tiene texto y llena el encuadre. |
| antipasto-misto | Antipasto Platter.jpg | [Antipasto Misto Con Bruschette.jpg](https://commons.wikimedia.org/wiki/File:Antipasto_Misto_Con_Bruschette.jpg) | AlMare (usuario de Commons) | CC BY 2.0 | La anterior era un plato de salmón/fiambres con distintos elementos poco claros; la nueva es un plato blanco con embutidos, bruschette, aceitunas y pimientos: reconocible como antipasto misto. |
| pizza-quattro-formaggi | Four cheese pizza.jpg | [Four Cheese - Pizza 500 2023-11-10.jpg](https://commons.wikimedia.org/wiki/File:Four_Cheese_-_Pizza_500_2023-11-10.jpg) | Andy Li | CC0 | La anterior era una pizza casi toda blanca en la que no se distinguían los quesos; la nueva muestra varios quesos bien visibles sobre tomate, bien enfocada, CC0. |
| fettuccine-alfredo | Chicken fettuccine alfredo.JPG | [Fiamma - Fettuccine with Alfredo Sauce.jpg](https://commons.wikimedia.org/wiki/File:Fiamma_-_Fettuccine_with_Alfredo_Sauce.jpg) | Calgary Reviews | CC BY 2.0 | La anterior incluía una ensalada César al lado; la nueva es un solo plato de fettuccine con salsa Alfredo, de cerca. Limitación: lleva camarones. |
| gnocchi-al-pesto | Gnocchi al pesto 02.jpg | [Gnocchi with pesto (3269919059).jpg](https://commons.wikimedia.org/wiki/File:Gnocchi_with_pesto_(3269919059).jpg) | Karen and Brad Emerson | CC BY 2.0 | La anterior tenía color pardo poco apetecible; la nueva muestra ñoquis verdes de pesto en un bowl blanco (recorte manual con zoom 1,5 para centrar el bowl). |
| risotto-ai-funghi | Mushroom Risotto (4789415965).jpg | [Risotto Champignons.jpg](https://commons.wikimedia.org/wiki/File:Risotto_Champignons.jpg) | PixelBrûlé | CC BY-SA 4.0 | La anterior era un salteado de hongos en sartén, sin arroz; la nueva es un risotto en plato hondo con champiñones salteados encima. |
| pollo-alla-parmigiana | Chicken parmigiana.jpg | [Tony's of North Beach - December 2022 - Sarah Stierch 05.jpg](https://commons.wikimedia.org/wiki/File:Tony%27s_of_North_Beach_-_December_2022_-_Sarah_Stierch_05.jpg) | Missvain | CC BY 4.0 | La anterior mostraba pollo con papas fritas y ensalada; la nueva muestra el pollo con salsa de tomate y mozzarella gratinada sobre pasta, plato único. |
| tiramisu | Dolce Tiramisù monoporzione.jpg | [Tiramisu - Bistro Don Giovanni - Sarah Stierch 2018 02.jpg](https://commons.wikimedia.org/wiki/File:Tiramisu_-_Bistro_Don_Giovanni_-_Sarah_Stierch_2018_02.jpg) | Missvain | CC BY 4.0 | La anterior (plato con adorno floral y tablero a cuadros) no se reconocía como tiramisú; la nueva muestra las capas de bizcocho, crema y cacao sobre plato blanco. |
| cannoli-siciliani | Cannoli in a box.jpg | [Cannoli from Brocato's New Orleans 01.jpg](https://commons.wikimedia.org/wiki/File:Cannoli_from_Brocato%27s_New_Orleans_01.jpg) | Infrogmation of New Orleans | CC BY-SA 4.0 | La anterior eran cannoli dentro de una caja de cartón; la nueva es un cannolo en plato de cerca (el archivo original es una foto de New Orleans, no siciliana). |
| affogato-al-caffe | Affogato.JPG | [Vinoteca, Smithfield, London (4485849609).jpg](https://commons.wikimedia.org/wiki/File:Vinoteca,_Smithfield,_London_(4485849609).jpg) | Ewan Munro from London, UK | CC BY-SA 2.0 | La anterior era una jarra y un tazón con helado poco apetecible; la nueva es una taza con dos bolas de helado sobre café, con platillo, luz cálida. |
| torta-caprese | Torta caprese with confectioner's sugar and chocolate sauce (7830104492).jpg | [Tortacapresespot.jpeg](https://commons.wikimedia.org/wiki/File:Tortacapresespot.jpeg) | Mgdongarra | CC0 | La anterior tenía un recorte raro (porción con tenedor, cortada); la nueva muestra la torta entera, centrada, con la almendra, y es CC0. |

## Conservadas con la misma fuente

15 fotos conservan su archivo de Commons; todas se regeneraron con el nuevo recorte (plato centrado) y el auto-contraste/nitidez homogéneos: bruschetta-clasica, carpaccio-di-manzo, calamares-fritti, arancini-di-risotto, focaccia-al-rosmarino, zuppa-minestrone, burrata-con-tomates-cherry, pizza-margherita, pizza-pepperoni, spaghetti-alla-carbonara, lasagna-alla-bolognese, panna-cotta, semifreddo-al-limone, zeppole, torta-della-nonna.

Nota: `torta-della-nonna` estaba entre las marcadas como flojas y se conservó. CONSERVADA: la única candidata alternativa (limón con crema y menú con precios al fondo) no es la torta clásica y tenía texto; la actual sí es la torta con piñones. Se suaviza el aspecto con el nuevo auto-contraste.

## Cómo se eligió

- `tools/buscar_candidatas.py` busca en Commons solo JPEG de al menos 1600 px y licencia CC0 / dominio público / CC BY / CC BY-SA (las NC/ND se descartan), prioriza las categorías Featured/Quality/Valued y arma una hoja de contacto por plato; se revisaron a ojo 8–12 candidatas por plato (ninguna de las que se probaron tenía categoría de calidad salvo 1 o 2, que no eran las mejores).
- Criterios: un plato protagonista y reconocible, sin manos ni personas ni texto ni logos, buena luz y fondo limpio.
- Formato: `<slug>.jpg` 800×500 (< 250 KB) y `<slug>@400.jpg` 400×250.

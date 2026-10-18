# Cartas de demostración (una por restaurante)

Cada archivo `<id>.json` es la carta del restaurante con ese `id` del seed (`app/datos/seed.py`):

| id | Restaurante | Cocina |
|----|-------------|--------|
| 1 | Slice Palace Medianoche | Pizzería |
| 2 | La Cocina del Turno Noche | Colombiana |
| 3 | Pasillo Este Sushi | Japonesa |
| 4 | Cámara 04 Parrilla | Parrilla |
| 5 | Backstage Pasta & Vino | Italiana |

Formato:

```json
{
  "restaurante_id": 2,
  "restaurante": "La Cocina del Turno Noche",
  "origen": "texto libre (quién escribió la carta)",
  "moneda": "COP",
  "categorias": [
    {"nombre": "Entrada", "orden": 1, "productos": [
      {"nombre": "Empanadas", "descripcion": "…", "precio_cop": 14000, "slug_foto": "empanadas-colombianas"}
    ]}
  ]
}
```

Reglas (las comprueba `tests/test_cartas_demo.py`):

- `precio_cop` es un entero positivo en pesos colombianos.
- Cada `slug_foto` tiene su foto `app/presentacion/static/img/platos/<slug>.jpg` (800×500, menos de 250 KB),
  su versión `<slug>@400.jpg` (400×250) y su entrada con autor y licencia en `CREDITOS.json`.
- **Ningún slug se repite entre restaurantes**: cada carta tiene sus propias fotos.
- Los nombres de plato no se repiten dentro de un restaurante.

La carta de los restaurantes 1 y 5 parte del menú del repositorio PIZZATRO de JuanPZ28 (usado con su
autorización; solo nombres, descripciones y precios), repartido entre la pizzería y la trattoria.

"""Genera una hoja de contacto (cuadrícula con el slug) de las fotos de la carta. Requiere Pillow.

Uso:  python tools/hoja_contacto.py docs/fotos_antes.png [carpeta]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
salida = Path(sys.argv[1])
carpeta = Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "app" / "presentacion" / "static" / "img" / "platos"
archivos = sorted(p for p in carpeta.glob("*.jpg") if "@" not in p.stem)
columnas, w, h = 5, 360, 225
filas = -(-len(archivos) // columnas)
hoja = Image.new("RGB", (columnas * w, filas * (h + 24)), (20, 20, 20))
dib = ImageDraw.Draw(hoja)
for i, ruta in enumerate(archivos):
    x, y = (i % columnas) * w, (i // columnas) * (h + 24)
    hoja.paste(Image.open(ruta).convert("RGB").resize((w - 4, h)), (x + 2, y))
    dib.text((x + 6, y + h + 6), ruta.stem, fill=(240, 220, 160))
hoja.save(salida)
print(f"{len(archivos)} fotos -> {salida}")

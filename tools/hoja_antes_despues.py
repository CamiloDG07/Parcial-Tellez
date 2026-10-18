"""Hoja de contactos por restaurante (después) y pares antes → después de las fotos reemplazadas. Requiere Pillow.

Uso:  python tools/hoja_antes_despues.py <salida.png> <carpeta_de_fotos_antes>
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
PLATOS = RAIZ / "app" / "presentacion" / "static" / "img" / "platos"
salida, antes = Path(sys.argv[1]), Path(sys.argv[2])
cred_antes = json.loads((antes / "CREDITOS.json").read_text(encoding="utf-8"))
cred_ahora = json.loads((PLATOS / "CREDITOS.json").read_text(encoding="utf-8"))
W, H, COLS, ETQ = 300, 188, 6, 18
cartas = {int(a.stem): json.loads(a.read_text(encoding="utf-8")) for a in sorted((RAIZ / "cartas_demo").glob("*.json"))}
reemplazadas = [s for s in cred_ahora if s in cred_antes and cred_antes[s]["archivo"] != cred_ahora[s]["archivo"]]
filas = sum(-(-sum(len(c["productos"]) for c in d["categorias"]) // COLS) for d in cartas.values())
alto = 5 * 30 + filas * (H + ETQ) + (-(-len(reemplazadas) // 3)) * (H + ETQ) + 60
hoja = Image.new("RGB", (COLS * W, alto), (18, 18, 18))
dib = ImageDraw.Draw(hoja)
y = 6


def pegar(ruta, x, y, texto, color=(240, 220, 160)):
    hoja.paste(Image.open(ruta).convert("RGB").resize((W - 4, H)), (x + 2, y))
    dib.text((x + 6, y + H + 3), texto, fill=color)


for rid, d in cartas.items():
    dib.text((6, y + 6), f"Restaurante {rid}: {d['restaurante']}", fill=(255, 255, 255)); y += 30
    slugs = [p["slug_foto"] for c in d["categorias"] for p in c["productos"]]
    for i, s in enumerate(slugs):
        pegar(PLATOS / f"{s}.jpg", (i % COLS) * W, y + (i // COLS) * (H + ETQ), s + ("  [reemplazada]" if s in reemplazadas else ""))
    y += -(-len(slugs) // COLS) * (H + ETQ)
dib.text((6, y + 6), "Reemplazadas en las cartas 1 y 5: ANTES (izquierda de cada par) → DESPUÉS", fill=(255, 255, 255)); y += 30
for i, s in enumerate(reemplazadas):
    x, yy = (i % 3) * 2 * W // 1, y + (i // 3) * (H + ETQ)
    x = (i % 3) * 2 * W
    pegar(antes / f"{s}.jpg", x, yy, f"antes: {s}", (255, 150, 150))
    pegar(PLATOS / f"{s}.jpg", x + W, yy, "después", (150, 255, 150))
hoja.crop((0, 0, COLS * W, y + (-(-len(reemplazadas) // 3)) * (H + ETQ) + 10)).save(salida)
print(f"{len(reemplazadas)} reemplazadas -> {salida}")

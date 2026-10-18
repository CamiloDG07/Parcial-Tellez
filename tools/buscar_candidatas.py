"""Busca candidatas en Wikimedia Commons para platos concretos y arma una hoja de contacto por plato para revisarlas a ojo.

Uso:  python tools/buscar_candidatas.py <carpeta_salida> slug1 slug2 "slug=consulta extra" ...
Solo acepta JPEG >= 1600 px de ancho con licencia CC0, dominio público, CC BY o CC BY-SA (consultada a la API;
NC/ND quedan descartadas). Marca con ★ las que están en las categorías Featured/Quality/Valued.
Requiere Pillow (solo herramientas).
"""
from __future__ import annotations

import io
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from descargar_fotos import API, EXCLUIR, LICENCIAS_OK, UA, texto   # noqa: E402

CONSULTAS = {
    "tiramisu": ["tiramisu dessert", "tiramisù slice plate", "tiramisu cup"],
    "risotto-ai-funghi": ["risotto ai funghi", "mushroom risotto plate", "risotto porcini"],
    "fettuccine-alfredo": ["fettuccine alfredo", "fettuccine al burro", "alfredo pasta plate"],
    "cannoli-siciliani": ["cannoli siciliani", "cannoli ricotta", "sicilian cannoli plate"],
    "torta-della-nonna": ["torta della nonna", "torta della nonna slice", "torta della nonna pinoli"],
    "torta-caprese": ["torta caprese", "torta caprese chocolate almond cake", "caprese cake slice"],
    "affogato-al-caffe": ["affogato", "affogato al caffè", "affogato espresso gelato"],
    "antipasto-misto": ["antipasto misto", "italian antipasto platter", "antipasti plate"],
    "pizza-quattro-formaggi": ["pizza quattro formaggi", "four cheese pizza", "pizza ai quattro formaggi"],
    "pollo-alla-parmigiana": ["chicken parmigiana", "pollo alla parmigiana", "chicken parmesan plate"],
    "gnocchi-al-pesto": ["gnocchi al pesto", "gnocchi pesto plate", "potato gnocchi pesto"],
}
BUENA_CATEGORIA = re.compile(r"Featured pictures|Quality images|Valued image", re.I)


def consultar(**params) -> dict:
    url = API + "?" + urllib.parse.urlencode({"action": "query", "format": "json", **params})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return json.load(r)


def candidatas(consulta: str) -> list[dict]:
    d = consultar(generator="search", gsrsearch=f"{consulta} filetype:bitmap", gsrnamespace=6, gsrlimit=30,
                  prop="imageinfo|categories", iiprop="url|extmetadata|size|mime", iiurlwidth=800, cllimit="max")
    salida = []
    for p in d.get("query", {}).get("pages", {}).values():
        ii = p["imageinfo"][0]
        lic = texto(ii["extmetadata"].get("LicenseShortName", {}).get("value", ""))
        if ii["mime"] != "image/jpeg" or ii["width"] < 1600 or not LICENCIAS_OK.match(lic) or EXCLUIR.search(p["title"]):
            continue
        cats = [c["title"] for c in p.get("categories", [])]
        salida.append({"title": p["title"], "licencia": lic, "ancho": ii["width"], "alto": ii["height"],
                       "thumb": ii["thumburl"], "pagina": ii["descriptionurl"],
                       "autor": texto(ii["extmetadata"].get("Artist", {}).get("value", "")) or "desconocido",
                       "buena": bool(any(BUENA_CATEGORIA.search(c) for c in cats)), "indice": p.get("index", 99)})
    return salida


def main() -> None:
    carpeta = Path(sys.argv[1]); carpeta.mkdir(parents=True, exist_ok=True)
    for arg in sys.argv[2:]:
        slug, _, extra = arg.partition("=")
        nombre = slug + ("__" + re.sub(r"\W+", "_", extra) if extra else "")
        vistas: dict[str, dict] = {}
        for q in ([extra] if extra else CONSULTAS.get(slug, [slug.replace("-", " ")])):
            for c in candidatas(q):
                vistas.setdefault(c["title"], c)
        lista = sorted(vistas.values(), key=lambda c: (not c["buena"], c["indice"]))[:12]
        (carpeta / f"{nombre}.json").write_text(json.dumps(lista, ensure_ascii=False, indent=1), encoding="utf-8")
        if not lista:
            print(slug, "SIN candidatas"); continue
        w, h = 400, 260
        hoja = Image.new("RGB", (4 * w, 3 * (h + 40)), (20, 20, 20)); dib = ImageDraw.Draw(hoja)
        for i, c in enumerate(lista):
            try:
                with urllib.request.urlopen(urllib.request.Request(c["thumb"], headers=UA), timeout=60) as r:
                    im = Image.open(io.BytesIO(r.read())).convert("RGB")
            except Exception as e:      # noqa: BLE001
                print("fallo descarga", c["title"], e); continue
            im.thumbnail((w - 4, h)); x, y = (i % 4) * w, (i // 4) * (h + 40)
            hoja.paste(im, (x + 2, y))
            dib.text((x + 4, y + h + 2), f"#{i} {'*' if c['buena'] else ''}{c['ancho']}px {c['licencia']}", fill=(255, 230, 150))
            dib.text((x + 4, y + h + 16), c["title"][5:48], fill=(200, 200, 200))
        hoja.save(carpeta / f"{nombre}.png")
        print(f"{slug}: {len(lista)} candidatas ({sum(c['buena'] for c in lista)} con categoría de calidad)")


if __name__ == "__main__":
    main()

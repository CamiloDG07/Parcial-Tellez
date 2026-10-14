"""Descarga fotos de la carta demo desde Wikimedia Commons (licencias libres) y guarda los créditos.

Uso:  python tools/descargar_fotos.py            (usa tools/fotos_elegidas.json si existe)
Requiere Pillow (solo para esta herramienta; la app no lo necesita).
Cada foto se recorta a 16:10, se reduce a 800×500 y se comprime a JPG (< 250 KB).
Los créditos (autor, licencia, página de origen) quedan en app/presentacion/static/img/platos/CREDITOS.json.
"""
from __future__ import annotations

import io
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "app" / "presentacion" / "static" / "img" / "platos"
ELEGIDAS = Path(__file__).with_name("fotos_elegidas.json")     # slug -> título del archivo en Commons (opcional)
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "MidnightDinerStudentProject/1.0 (proyecto academico; appleoxx99@gmail.com)"}
LICENCIAS_OK = re.compile(r"^(CC0|Public domain|PD|CC BY(-SA)?( [0-9.]+)?)$", re.I)
EXCLUIR = re.compile(r"menu|logo|map|poster|stamp|sign|restaurant|shop|cartoon|diagram|recipe book", re.I)

CONSULTAS = {
    "bruschetta-clasica": "bruschetta", "ensalada-caprese": "insalata caprese", "carpaccio-di-manzo": "beef carpaccio",
    "calamares-fritti": "fried calamari", "arancini-di-risotto": "arancini", "focaccia-al-rosmarino": "focaccia rosemary",
    "zuppa-minestrone": "minestrone soup", "burrata-con-tomates-cherry": "burrata", "antipasto-misto": "antipasto platter",
    "pizza-margherita": "pizza margherita", "pizza-pepperoni": "pepperoni pizza", "pizza-quattro-formaggi": "quattro formaggi pizza",
    "spaghetti-alla-carbonara": "spaghetti carbonara", "fettuccine-alfredo": "fettuccine alfredo",
    "lasagna-alla-bolognese": "lasagne bolognese", "gnocchi-al-pesto": "gnocchi pesto", "risotto-ai-funghi": "mushroom risotto",
    "pollo-alla-parmigiana": "chicken parmigiana", "tiramisu": "tiramisu", "panna-cotta": "panna cotta",
    "cannoli-siciliani": "cannoli", "affogato-al-caffe": "affogato", "torta-caprese": "torta caprese",
    "semifreddo-al-limone": "semifreddo", "zeppole": "zeppole", "torta-della-nonna": "torta della nonna",
}


def consultar(**params) -> dict:
    url = API + "?" + urllib.parse.urlencode({"action": "query", "format": "json", **params})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def texto(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def info_por_titulo(titulo: str) -> dict | None:
    d = consultar(titles=titulo, prop="imageinfo", iiprop="url|extmetadata|size|mime", iiurlwidth=900)
    return next(iter(d["query"]["pages"].values())).get("imageinfo", [None])[0] | {"title": titulo} if d["query"]["pages"] else None


def candidatos(consulta: str) -> list[dict]:
    d = consultar(generator="search", gsrsearch=f"{consulta} filetype:bitmap", gsrnamespace=6, gsrlimit=15,
                  prop="imageinfo", iiprop="url|extmetadata|size|mime", iiurlwidth=900)
    paginas = sorted(d.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    salida = []
    for p in paginas:
        ii = p["imageinfo"][0]
        licencia = texto(ii["extmetadata"].get("LicenseShortName", {}).get("value", ""))
        if (ii["mime"] == "image/jpeg" and ii["width"] >= 700 and ii["height"] >= 450 and LICENCIAS_OK.match(licencia)
                and not EXCLUIR.search(p["title"])):
            salida.append({**ii, "title": p["title"], "licencia": licencia})
    return salida


def preparar(ii: dict) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(ii["thumburl"], headers=UA), timeout=60) as r:
        imagen = Image.open(io.BytesIO(r.read())).convert("RGB")
    ancho, alto = imagen.size
    objetivo = 16 / 10
    if ancho / alto > objetivo:                 # demasiado ancha: recorta a los lados
        nuevo = int(alto * objetivo)
        imagen = imagen.crop(((ancho - nuevo) // 2, 0, (ancho - nuevo) // 2 + nuevo, alto))
    else:                                       # demasiado alta: recorta arriba/abajo
        nuevo = int(ancho / objetivo)
        imagen = imagen.crop((0, (alto - nuevo) // 3, ancho, (alto - nuevo) // 3 + nuevo))
    imagen = imagen.resize((800, 500), Image.LANCZOS)
    for calidad in (82, 74, 66, 58, 50):
        buffer = io.BytesIO()
        imagen.save(buffer, "JPEG", quality=calidad, optimize=True, progressive=True)
        if buffer.tell() < 250 * 1024:
            return buffer.getvalue()
    raise RuntimeError("No se logró comprimir por debajo de 250 KB")


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    elegidas = json.loads(ELEGIDAS.read_text(encoding="utf-8")) if ELEGIDAS.exists() else {}
    creditos, fallos = {}, []
    for slug, consulta in CONSULTAS.items():
        try:
            if slug in elegidas:
                d = consultar(titles=elegidas[slug], prop="imageinfo", iiprop="url|extmetadata|size|mime", iiurlwidth=900)
                p = next(iter(d["query"]["pages"].values()))
                ii = {**p["imageinfo"][0], "title": p["title"],
                      "licencia": texto(p["imageinfo"][0]["extmetadata"].get("LicenseShortName", {}).get("value", ""))}
            else:
                lista = candidatos(consulta)
                if not lista:
                    fallos.append(slug)
                    continue
                ii = lista[0]
            (DESTINO / f"{slug}.jpg").write_bytes(preparar(ii))
            meta = ii["extmetadata"]
            creditos[slug] = {"archivo": ii["title"], "autor": texto(meta.get("Artist", {}).get("value", "")) or "desconocido",
                              "licencia": ii["licencia"], "pagina": ii["descriptionurl"]}
            print(f"OK  {slug:30s} <- {ii['title']} [{ii['licencia']}]")
        except Exception as e:                    # noqa: BLE001 - herramienta de línea de comandos
            fallos.append(slug)
            print(f"ERR {slug}: {e}", file=sys.stderr)
    (DESTINO / "CREDITOS.json").write_text(json.dumps(creditos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(creditos)} fotos guardadas; sin foto: {fallos or 'ninguna'}")


if __name__ == "__main__":
    main()

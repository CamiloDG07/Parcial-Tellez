"""Descarga fotos de la carta demo desde Wikimedia Commons (licencias libres) y guarda los créditos.

Uso:  python tools/descargar_fotos.py            (usa tools/fotos_elegidas.json si existe)
Requiere Pillow (solo para esta herramienta; la app no lo necesita).
Cada foto se recorta a 16:10 CENTRANDO EL PLATO (no el centro geométrico), se reduce a 800×500, se le aplica un auto-contraste
y una nitidez suaves y homogéneos y se comprime a JPG (< 250 KB). Además se guarda <slug>@400.jpg (400×250) para srcset.
Los créditos (autor, licencia, página de origen) quedan en app/presentacion/static/img/platos/CREDITOS.json.
"""
from __future__ import annotations

import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "app" / "presentacion" / "static" / "img" / "platos"
CENTROS = Path(__file__).with_name("fotos_centros.json")        # slug -> [x, y] en [0,1]: centro del plato a mano (opcional)
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


def con_reintentos(funcion, intentos: int = 4):
    """Las conexiones a Commons fallan a veces por tiempo de espera: se reintenta con pausa creciente."""
    for n in range(intentos):
        try:
            return funcion()
        except OSError:
            if n == intentos - 1:
                raise
            time.sleep(3 * (n + 1))


def consultar(**params) -> dict:
    url = API + "?" + urllib.parse.urlencode({"action": "query", "format": "json", **params})
    return con_reintentos(lambda: json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40)))


def texto(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def info_por_titulo(titulo: str) -> dict | None:
    d = consultar(titles=titulo, prop="imageinfo", iiprop="url|extmetadata|size|mime|user", iiurlwidth=1600)
    return next(iter(d["query"]["pages"].values())).get("imageinfo", [None])[0] | {"title": titulo} if d["query"]["pages"] else None


def candidatos(consulta: str) -> list[dict]:
    d = consultar(generator="search", gsrsearch=f"{consulta} filetype:bitmap", gsrnamespace=6, gsrlimit=15,
                  prop="imageinfo", iiprop="url|extmetadata|size|mime|user", iiurlwidth=1600)
    paginas = sorted(d.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    salida = []
    for p in paginas:
        ii = p["imageinfo"][0]
        licencia = texto(ii["extmetadata"].get("LicenseShortName", {}).get("value", ""))
        if (ii["mime"] == "image/jpeg" and ii["width"] >= 700 and ii["height"] >= 450 and LICENCIAS_OK.match(licencia)
                and not EXCLUIR.search(p["title"])):
            salida.append({**ii, "title": p["title"], "licencia": licencia})
    return salida


def centro_del_plato(imagen: Image.Image) -> tuple[float, float]:
    """Centro de interés (x, y) en [0,1]: centroide de una mapa de saliencia = saturación × luminosidad + bordes.
    Solo Pillow. Sirve para centrar el plato aunque no esté en el centro geométrico de la foto."""
    pequena = imagen.copy()
    pequena.thumbnail((64, 64))
    hsv, bordes = pequena.convert("HSV"), pequena.convert("L").filter(ImageFilter.FIND_EDGES)
    ancho, alto = pequena.size
    total = sx = sy = 0.0
    for y in range(alto):
        for x in range(ancho):
            _, sat, val = hsv.getpixel((x, y))
            peso = ((sat / 255) * (val / 255) + bordes.getpixel((x, y)) / 255) ** 2
            total, sx, sy = total + peso, sx + peso * (x + 0.5), sy + peso * (y + 0.5)
    return (sx / total / ancho, sy / total / alto) if total else (0.5, 0.5)


def recortar_16_10(imagen: Image.Image, centro: list[float] | None = None) -> Image.Image:
    """Recorta a 16:10 con la ventana centrada en el plato (limitada a los bordes de la foto).
    `centro` opcional: [x, y], [x, y, zoom] o [x, y, zoom, gamma] a mano (zoom > 1 acerca el recorte)."""
    ancho, alto = imagen.size
    cx, cy = (centro[0], centro[1]) if centro else centro_del_plato(imagen)
    zoom = centro[2] if centro and len(centro) > 2 else 1.0
    ancho_v = min(ancho, alto * 16 / 10) / zoom                 # tamaño de la ventana 16:10
    alto_v = ancho_v * 10 / 16
    x0 = min(max(cx * ancho - ancho_v / 2, 0), ancho - ancho_v)
    y0 = min(max(cy * alto - alto_v / 2, 0), alto - alto_v)
    return imagen.crop((int(x0), int(y0), int(x0 + ancho_v), int(y0 + alto_v)))


def homogeneizar(imagen: Image.Image, gamma: float = 1.0) -> Image.Image:
    """Auto-contraste suave (mezcla 35 % con el original), calidez leve y nitidez suave, iguales para todas las fotos."""
    mejorada = Image.blend(imagen, ImageOps.autocontrast(imagen, cutoff=1), 0.35)
    if gamma != 1.0:      # aclarar (gamma < 1) fotos oscuras: ajuste manual por plato en fotos_centros.json (4.º valor)
        mejorada = mejorada.point(lambda v: int(255 * (v / 255) ** gamma))
    r, g, b = mejorada.split()
    mejorada = Image.merge("RGB", (r.point(lambda v: min(255, int(v * 1.02))), g, b.point(lambda v: int(v * 0.98))))
    return mejorada.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=3))


def comprimir(imagen: Image.Image, limite_kb: int) -> bytes:
    for calidad in (84, 78, 72, 66, 58, 50):
        buffer = io.BytesIO()
        imagen.save(buffer, "JPEG", quality=calidad, optimize=True, progressive=True)
        if buffer.tell() < limite_kb * 1024:
            return buffer.getvalue()
    raise RuntimeError(f"No se logró comprimir por debajo de {limite_kb} KB")


def preparar(ii: dict, centro: list[float] | None = None) -> tuple[bytes, bytes]:
    """Devuelve (800×500, 400×250) ya procesadas."""
    datos = con_reintentos(lambda: urllib.request.urlopen(urllib.request.Request(ii["thumburl"], headers=UA), timeout=90).read())
    imagen = Image.open(io.BytesIO(datos)).convert("RGB")
    gamma = centro[3] if centro and len(centro) > 3 else 1.0
    grande = homogeneizar(recortar_16_10(imagen, centro).resize((800, 500), Image.LANCZOS), gamma)
    chica = grande.resize((400, 250), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=0.8, percent=40, threshold=3))
    return comprimir(grande, 250), comprimir(chica, 100)


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    elegidas = json.loads(ELEGIDAS.read_text(encoding="utf-8")) if ELEGIDAS.exists() else {}
    centros = json.loads(CENTROS.read_text(encoding="utf-8")) if CENTROS.exists() else {}
    archivo_creditos = DESTINO / "CREDITOS.json"
    previos = json.loads(archivo_creditos.read_text(encoding="utf-8")) if archivo_creditos.exists() else {}
    solo = set(sys.argv[1:])                      # opcional: regenerar solo estos slugs
    creditos, fallos = {k: v for k, v in previos.items() if solo and k not in solo}, []
    for slug in list(dict.fromkeys([*CONSULTAS, *elegidas])):
        consulta = CONSULTAS.get(slug, slug.replace("-", " "))
        if solo and slug not in solo:
            continue
        try:
            if slug in elegidas:
                d = consultar(titles=elegidas[slug], prop="imageinfo", iiprop="url|extmetadata|size|mime|user", iiurlwidth=1600)
                p = next(iter(d["query"]["pages"].values()))
                ii = {**p["imageinfo"][0], "title": p["title"],
                      "licencia": texto(p["imageinfo"][0]["extmetadata"].get("LicenseShortName", {}).get("value", ""))}
            else:
                lista = candidatos(consulta)
                if not lista:
                    fallos.append(slug)
                    continue
                ii = lista[0]
            grande, chica = preparar(ii, centros.get(slug))
            (DESTINO / f"{slug}.jpg").write_bytes(grande)
            (DESTINO / f"{slug}@400.jpg").write_bytes(chica)
            meta = ii["extmetadata"]
            creditos[slug] = {"archivo": ii["title"], "autor": texto(meta.get("Artist", {}).get("value", "")) or f"{ii.get('user', 'desconocido')} (usuario de Commons)",
                              "licencia": ii["licencia"], "pagina": ii["descriptionurl"]}
            print(f"OK  {slug:30s} <- {ii['title']} [{ii['licencia']}]")
        except Exception as e:                    # noqa: BLE001 - herramienta de línea de comandos
            fallos.append(slug)
            print(f"ERR {slug}: {e}", file=sys.stderr)
    (DESTINO / "CREDITOS.json").write_text(json.dumps(creditos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(creditos)} fotos guardadas; sin foto: {fallos or 'ninguna'}")


if __name__ == "__main__":
    main()

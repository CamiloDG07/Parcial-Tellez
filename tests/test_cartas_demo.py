"""Cada restaurante del seed tiene su propia carta, con fotos propias y créditos completos."""
import json
import re

from app import config
from app.datos import seed
from app.datos.dao import ProductoDAO, RestauranteDAO


def _cartas():
    archivos = sorted(seed.CARTAS_DIR.glob("*.json"))
    assert archivos, "no hay cartas en cartas_demo/"
    return [(int(a.stem), json.loads(a.read_text(encoding="utf-8"))) for a in archivos]


def test_las_cartas_tienen_formato_valido():
    for rid, carta in _cartas():
        assert carta["restaurante_id"] == rid and carta["moneda"].startswith("COP")
        nombres = []
        for cat in carta["categorias"]:
            assert cat["nombre"] and isinstance(cat["orden"], int) and cat["productos"]
            for p in cat["productos"]:
                assert isinstance(p["precio_cop"], int) and p["precio_cop"] > 0, p["nombre"]
                assert p["nombre"].strip() and len(p["descripcion"]) >= 15, p["nombre"]
                assert re.fullmatch(r"[a-z0-9-]+", p["slug_foto"]), p["slug_foto"]
                nombres.append(p["nombre"])
        assert len(nombres) == len(set(nombres)), f"nombres repetidos en la carta {rid}"


def test_ninguna_foto_se_repite_entre_restaurantes():
    vistos: dict[str, int] = {}
    for rid, carta in _cartas():
        for cat in carta["categorias"]:
            for p in cat["productos"]:
                assert p["slug_foto"] not in vistos, f"{p['slug_foto']} está en las cartas {vistos[p['slug_foto']]} y {rid}"
                vistos[p["slug_foto"]] = rid


def test_cada_foto_de_las_cartas_existe_con_su_version_pequena_y_credito():
    creditos = json.loads((config.PLATOS_DIR / "CREDITOS.json").read_text(encoding="utf-8"))
    for rid, carta in _cartas():
        for cat in carta["categorias"]:
            for p in cat["productos"]:
                s = p["slug_foto"]
                grande, pequena = config.PLATOS_DIR / f"{s}.jpg", config.PLATOS_DIR / f"{s}@400.jpg"
                assert grande.is_file() and grande.stat().st_size < 250 * 1024, s
                assert pequena.is_file(), s
                assert creditos[s]["autor"] and creditos[s]["licencia"], s


def test_el_seed_carga_la_carta_de_cada_restaurante_y_no_las_mezcla(bd):
    cartas = dict(_cartas())
    dao = ProductoDAO()
    for r in RestauranteDAO().listar():
        esperados = {p["nombre"] for c in cartas.get(r.id, {"categorias": []})["categorias"] for p in c["productos"]}
        assert {p.nombre for p in dao.listar_por_restaurante(r.id)} == esperados, r.nombre


def test_cada_restaurante_del_seed_tiene_carta_con_al_menos_10_platos_y_3_categorias():
    """Cada restaurante sembrado (1 a 5) tiene su carta, con ≥ 10 platos y ≥ 3 categorías."""
    ids_con_carta = {rid for rid, _ in _cartas()}
    for rid, carta in _cartas():
        platos = [p for cat in carta["categorias"] for p in cat["productos"]]
        assert len(platos) >= 10, f"la carta {rid} tiene solo {len(platos)} platos"
        assert len(carta["categorias"]) >= 3, f"la carta {rid} tiene solo {len(carta['categorias'])} categorías"
    ids_restaurantes = set(range(1, len(seed.RESTAURANTES) + 1))      # el seed les asigna id 1..N en orden
    assert ids_restaurantes <= ids_con_carta, f"restaurantes sin carta: {sorted(ids_restaurantes - ids_con_carta)}"

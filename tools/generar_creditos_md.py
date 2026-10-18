"""Regenera CREDITOS.md (y opcionalmente imprime la tabla Markdown) a partir de CREDITOS.json. Solo biblioteca estándar.

Uso:  python tools/generar_creditos_md.py
"""
import json
from pathlib import Path

PLATOS = Path(__file__).resolve().parent.parent / "app" / "presentacion" / "static" / "img" / "platos"
cred = json.loads((PLATOS / "CREDITOS.json").read_text(encoding="utf-8"))
filas = ["| Plato (archivo) | Foto en Wikimedia Commons | Autor | Licencia |", "|---|---|---|---|"]
for slug, c in cred.items():
    filas.append(f"| `{slug}.jpg` | [{c['archivo'].replace('File:', '')}]({c['pagina']}) | {c['autor'].replace('|', '/')} | {c['licencia']} |")
(PLATOS / "CREDITOS.md").write_text("\n".join(filas) + "\n", encoding="utf-8")
print(f"{len(cred)} créditos -> CREDITOS.md")

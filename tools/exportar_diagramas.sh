#!/usr/bin/env bash
# Exporta docs/*.mmd a docs/diagramas/*.png con mermaid-cli y el Chromium de Playwright.
# Requisitos: (cd tools/mmdc && PUPPETEER_SKIP_DOWNLOAD=1 npm install @mermaid-js/mermaid-cli)
#             python -m playwright install chromium
# Ajusta executablePath en tools/mmdc/puppeteer-config.json a tu instalación de Chromium.
set -e
mkdir -p docs/diagramas
for f in modelo_relacional diagrama_dao diagrama_control_patrones arquitectura_tres_capas; do
  tools/mmdc/node_modules/.bin/mmdc -p tools/mmdc/puppeteer-config.json -i "docs/$f.mmd" -o "docs/diagramas/$f.png" -b "#ffffff" -s 2
done

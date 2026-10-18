"""Recorrido E2E con Playwright: flujos de cliente y administrador, capturas, HTML/consola, movimiento reducido y FPS.

Uso (con el servidor corriendo sobre una base recién sembrada):
    python tools/e2e_capturas.py http://localhost:8765 docs/capturas
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = sys.argv[1].rstrip("/")
SALIDA = Path(sys.argv[2])
if SALIDA.exists():
    shutil.rmtree(SALIDA)
SALIDA.mkdir(parents=True)

VOID = {"meta", "link", "input", "br", "hr", "img", "source", "path", "circle", "rect", "ellipse", "stop", "use", "line"}
problemas: list[str] = []
consola: list[tuple] = []
informe: list[str] = []


class Balance(HTMLParser):
    """Detecta etiquetas sin cerrar o cierres inesperados en el DOM serializado."""

    def __init__(self):
        super().__init__()
        self.pila, self.errores = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.pila.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if self.pila and self.pila[-1] == tag:
            self.pila.pop()
        else:
            self.errores.append(f"</{tag}> inesperado (abiertas: {self.pila[-3:]})")


def revisar_html(page, nombre):
    """Etiquetas balanceadas y sin atributos pegados tipo  action="/x"alidate  en el HTML servido."""
    crudo = page.request.get(page.url).text() if page.url.startswith("http") else page.content()
    b = Balance()
    b.feed(crudo)
    if b.errores or b.pila:
        problemas.append(f"{nombre}: {b.errores[:3]} sin cerrar={b.pila}")
    pegados = re.findall(r'\s[\w:-]+="[^"]*"[A-Za-z]', crudo)
    if pegados:
        problemas.append(f"{nombre}: atributos pegados {pegados[:3]}")


def captura(page, nombre, revisar=True):
    page.add_style_tag(content=".barra{position:static!important}.revela{opacity:1!important;transform:none!important}"
                              "main{animation:none!important}")
    for ancho, alto, sufijo in ((1440, 900, "1440"), (375, 812, "375")):
        page.set_viewport_size({"width": ancho, "height": alto})
        page.wait_for_timeout(350)
        page.screenshot(path=str(SALIDA / f"{nombre}_{sufijo}.png"), full_page=True)
        if page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"):
            problemas.append(f"{nombre} @{ancho}px: scroll horizontal")
    page.set_viewport_size({"width": 1440, "height": 900})
    if revisar:
        revisar_html(page, nombre)


def login(page, email, pw):
    page.goto(BASE + "/login")
    page.fill("#email", email)
    page.fill("#password", pw)
    page.click("button:has-text('ENTRAR')")
    page.wait_for_load_state("networkidle")


def siguiente(page):
    page.click("#paso-sig")
    page.wait_for_timeout(380)


with sync_playwright() as p:
    exe = os.environ.get("CHROMIUM_EXE")          # opcional: ruta de un Chromium ya instalado (p. ej. en un contenedor)
    nav = p.chromium.launch(executable_path=exe, args=["--no-sandbox"]) if exe else p.chromium.launch()
    ctx_c = nav.new_context(viewport={"width": 1440, "height": 900})
    ctx_a = nav.new_context(viewport={"width": 1440, "height": 900})
    cli, adm = ctx_c.new_page(), ctx_a.new_page()
    for pg, quien in ((cli, "cliente"), (adm, "admin")):
        pg.on("console", lambda m, q=quien: consola.append((q, m.type, m.text, m.location.get("url", ""))) if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e, q=quien: consola.append((q, "pageerror", str(e), "")))

    # ---------- público ----------
    cli.goto(BASE + "/login"); captura(cli, "01_login_cliente")
    cli.goto(BASE + "/"); captura(cli, "02_inicio")
    cli.goto(BASE + "/restaurantes"); captura(cli, "03_restaurantes")
    cli.goto(BASE + "/carta?restaurante_id=1"); captura(cli, "04_carta_publica")
    cli.goto(BASE + "/login"); cli.fill("#email", "cliente@demo.com"); cli.fill("#password", "incorrecta")
    cli.click("button:has-text('ENTRAR')"); cli.wait_for_load_state()
    assert "incorrectos" in cli.content(); captura(cli, "05_error_login")

    # ---------- registro ----------
    cli.goto(BASE + "/registro"); captura(cli, "06_registro")
    cli.fill("#nombre", "Eva Prueba"); cli.fill("#email", "eva@demo.com")
    cli.fill("#password", "Clave12345"); cli.fill("#confirmacion", "Otra123456")
    cli.click("button:has-text('REGISTRARME')"); cli.wait_for_load_state()
    assert "no coincide" in cli.content(); captura(cli, "07_error_registro")
    cli.fill("#password", "Clave12345"); cli.fill("#confirmacion", "Clave12345")
    cli.click("button:has-text('REGISTRARME')"); cli.wait_for_load_state()
    assert cli.url.endswith("/restaurantes"), cli.url

    # ---------- carta y pre-pedido (con animación "vuela al carrito") ----------
    cli.goto(BASE + "/carta?restaurante_id=1")
    cli.click(".pestana:has-text('POSTRE')")
    assert cli.locator(".plato:visible").count() == 3          # Slice Palace tiene 3 postres
    cli.fill("#buscar-plato", "cannoli")
    assert cli.locator(".plato:visible").count() == 1
    cli.fill("#cant-" + cli.locator(".plato:visible [data-agregar]").first.get_attribute("data-agregar"), "8")
    cli.click(".plato:visible [data-agregar]")
    expect(cli.locator("#insignia-carrito")).to_have_text("8")
    informe.append("carta: pestañas, búsqueda y agregar al pre-pedido OK")
    cli.fill("#buscar-plato", ""); cli.click(".pestana:has-text('ENTRADA')")
    cli.click(".plato:visible >> nth=0 >> [data-agregar]")
    expect(cli.locator("#insignia-carrito")).to_have_text("9")
    cli.click("#abrir-carrito"); cli.wait_for_timeout(500)
    total_cajon = cli.inner_text("#carrito-total")
    captura(cli, "08_carta_y_cajon_pre_pedido", revisar=False)
    cli.keyboard.press("Escape")
    cli.reload(); expect(cli.locator("#insignia-carrito")).to_have_text("9")

    # ---------- asistente de reserva (pasos) ----------
    cli.goto(BASE + "/reservar?restaurante_id=1")
    cli.wait_for_selector(".chip:not([disabled])", state="attached")
    assert cli.locator(".paso:visible").count() == 1, "solo debe verse un paso"
    cli.fill("#personas", "3"); cli.wait_for_timeout(600)
    captura(cli, "09_reservar_paso1_fecha", revisar=False)
    siguiente(cli)
    cli.click("#paso-sig"); cli.wait_for_timeout(200)                       # sin hora: no avanza
    assert cli.inner_text("#err-hora"), "debió exigir una hora"
    captura(cli, "10_error_validacion_hora", revisar=False)
    cli.click(".chip:not([disabled]) >> nth=5"); siguiente(cli)
    cli.uncheck("#auto-mesa")
    assert cli.locator(".zona").count() >= 2, "el plano debe agrupar las mesas por zonas"
    cli.click(".mesa-libre:not([disabled]) >> nth=0")
    assert cli.locator(".mesa-sel").count() == 1
    captura(cli, "11_reservar_mesa_elegida", revisar=False)
    siguiente(cli)
    assert "TOTAL ESTIMADO" in cli.inner_text("#paso-pedido") and total_cajon in cli.inner_text("#paso-pedido")
    captura(cli, "12_reservar_paso_pre_pedido", revisar=False)
    siguiente(cli)
    cli.fill("#notas", "Cumpleaños, una vela por favor")
    # total a pagar calculado por el servidor con la cadena de decoradores (Decorator)
    assert cli.inner_text("#cobro-total") == "$157.464", cli.inner_text("#cobro-total")      # 162.000 -10 % +8 %
    assert "Descuento por pedido grande" in cli.inner_text("#cobro")
    captura(cli, "12b_reservar_paso_confirmar", revisar=False)
    cli.check("#propina")
    expect(cli.locator("#cobro-total")).to_have_text("$173.210")   # +10 % de propina
    captura(cli, "12c_reservar_confirmar_con_propina", revisar=False)
    hora, mesa = cli.input_value("#campo-hora"), cli.input_value("#campo-mesa")
    fecha = cli.input_value("#fecha")
    cli.click("button:has-text('CONFIRMAR RESERVA')"); cli.wait_for_load_state()
    assert cli.url.endswith("/mis-reservas") and "PENDIENTE" in cli.content()
    assert total_cajon in cli.content()
    assert "Total a pagar estimado: $173.210 (propina incluida)" in cli.content()
    cli.click("summary:has-text('plato')")
    captura(cli, "13_mis_reservas")
    assert cli.locator(".reserva-card").count() == 1 and "MD-" in cli.inner_text(".reserva-codigo")
    # filtros, comprobante imprimible y archivo de calendario (.ics)
    cli.click("a.pestana:has-text('CANCELADAS')"); cli.wait_for_load_state()
    assert cli.locator(".reserva-card").count() == 0
    cli.goto(BASE + "/mis-reservas")
    href_ics = cli.get_attribute("a:has-text('CALENDARIO')", "href")
    ics = cli.request.get(BASE + href_ics)
    assert ics.ok and ics.headers["content-type"].startswith("text/calendar") and "BEGIN:VEVENT" in ics.text()
    cli.click("a:has-text('COMPROBANTE')"); cli.wait_for_load_state()
    assert "no es una factura" in cli.content() and "TOTAL A PAGAR" in cli.content()
    captura(cli, "13b_comprobante")
    cli.goto(BASE + "/mis-reservas")
    informe.append("mis reservas: tarjetas, filtros, comprobante y .ics OK")
    informe.append(f"asistente: 5 pasos recorridos; reserva con pre-pedido {total_cajon} (a pagar $157.464; con propina $173.210)")

    # doble reserva de la misma mesa y hora (POST directo con el token de la sesión)
    token = cli.evaluate("document.querySelector('meta[name=csrf-token]').content")
    r = cli.request.post(BASE + "/reservar", form={"csrf_token": token, "restaurante_id": "1", "fecha": fecha, "hora": hora,
                                                   "personas": "3", "mesa_id": mesa, "notas": ""}, max_redirects=0)
    cli.goto(BASE + r.headers["location"])
    assert "ya está reservada" in cli.content(), "doble reserva no rechazada"
    captura(cli, "14_doble_reserva_rechazada")
    # fuera de horario
    r = cli.request.post(BASE + "/reservar", form={"csrf_token": token, "restaurante_id": "1", "fecha": fecha, "hora": "03:00",
                                                   "personas": "2", "mesa_id": mesa, "notas": ""}, max_redirects=0)
    cli.goto(BASE + r.headers["location"]); assert "horario" in cli.content()
    informe.append("doble reserva y reserva a las 03:00 rechazadas con mensaje")

    cli.goto(BASE + "/mis-cuentas") if False else None
    cli.goto(BASE + "/admin"); assert "ACCESO DENEGADO" in cli.content()
    captura(cli, "15_cliente_en_admin_403")

    # ---------- administrador ----------
    login(adm, "admin@demo.com", "Admin123!")
    assert adm.url.endswith("/admin")
    assert adm.locator("svg.barras-svg rect.barra-svg").count() == 14
    assert adm.locator("svg.dona-svg").count() == 1 and adm.locator(".calor-celda").count() == 42
    informe.append("panel: barras (14), dona de estados y mapa de calor (7x6) presentes")
    adm.wait_for_timeout(1200)
    captura(adm, "16_admin_panel")
    adm.goto(BASE + "/admin/mesas"); captura(adm, "17_admin_mesas")
    adm.goto(BASE + "/admin/horarios"); captura(adm, "18_admin_horarios")
    adm.goto(BASE + "/admin/carta"); captura(adm, "19_admin_carta")
    adm.goto(BASE + "/admin/reservas"); captura(adm, "20_admin_reservas")
    csv_ = adm.request.get(BASE + "/admin/reservas.csv")
    assert csv_.ok and csv_.headers["content-type"].startswith("text/csv") and csv_.body().startswith(b"\xef\xbb\xbfcodigo;")
    adm.goto(BASE + "/admin/reservas?q=eva")
    assert "Eva Prueba" in adm.content()
    adm.click("button:has-text('CONFIRMAR')"); adm.wait_for_load_state()
    assert "CONFIRMADA" in adm.content()
    captura(adm, "21_admin_reserva_confirmada")
    # modal de confirmación propio al cancelar (sin diálogo nativo)
    adm.click("button:has-text('CANCELAR')"); adm.wait_for_selector("dialog[open]")
    captura(adm, "22_admin_modal_confirmar", revisar=False)
    adm.click("dialog[open] button[value='no']")
    assert "CONFIRMADA" in adm.content()
    cli.goto(BASE + "/mis-reservas"); assert "CONFIRMADA" in cli.content()
    informe.append("admin: confirmó la reserva; modal de cancelación abre y se descarta")
    # el admin no entra a la vista del cliente
    assert adm.goto(BASE + "/reservar").status == 403

    # ---------- movimiento reducido ----------
    ctx_r = nav.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    red = ctx_r.new_page()
    login(red, "cliente@demo.com", "Cliente123!")
    red.goto(BASE + "/carta?restaurante_id=1")
    ocultos = red.evaluate("[...document.querySelectorAll('.plato')].filter(e => getComputedStyle(e).opacity !== '1').length")
    red.goto(BASE + "/reservar?restaurante_id=1"); red.wait_for_selector(".chip:not([disabled])", state="attached")
    anim = red.evaluate("document.getAnimations().filter(a => a.playState === 'running' && a.effect && a.effect.getTiming().iterations === Infinity).length")
    ruido = red.evaluate("getComputedStyle(document.querySelector('.rec i')).animationName")
    informe.append(f"reduced-motion: platos con opacidad<1 = {ocultos}; animaciones infinitas activas = {anim}; punto REC animationName = {ruido}")
    assert ocultos == 0 and anim == 0
    ctx_r.close()

    # ---------- destellos y FPS (modo normal) ----------
    cli.goto(BASE + "/reservar?restaurante_id=1"); cli.wait_for_selector(".chip:not([disabled])", state="attached")
    siguiente(cli); cli.click(".chip:not([disabled]) >> nth=2"); siguiente(cli)
    cli.uncheck("#auto-mesa"); cli.wait_for_timeout(300)
    inf = cli.evaluate("""document.getAnimations().filter(a => a.effect && a.effect.getTiming().iterations === Infinity)
        .map(a => [a.animationName || a.constructor.name, a.effect.getTiming().duration])""")
    mas_rapida = min(d for _, d in inf)
    informe.append(f"animaciones infinitas: {len(inf)}; la más rápida dura {mas_rapida} ms (<= 3 destellos/s exige >= 333 ms)")
    assert mas_rapida >= 333

    cli.goto(BASE + "/carta?restaurante_id=1"); cli.wait_for_timeout(500)
    cli.evaluate("""() => { window.__f = []; let t = performance.now();
        const b = (n) => { window.__f.push(n - t); t = n; if (window.__activo) requestAnimationFrame(b); };
        window.__activo = true; requestAnimationFrame(b); }""")
    for y in range(0, 4500, 300):
        cli.mouse.wheel(0, 300); cli.wait_for_timeout(60)
    cli.evaluate("window.scrollTo(0, 0)"); cli.wait_for_timeout(200)
    cli.click(".plato:visible >> nth=1 >> [data-agregar]"); cli.wait_for_timeout(300)
    cli.click("#abrir-carrito"); cli.wait_for_timeout(700)
    cli.keyboard.press("Escape"); cli.wait_for_timeout(300)
    marcos = cli.evaluate("window.__activo = false; window.__f.slice(1)")
    marcos.sort()
    prom = sum(marcos) / len(marcos)
    informe.append(f"FPS (Chromium headless, render por software, scroll+vuelo+cajón): promedio {1000 / prom:.0f} fps; "
                   f"p95 de duración de fotograma {marcos[int(len(marcos) * .95)]:.1f} ms; {len(marcos)} fotogramas")
    nav.close()

print("\n== HTML / diseño ==")
print("\n".join(problemas) or "sin etiquetas rotas ni scroll horizontal en las páginas revisadas")
esperados = [c for c in consola if re.search(r"\b(400|401|403)\b", c[2])]
print("\n== Consola del navegador ==")
print("errores/avisos inesperados:", [c for c in consola if c not in esperados] or "ninguno")
print(f"(respuestas 4xx provocadas a propósito por las pruebas: {len(esperados)})")
print("\n== Informe ==")
print("\n".join(informe))

"""Configuración central de la aplicación."""
import os
from pathlib import Path

BRAND_NAME = "MIDNIGHT DINER"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("RESERVAS_DB", str(BASE_DIR.parent / "reservas.db"))
SCHEMA_PATH = BASE_DIR / "datos" / "schema.sql"

# Solo para desarrollo: en producción se debe definir SECRET_KEY en el entorno.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-solo-desarrollo-cambiar-en-produccion")

# Poner HTTPS_ONLY=1 cuando la app se sirva por HTTPS: la cookie de sesión pasa a `Secure` y se envía HSTS.
HTTPS_ONLY = os.environ.get("HTTPS_ONLY", "").strip().lower() in ("1", "true", "si", "sí", "yes")

# Poner AUTOSEMBRAR=1 en despliegues de demostración: al arrancar, si la BD está vacía, se siembran los datos demo
# (así el comando de arranque es solo `uvicorn app.main:app ...`). Nunca borra datos existentes.
AUTOSEMBRAR = os.environ.get("AUTOSEMBRAR", "").strip().lower() in ("1", "true", "si", "sí", "yes")

UPLOADS_DIR = BASE_DIR / "presentacion" / "static" / "uploads"    # imágenes subidas por el admin
PLATOS_DIR = BASE_DIR / "presentacion" / "static" / "img" / "platos"  # fotos de la carta demo (slug_foto.jpg)

DURACION_RESERVA_MIN = 120  # duración fija de cada reserva
PASO_FRANJA_MIN = 30         # separación entre franjas ofrecidas
ESTADOS = ("PENDIENTE", "CONFIRMADA", "CANCELADA")
DIAS_SEMANA = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")

# ---- Cobro del pre-pedido (patrón Decorator) -------------------------------------------------
# SUPUESTOS CONFIGURABLES de demostración. No se han verificado contra la normativa vigente ni contra la rúbrica:
# cámbialos aquí si el profesor o el negocio piden otras tasas. Son puntos porcentuales enteros.
TASA_IMPUESTO_CONSUMO_PCT = 8        # supuesto: impuesto al consumo sobre el monto ya descontado
TASA_PROPINA_SUGERIDA_PCT = 10       # supuesto: propina sugerida (voluntaria), sobre el monto con impuesto
DESCUENTO_PEDIDO_GRANDE_PCT = 10     # supuesto de promoción de demostración
DESCUENTO_PEDIDO_GRANDE_MINIMO_COP = 150_000   # el descuento aplica si el subtotal es >= a este valor

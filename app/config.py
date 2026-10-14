"""Configuración central de la aplicación."""
import os
from pathlib import Path

BRAND_NAME = "MIDNIGHT DINER"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("RESERVAS_DB", str(BASE_DIR.parent / "reservas.db"))
SCHEMA_PATH = BASE_DIR / "datos" / "schema.sql"

# Solo para desarrollo: en producción se debe definir SECRET_KEY en el entorno.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-solo-desarrollo-cambiar-en-produccion")

DURACION_RESERVA_MIN = 120   # duración fija de cada reserva
PASO_FRANJA_MIN = 30         # separación entre franjas ofrecidas
ESTADOS = ("PENDIENTE", "CONFIRMADA", "CANCELADA")
DIAS_SEMANA = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")

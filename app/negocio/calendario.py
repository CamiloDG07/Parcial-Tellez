"""Exportación de una reserva como evento de calendario (iCalendar, RFC 5545), solo con la librería estándar."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import config
from app.datos.modelos import Mesa, Reserva, Restaurante


def _escapar(texto: str) -> str:
    """Escapa los caracteres especiales de un valor TEXT (RFC 5545 §3.3.11)."""
    return (texto.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,")
            .replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n"))


def _doblar(linea: str) -> list[str]:
    """Pliega las líneas largas a 75 octetos (la continuación empieza con un espacio)."""
    datos = linea.encode("utf-8")
    if len(datos) <= 75:
        return [linea]
    partes, actual = [], b""
    limite = 75
    for caracter in linea:
        c = caracter.encode("utf-8")
        if len(actual) + len(c) > limite:
            partes.append(actual.decode("utf-8"))
            actual, limite = b"", 74           # la línea de continuación lleva un espacio inicial
        actual += c
    partes.append(actual.decode("utf-8"))
    return [partes[0]] + [" " + p for p in partes[1:]]


def evento_ics(reserva: Reserva, restaurante: Restaurante, mesa: Mesa, ahora: datetime | None = None) -> str:
    """Devuelve el contenido de un archivo .ics con un único evento (la hora es local, sin zona fija)."""
    inicio = datetime.fromisoformat(f"{reserva.fecha}T{reserva.hora}")
    fin = inicio + timedelta(minutes=config.DURACION_RESERVA_MIN)
    sello = (ahora or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    descripcion = (f"Reserva MD-{reserva.id:04d} · {reserva.num_personas} persona(s) · mesa {mesa.numero}"
                   f"{' (' + mesa.ubicacion + ')' if mesa.ubicacion else ''} · estado {reserva.estado}.")
    if reserva.notas:
        descripcion += f" Notas: {reserva.notas}"
    lineas = [
        "BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//{config.BRAND_NAME}//Reservas//ES", "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH", "BEGIN:VEVENT",
        f"UID:reserva-{reserva.id}@midnight-diner.local",
        f"DTSTAMP:{sello}",
        f"DTSTART:{inicio.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND:{fin.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{_escapar('Reserva en ' + restaurante.nombre)}",
        f"LOCATION:{_escapar(restaurante.direccion + ', ' + restaurante.ciudad)}",
        f"DESCRIPTION:{_escapar(descripcion)}",
        "STATUS:" + ("CANCELLED" if reserva.estado == "CANCELADA" else "CONFIRMED" if reserva.estado == "CONFIRMADA" else "TENTATIVE"),
        "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(parte for linea in lineas for parte in _doblar(linea)) + "\r\n"

"""Excepciones de la capa de negocio."""


class ReglaNegocioError(Exception):
    """Se violó una regla de negocio (mensaje apto para mostrar al usuario)."""


class NoAutorizadoError(Exception):
    """El usuario no tiene permiso para la operación."""


class NoEncontradoError(Exception):
    """El recurso solicitado no existe."""

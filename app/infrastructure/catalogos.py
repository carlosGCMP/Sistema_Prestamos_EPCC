"""Datos de referencia necesarios para las claves foráneas de estados y auditoría."""

from sqlalchemy import Connection, insert, select

from app.infrastructure.database import Base
from app.infrastructure.models import LoanState, ReservationState


def cargar_catalogos(conexion: Connection) -> None:
    """Añade los valores faltantes sin borrar ni duplicar los existentes."""
    catalogos: list[tuple[str, str, list[str]]] = [
        ("estado_de_la_reserva", "nombre_estado", [estado.value for estado in ReservationState]),
        ("estado_del_prestamo", "nombre_estado", [estado.value for estado in LoanState]),
        ("estado_de_la_garantia", "nombre_estado", ["RECIBIDA", "DEVUELTA", "EJECUTADA"]),
        ("estado_de_la_incidencia", "nombre_estado", ["ABIERTA", "EN_REVISION", "RESUELTA"]),
        ("estado_de_la_sancion", "nombre_estado", ["ACTIVA", "APELADA", "CUMPLIDA", "ANULADA"]),
        ("tipo_de_evento", "nombre_tipo_evento", ["OPERACION"]),
    ]
    for nombre_tabla, nombre, valores in catalogos:
        tabla = Base.metadata.tables[nombre_tabla]
        existentes = set(conexion.scalars(select(tabla.c[nombre])))
        faltantes = [{nombre: str(valor)} for valor in valores if valor not in existentes]
        if faltantes:
            conexion.execute(insert(tabla), faltantes)

"""Indicadores actuales e importación básica del catálogo desde CSV."""

import csv
import io
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.basic_use_cases import new_category, new_item_type
from app.application.comun import UseCaseError, ahora
from app.infrastructure.models import (
    Category,
    ItemType,
    Loan,
    LoanState,
    Person,
    PhysicalUnit,
    Reservation,
)


def resumen(sesion: Session) -> dict[str, Any]:
    """Cuenta datos actuales de toda la base; no depende de límites del frontend."""

    def total(modelo: Any) -> int:
        return int(sesion.scalar(select(func.count()).select_from(modelo)) or 0)

    def por_estado(modelo: Any) -> dict[str, int]:
        return {
            str(estado): cantidad
            for estado, cantidad in sesion.execute(
                select(modelo.state, func.count()).group_by(modelo.state)
            )
        }

    abiertos = Loan.state.in_((LoanState.ACTIVE, LoanState.OVERDUE))
    vencidos = int(
        sesion.scalar(select(func.count()).select_from(Loan).where(abiertos, Loan.due_at < ahora()))
        or 0
    )
    prestamos = por_estado(Loan)
    # El vencimiento es calculado: no cambia el préstamo ni libera la unidad.
    cantidad_abiertos = sum(
        prestamos.pop(estado.value, 0) for estado in (LoanState.ACTIVE, LoanState.OVERDUE)
    )
    prestamos[LoanState.ACTIVE.value] = cantidad_abiertos - vencidos
    prestamos[LoanState.OVERDUE.value] = vencidos
    return {
        "generado_en": ahora(),
        "personas": total(Person),
        "tipos": total(ItemType),
        "categorias": total(Category),
        "unidades": total(PhysicalUnit),
        "reservas": total(Reservation),
        "prestamos": total(Loan),
        "inventario_por_estado": por_estado(PhysicalUnit),
        "reservas_por_estado": por_estado(Reservation),
        "prestamos_por_estado": prestamos,
    }


def validar_csv(sesion: Session, contenido: str) -> list[dict[str, str]]:
    """Valida todo el archivo antes de crear datos. Máximo 200 categorías."""
    if len(contenido.encode("utf-8")) > 100_000:
        raise UseCaseError(422, "El CSV debe ocupar como máximo 100 KB")
    if "\x00" in contenido:
        raise UseCaseError(422, "El CSV contiene un carácter nulo. Guárdalo como CSV UTF-8")
    lector = csv.DictReader(io.StringIO(contenido.lstrip("\ufeff")), strict=True)
    filas: list[dict[str, str]] = []
    repetidas: set[tuple[str, str]] = set()
    tipos = {tipo.name: tipo for tipo in sesion.scalars(select(ItemType))}
    existentes = set(sesion.execute(select(ItemType.name, Category.name).join(Category)).all())
    try:
        if lector.fieldnames != ["tipo", "categoria", "descripcion"]:
            raise UseCaseError(422, "Cabecera requerida: tipo,categoria,descripcion")
        for numero, fila in enumerate(lector, start=2):
            if len(filas) >= 200:
                raise UseCaseError(422, "Importa como máximo 200 categorías por archivo")
            if None in fila or any(valor is None for valor in fila.values()):
                raise UseCaseError(422, f"Fila {numero}: debe tener exactamente tres columnas")
            tipo = fila["tipo"].strip()
            categoria = fila["categoria"].strip()
            descripcion = fila["descripcion"].strip()
            if not 2 <= len(tipo) <= 100 or not 2 <= len(categoria) <= 100:
                raise UseCaseError(
                    422, f"Fila {numero}: tipo y categoría requieren 2 a 100 caracteres"
                )
            if len(descripcion) > 1000:
                raise UseCaseError(422, f"Fila {numero}: descripción de máximo 1000 caracteres")
            clave = (tipo, categoria)
            if clave in repetidas or clave in existentes:
                raise UseCaseError(409, f"Fila {numero}: la categoría '{categoria}' está duplicada")
            if tipo in tipos and not tipos[tipo].active:
                raise UseCaseError(409, f"Fila {numero}: el tipo '{tipo}' está inactivo")
            repetidas.add(clave)
            filas.append({"tipo": tipo, "categoria": categoria, "descripcion": descripcion})
    except csv.Error as error:
        raise UseCaseError(422, "CSV inválido: revisa comas y comillas") from error
    if not filas:
        raise UseCaseError(422, "El archivo no contiene categorías")
    return filas


def importar_catalogo(sesion: Session, contenido: str, actor: Person) -> dict[str, int]:
    filas = validar_csv(sesion, contenido)
    tipos = {tipo.name: tipo for tipo in sesion.scalars(select(ItemType).with_for_update())}
    creados = 0
    for fila in filas:
        tipo = tipos.get(fila["tipo"])
        if tipo is None:
            tipo = new_item_type(sesion, fila["tipo"], True, actor)
            tipos[tipo.name] = tipo
            creados += 1
        new_category(sesion, fila["categoria"], fila["descripcion"] or None, actor, tipo.id)
    return {"tipos_creados": creados, "categorias_creadas": len(filas)}

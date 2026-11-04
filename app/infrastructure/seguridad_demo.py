"""Comprueba el destino de la demo antes de crear tablas o escribir datos."""

import hashlib
import json

from sqlalchemy import Connection, MetaData, Table, select, text
from sqlalchemy.orm import Session

from app.application.comun import audit
from app.infrastructure.models import AuditEvent

ACCION_DEMO = "DEMO_CARGADA"
VERSION_DEMO = "epcc-demo-v2"
# Son los únicos datos que el arranque normal añade a una instalación vacía.
CATALOGOS_INICIALES = {
    "estado_de_la_reserva",
    "estado_del_prestamo",
    "estado_de_la_garantia",
    "estado_de_la_incidencia",
    "estado_de_la_sancion",
    "tipo_de_evento",
}


class CargaDemoRechazada(Exception):
    """El destino no está vacío o no conserva la demostración original."""


def _tablas(conexion: Connection) -> list[Table]:
    metadatos = MetaData()
    metadatos.reflect(bind=conexion, resolve_fks=False)
    return sorted(metadatos.tables.values(), key=lambda tabla: tabla.name)


def _huella(conexion: Connection, tablas: list[Table], marca_id: int) -> str:
    """Detecta datos añadidos o cambiados sin guardar una copia de ellos en la marca."""
    resumen = hashlib.sha256()
    for tabla in tablas:
        if tabla.name in CATALOGOS_INICIALES:
            continue
        filas = []
        for fila in conexion.execute(select(tabla)).mappings():
            valores = dict(fila)
            if tabla.name == "cuenta":
                # Entrar o salir de la plataforma no altera los datos de la demo.
                valores.pop("ultimo_acceso", None)
                valores.pop("version_sesion", None)
            if tabla.name == "registro_auditoria" and valores.get("id_registro") == marca_id:
                # La huella no puede incluirse a sí misma.
                valores.pop("descripcion", None)
            filas.append(json.dumps(valores, sort_keys=True, default=str, ensure_ascii=False))
        contenido = json.dumps([tabla.name, sorted(filas)], ensure_ascii=False)
        resumen.update(contenido.encode("utf-8"))
    return resumen.hexdigest()


def comprobar_destino(conexion: Connection) -> bool:
    """True: se puede cargar. False: ya está cargada. En otro caso, rechazar."""
    tablas = _tablas(conexion)
    if conexion.dialect.name == "postgresql" and tablas:
        # El cargador debe ejecutarse con la API detenida. También protegemos la
        # comprobación frente a escritores que ya estuvieran usando estas tablas.
        nombres = ", ".join(conexion.dialect.identifier_preparer.format_table(t) for t in tablas)
        conexion.execute(text(f"LOCK TABLE {nombres} IN SHARE ROW EXCLUSIVE MODE"))
    auditoria = next((t for t in tablas if t.name == "registro_auditoria"), None)
    if auditoria is not None and {"accion", "id_entidad", "descripcion", "id_registro"} <= set(
        auditoria.c.keys()
    ):
        marcas = (
            conexion.execute(
                select(auditoria).where(
                    auditoria.c.accion == ACCION_DEMO,
                    auditoria.c.id_entidad == VERSION_DEMO,
                )
            )
            .mappings()
            .all()
        )
        if len(marcas) == 1:
            try:
                contenido = json.loads(marcas[0]["descripcion"])
            except (ValueError, TypeError):
                contenido = None
            if (
                isinstance(contenido, dict)
                and contenido.get("version") == VERSION_DEMO
                and contenido.get("huella") == _huella(conexion, tablas, marcas[0]["id_registro"])
            ):
                return False
            raise CargaDemoRechazada(
                "La demo ya tiene cambios o datos adicionales. No se borró ni se restableció nada. "
                "Usa otra base vacía si necesitas una demostración nueva."
            )
    for tabla in tablas:
        if tabla.name not in CATALOGOS_INICIALES:
            if conexion.execute(select(1).select_from(tabla).limit(1)).first() is not None:
                raise CargaDemoRechazada(
                    "La base contiene datos previos ajenos a una carga demo reconocida. "
                    "No se modificó la base. Configura una base vacía y separada; "
                    "no borres la actual."
                )
    return True


def registrar_carga(sesion: Session) -> None:
    """Marca la carga completa dentro de la misma transacción, sin tablas nuevas."""
    audit(sesion, None, ACCION_DEMO, "Demostracion", VERSION_DEMO)
    sesion.flush()
    marca = sesion.scalar(
        select(AuditEvent).where(
            AuditEvent.action == ACCION_DEMO,
            AuditEvent.entity_id == VERSION_DEMO,
        )
    )
    assert marca is not None
    conexion = sesion.connection()
    marca.details = {
        "version": VERSION_DEMO,
        "huella": _huella(conexion, _tablas(conexion), marca.id),
    }
    sesion.flush()

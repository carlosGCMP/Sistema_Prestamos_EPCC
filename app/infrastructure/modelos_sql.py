"""Tablas de apoyo de los SQL originales, sin ejecutar ni modificar esos archivos."""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base
from app.infrastructure.models import IDENTIFICADOR, UTCDateTime


class PersonalAdministrativo(Base):
    __tablename__ = "solicitante_personal_administrativo"
    id_solicitante: Mapped[int] = mapped_column(
        ForeignKey("solicitante.id_solicitante"), primary_key=True
    )
    id_persona: Mapped[int] = mapped_column(ForeignKey("persona.id_persona"), unique=True)
    codigo_personal: Mapped[str] = mapped_column(String(20))
    departamento: Mapped[str] = mapped_column(String(100))
    cargo: Mapped[str] = mapped_column(String(100))


class CaracteristicaDelBien(Base):
    __tablename__ = "caracteristica_del_bien"
    __table_args__ = (UniqueConstraint("id_categoria", "nombre_caracteristica"),)
    id_caracteristica: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_categoria: Mapped[int] = mapped_column(ForeignKey("categoria_del_bien.id_categoria"))
    nombre_caracteristica: Mapped[str] = mapped_column(String(100))


class UbicacionDelBien(Base):
    __tablename__ = "ubicacion_del_bien"
    id_ubicacion: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_unidad_fisica: Mapped[int] = mapped_column(ForeignKey("unidad_fisica.id_unidad_fisica"))
    ubicacion: Mapped[str] = mapped_column(String(100))
    fecha_registro: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class EstadoDeLaReserva(Base):
    __tablename__ = "estado_de_la_reserva"
    id_estado: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    nombre_estado: Mapped[str] = mapped_column(String(50), unique=True)


class RegistroDeReserva(Base):
    __tablename__ = "registro_de_reserva"
    __table_args__ = (CheckConstraint("fecha_expiracion > fecha_reserva"),)
    id_reserva: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_solicitud: Mapped[int] = mapped_column(
        ForeignKey("solicitud_de_reserva.id_solicitud"), unique=True
    )
    id_solicitante: Mapped[int] = mapped_column(ForeignKey("solicitante.id_solicitante"))
    id_unidad_fisica: Mapped[int] = mapped_column(ForeignKey("unidad_fisica.id_unidad_fisica"))
    fecha_reserva: Mapped[datetime] = mapped_column(UTCDateTime())
    fecha_expiracion: Mapped[datetime] = mapped_column(UTCDateTime())
    estado: Mapped[str] = mapped_column(ForeignKey("estado_de_la_reserva.nombre_estado"))


class PrestamoAprobadoDeReserva(Base):
    __tablename__ = "prestamo_aprobado_de_reserva"
    __table_args__ = (CheckConstraint("fecha_fin > fecha_inicio"),)
    id_prestamo_aprobado: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_reserva: Mapped[int] = mapped_column(
        ForeignKey("registro_de_reserva.id_reserva"), unique=True
    )
    fecha_aprobacion: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)


class EstadoDelPrestamo(Base):
    __tablename__ = "estado_del_prestamo"
    id_estado: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    nombre_estado: Mapped[str] = mapped_column(String(50), unique=True)


class RegistroBienesFisicosPrestamo(Base):
    __tablename__ = "registro_bienes_fisicos_prestamo"
    __table_args__ = (UniqueConstraint("id_prestamo", "id_unidad_fisica"),)
    id_registro: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_prestamo: Mapped[int] = mapped_column(ForeignKey("prestamo.id_prestamo"))
    id_unidad_fisica: Mapped[int] = mapped_column(ForeignKey("unidad_fisica.id_unidad_fisica"))
    fecha_registro: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class EntregaDelPrestamo(Base):
    __tablename__ = "entrega_del_prestamo"
    id_entrega: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_prestamo: Mapped[int] = mapped_column(ForeignKey("prestamo.id_prestamo"), unique=True)
    fecha_entrega: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    observaciones: Mapped[str | None] = mapped_column(Text)


class DevolucionDelPrestamo(Base):
    __tablename__ = "devolucion_del_prestamo"
    id_devolucion: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_prestamo: Mapped[int] = mapped_column(ForeignKey("prestamo.id_prestamo"), unique=True)
    fecha_devolucion: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    observaciones: Mapped[str | None] = mapped_column(Text)


class ReglasDelPrestamo(Base):
    __tablename__ = "reglas_del_prestamo"
    __table_args__ = (
        UniqueConstraint("id_tipo_bien", "tipo_solicitante"),
        CheckConstraint("cantidad_maxima_prestamos >= 0 AND cantidad_maxima_bienes >= 0"),
    )
    id_regla: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_tipo_bien: Mapped[int] = mapped_column(ForeignKey("tipo_de_bien.id_tipo_bien"))
    tipo_solicitante: Mapped[str] = mapped_column(String(30))
    cantidad_maxima_prestamos: Mapped[int] = mapped_column(Integer)
    cantidad_maxima_bienes: Mapped[int] = mapped_column(Integer)
    permitido: Mapped[bool] = mapped_column(Boolean, default=True)


class VersionDeLaPolitica(Base):
    __tablename__ = "version_de_la_politica"
    id_version: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_politica: Mapped[int] = mapped_column(ForeignKey("politicas_del_prestamo.id_politica"))
    fecha_creacion: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    contenido: Mapped[str] = mapped_column(Text)


class SemestreAcademico(Base):
    __tablename__ = "semestre_academico"
    __table_args__ = (CheckConstraint("fecha_fin > fecha_inicio"),)
    id_semestre: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    nombre_semestre: Mapped[str] = mapped_column(String(50), unique=True)
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)


class MatriculaRealizada(Base):
    __tablename__ = "matricula_realizada"
    __table_args__ = (UniqueConstraint("id_solicitante", "id_semestre"),)
    id_matricula: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_solicitante: Mapped[int] = mapped_column(ForeignKey("solicitante_estudiante.id_solicitante"))
    id_semestre: Mapped[int] = mapped_column(ForeignKey("semestre_academico.id_semestre"))
    fecha_matricula: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class TipoDeGarantia(Base):
    __tablename__ = "tipo_de_garantia"
    id_tipo_garantia: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    nombre_tipo_garantia: Mapped[str] = mapped_column(String(100), unique=True)


class EstadoDeLaGarantia(Base):
    __tablename__ = "estado_de_la_garantia"
    id_estado: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    nombre_estado: Mapped[str] = mapped_column(String(50), unique=True)


class Garantia(Base):
    __tablename__ = "garantia"
    id_garantia: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_prestamo: Mapped[int] = mapped_column(ForeignKey("prestamo.id_prestamo"))
    id_tipo_garantia: Mapped[int] = mapped_column(ForeignKey("tipo_de_garantia.id_tipo_garantia"))
    id_estado: Mapped[int] = mapped_column(ForeignKey("estado_de_la_garantia.id_estado"))
    descripcion: Mapped[str] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class TipoDeIncidencia(Base):
    __tablename__ = "tipo_de_incidencia"
    id_tipo_incidencia: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    nombre_tipo_incidencia: Mapped[str] = mapped_column(String(100), unique=True)


class EstadoDeLaIncidencia(Base):
    __tablename__ = "estado_de_la_incidencia"
    id_estado: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    nombre_estado: Mapped[str] = mapped_column(String(50), unique=True)


class Incidencia(Base):
    __tablename__ = "incidencia"
    id_incidencia: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_solicitante: Mapped[int] = mapped_column(ForeignKey("solicitante.id_solicitante"))
    id_administrador: Mapped[int] = mapped_column(ForeignKey("administrador.id_administrador"))
    id_tipo_incidencia: Mapped[int] = mapped_column(
        ForeignKey("tipo_de_incidencia.id_tipo_incidencia")
    )
    id_estado: Mapped[int] = mapped_column(ForeignKey("estado_de_la_incidencia.id_estado"))
    fecha_incidencia: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    descripcion: Mapped[str] = mapped_column(Text)


class ResolucionDeIncidencia(Base):
    __tablename__ = "resolucion_de_incidencia"
    id_resolucion: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_incidencia: Mapped[int] = mapped_column(ForeignKey("incidencia.id_incidencia"), unique=True)
    fecha_resolucion: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    descripcion: Mapped[str] = mapped_column(Text)


class TipoDeSancion(Base):
    __tablename__ = "tipo_de_sancion"
    id_tipo_sancion: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    nombre_tipo_sancion: Mapped[str] = mapped_column(String(100), unique=True)


class EstadoDeLaSancion(Base):
    __tablename__ = "estado_de_la_sancion"
    id_estado: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    nombre_estado: Mapped[str] = mapped_column(String(50), unique=True)


class Sancion(Base):
    __tablename__ = "sancion"
    id_sancion: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_prestamo: Mapped[int] = mapped_column(ForeignKey("prestamo.id_prestamo"))
    id_tipo_sancion: Mapped[int] = mapped_column(ForeignKey("tipo_de_sancion.id_tipo_sancion"))
    id_estado: Mapped[int] = mapped_column(ForeignKey("estado_de_la_sancion.id_estado"))
    fecha_sancion: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    descripcion: Mapped[str] = mapped_column(Text)


class CumplimientoDeSancion(Base):
    __tablename__ = "cumplimiento_de_sancion"
    id_cumplimiento: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_sancion: Mapped[int] = mapped_column(ForeignKey("sancion.id_sancion"), unique=True)
    fecha_cumplimiento: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    descripcion: Mapped[str] = mapped_column(Text)


class ApelacionDeSancion(Base):
    __tablename__ = "apelacion_de_sancion"
    id_apelacion: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_sancion: Mapped[int] = mapped_column(ForeignKey("sancion.id_sancion"), unique=True)
    fecha_apelacion: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    descripcion: Mapped[str] = mapped_column(Text)


class TipoDeEvento(Base):
    __tablename__ = "tipo_de_evento"
    id_tipo_evento: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    nombre_tipo_evento: Mapped[str] = mapped_column(String(100), unique=True)


class HistorialDeCambios(Base):
    __tablename__ = "historial_de_cambios"
    id_historial: Mapped[int] = mapped_column(IDENTIFICADOR, Identity(), primary_key=True)
    id_registro: Mapped[int] = mapped_column(ForeignKey("registro_auditoria.id_registro"))
    fecha: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    descripcion: Mapped[str] = mapped_column(Text)

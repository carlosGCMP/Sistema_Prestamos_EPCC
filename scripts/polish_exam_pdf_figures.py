#!/usr/bin/env python3
"""Replace only the two UML figures in a generated exam PDF, retaining its design."""

from __future__ import annotations

import argparse
import io
from pathlib import Path

import pdfplumber
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path.home() / "Documents" / "informe_prestamos_epcc.pdf"
DEFAULT_OUTPUT = ROOT / "docs" / "entregables" / "informe-primer-examen.pdf"

BLUE = colors.HexColor("#245AA2")
INK = colors.HexColor("#202A37")
MUTED = colors.HexColor("#5B6676")
LINE = colors.HexColor("#6D7886")
PALE = colors.HexColor("#F2F5F9")
PALE_BLUE = colors.HexColor("#EEF3F9")
PRESENTATION = colors.HexColor("#F7F1E7")
APPLICATION = colors.HexColor("#E8EEF8")
DOMAIN = colors.HexColor("#E9F1E8")
INFRA = colors.HexColor("#EEE8F3")
WHITE = colors.white


def label(c: canvas.Canvas, text: str, x: float, y: float, *, size: float = 6.2, bold: bool = False, color=INK) -> None:
    c.setFillColor(color)
    c.setFont("Times-Bold" if bold else "Times-Roman", size)
    c.drawString(x, y, text)


def arrow(c: canvas.Canvas, points: list[tuple[float, float]], *, color=LINE, width: float = 0.8) -> None:
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    path = c.beginPath()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    c.drawPath(path)
    x1, y1 = points[-2]
    x2, y2 = points[-1]
    c.saveState()
    c.translate(x2, y2)
    import math

    angle = math.atan2(y2 - y1, x2 - x1)
    c.rotate(angle * 180 / math.pi)
    c.line(-4.2, -2.0, 0, 0)
    c.line(-4.2, 2.0, 0, 0)
    c.restoreState()


def class_box(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    details: list[str],
) -> None:
    c.setFillColor(PALE)
    c.setStrokeColor(BLUE)
    c.setLineWidth(0.75)
    c.roundRect(x, y, width, height, 2, fill=1, stroke=1)
    c.setFillColor(PALE_BLUE)
    c.roundRect(x, y + height - 15, width, 15, 2, fill=1, stroke=0)
    label(c, title, x + 5, y + height - 10.5, size=7.2, bold=True, color=BLUE)
    c.setStrokeColor(colors.HexColor("#CAD4E0"))
    c.setLineWidth(0.4)
    c.line(x, y + height - 15, x + width, y + height - 15)
    for index, text in enumerate(details):
        label(c, text, x + 5, y + height - 25 - index * 8, size=6.15)


def draw_domain(c: canvas.Canvas) -> None:
    ox, oy = 32, 31
    c.setFillColor(WHITE)
    c.rect(ox - 2, oy - 2, 534, 304, fill=1, stroke=0)

    # Associations; orthogonal routes keep the diagram close to the source style.
    arrow(c, [(ox + 103, oy + 224), (ox + 103, oy + 192)])
    arrow(c, [(ox + 158, oy + 259), (ox + 195, oy + 259)])
    arrow(c, [(ox + 158, oy + 233), (ox + 171, oy + 220), (ox + 171, oy + 120), (ox + 195, oy + 120)])
    arrow(c, [(ox + 261, oy + 220), (ox + 261, oy + 186)])
    arrow(c, [(ox + 327, oy + 252), (ox + 370, oy + 252), (ox + 370, oy + 95), (ox + 394, oy + 95)])
    arrow(c, [(ox + 327, oy + 164), (ox + 382, oy + 164), (ox + 382, oy + 70), (ox + 394, oy + 70)])
    arrow(c, [(ox + 261, oy + 103), (ox + 261, oy + 83)])
    arrow(c, [(ox + 460, oy + 244), (ox + 460, oy + 222)])
    arrow(c, [(ox + 460, oy + 180), (ox + 460, oy + 158)])
    arrow(c, [(ox + 460, oy + 116), (ox + 460, oy + 94)])

    # Relationship names and multiplicities.
    label(c, "cuenta", ox + 110, oy + 207, size=5.8, color=BLUE)
    label(c, "0..1", ox + 106, oy + 216, size=5.6, bold=True)
    label(c, "1", ox + 106, oy + 188, size=5.6, bold=True)
    label(c, "solicitante", ox + 161, oy + 264, size=5.6, color=BLUE)
    label(c, "0..*", ox + 160, oy + 251, size=5.5, bold=True)
    label(c, "1", ox + 188, oy + 251, size=5.5, bold=True)
    label(c, "0..*", ox + 160, oy + 229, size=5.5, bold=True)
    label(c, "1", ox + 188, oy + 117, size=5.5, bold=True)
    label(c, "reserva origen", ox + 264, oy + 202, size=5.6, color=BLUE)
    label(c, "0..1", ox + 263, oy + 211, size=5.4, bold=True)
    label(c, "0..1", ox + 263, oy + 187, size=5.4, bold=True)
    label(c, "unidad", ox + 334, oy + 259, size=5.6, color=BLUE)
    label(c, "0..*", ox + 313, oy + 247, size=5.4, bold=True)
    label(c, "1", ox + 384, oy + 98, size=5.4, bold=True)
    label(c, "unidad", ox + 336, oy + 170, size=5.6, color=BLUE)
    label(c, "0..*", ox + 313, oy + 159, size=5.4, bold=True)
    label(c, "1", ox + 384, oy + 67, size=5.4, bold=True)
    label(c, "1", ox + 263, oy + 100, size=5.4, bold=True)
    label(c, "0..*", ox + 263, oy + 84, size=5.4, bold=True)
    for y, relation in ((244, "tipos"), (180, "fichas"), (116, "unidades")):
        label(c, "1", ox + 463, oy + y, size=5.2, bold=True)
        label(c, "0..*", ox + 463, oy + y - 13, size=5.2, bold=True)
        label(c, relation, ox + 470, oy + y - 7, size=5.3, color=BLUE)

    class_box(c, ox + 48, oy + 224, 110, 64, "Persona", ["nombre, CUI/documento", "vinculación, rol y estado"])
    class_box(c, ox + 48, oy + 138, 110, 54, "Cuenta", ["usuario, hash de contraseña", "estado y último acceso"])
    class_box(c, ox + 195, oy + 220, 132, 68, "Reserva", ["intervalo, solicitud y uso", "estado y motivo de rechazo"])
    class_box(c, ox + 195, oy + 103, 132, 83, "Préstamo", ["solicitante, administrador", "plazo, estado y modalidad", "datos de entrega/devolución"])
    class_box(c, ox + 195, oy + 31, 132, 52, "Renovación", ["secuencia y vencimientos", "administrador, autorización"])
    class_box(c, ox + 394, oy + 244, 132, 42, "CategoriaBien", ["nombre, descripción, estado"])
    class_box(c, ox + 394, oy + 180, 132, 42, "TipoBien", ["nombre, prestable, estado"])
    class_box(c, ox + 394, oy + 116, 132, 42, "FichaBien", ["nombre, descripción, estado"])
    class_box(c, ox + 394, oy + 52, 132, 42, "UnidadFisica", ["inventario, ubicación, condición"])


def package_box(c: canvas.Canvas, x: float, y: float, width: float, height: float, title: str, subtitle: str, fill) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(BLUE)
    c.setLineWidth(0.8)
    c.roundRect(x, y, width, height, 4, fill=1, stroke=1)
    label(c, f"«paquete» {title}", x + 8, y + height - 14, size=9.2, bold=True, color=BLUE)
    label(c, subtitle, x + 8, y + height - 27, size=6.5, color=MUTED)


def chip(c: canvas.Canvas, x: float, y: float, width: float, height: float, stereotype: str, text: str) -> None:
    c.setFillColor(WHITE)
    c.setStrokeColor(BLUE)
    c.setLineWidth(0.55)
    c.roundRect(x, y, width, height, 2, fill=1, stroke=1)
    label(c, stereotype, x + 4, y + height - 7, size=5.6, color=MUTED)
    label(c, text, x + 4, y + 4, size=6.3, color=INK)


def draw_architecture(c: canvas.Canvas) -> None:
    ox, oy = 32, 39
    c.setFillColor(WHITE)
    c.rect(ox - 2, oy - 2, 534, 386, fill=1, stroke=0)

    # The original uses four horizontal UML package bands with pastel fills.
    package_box(c, ox, oy + 300, 530, 68, "Presentación", "FastAPI + Pydantic", PRESENTATION)
    package_box(c, ox, oy + 211, 530, 79, "Aplicación", "Casos de uso y coordinación", APPLICATION)
    package_box(c, ox, oy + 110, 530, 91, "Dominio", "Entidades, reglas y contratos", DOMAIN)
    package_box(c, ox, oy + 20, 530, 78, "Infraestructura", "PostgreSQL, SQLAlchemy, seguridad y migraciones", INFRA)

    chip(c, ox + 9, oy + 307, 157, 19, "«API»", "Operaciones HTTP")
    chip(c, ox + 175, oy + 307, 220, 19, "«esquema»", "Validación de entrada y salida")

    app_chips = [
        (9, 92, "«caso de uso»", "Gestionar reservas"),
        (105, 92, "«caso de uso»", "Registrar préstamo"),
        (201, 100, "«caso de uso»", "Entrega y devolución"),
        (305, 104, "«caso de uso»", "Registrar renovación"),
        (413, 108, "«caso de uso»", "Consultar disponibilidad"),
    ]
    for x, width, stereotype, text in app_chips:
        chip(c, ox + x, oy + 229, width, 20, stereotype, text)

    entity_chips = [
        (9, 55, "Persona"), (67, 48, "Cuenta"), (118, 78, "CategoriaBien"),
        (199, 52, "TipoBien"), (254, 58, "FichaBien"), (315, 70, "UnidadFisica"),
        (388, 50, "Reserva"), (441, 50, "Préstamo"), (494, 29, "Renov."),
    ]
    for x, width, text in entity_chips:
        chip(c, ox + x, oy + 151, width, 19, "«entidad»", text)
    chip(c, ox + 9, oy + 119, 205, 19, "«interfaz»", "Contratos de persistencia y seguridad")

    chip(c, ox + 9, oy + 32, 235, 23, "«adaptador»", "Persistencia (SQLAlchemy / PostgreSQL)")
    chip(c, ox + 253, oy + 32, 88, 23, "«adaptador»", "Seguridad")
    chip(c, ox + 350, oy + 32, 135, 23, "«adaptador»", "Migraciones (Alembic)")

    # Dependency arrows use the same blue annotation style as the source.
    arrow(c, [(ox + 265, oy + 300), (ox + 265, oy + 290)], width=0.75)
    label(c, "depende", ox + 274, oy + 293, size=5.6, color=MUTED)
    arrow(c, [(ox + 265, oy + 211), (ox + 265, oy + 201)], width=0.75)
    label(c, "depende", ox + 274, oy + 204, size=5.6, color=MUTED)
    arrow(c, [(ox + 265, oy + 98), (ox + 265, oy + 110)], width=0.75)
    label(c, "implementa contratos", ox + 274, oy + 103, size=5.6, color=MUTED)


def make_overlay(page_index: int, draw_figure) -> bytes:
    stream = io.BytesIO()
    c = canvas.Canvas(stream, pagesize=A4, pageCompression=1)
    if page_index == 1:
        draw_domain(c)
    else:
        draw_architecture(c)
    c.save()
    return stream.getvalue()


def polish(source: Path, output: Path) -> None:
    with pdfplumber.open(source) as pdf:
        if len(pdf.pages) != 4 or any(abs(page.width - 595) > 1 or abs(page.height - 842) > 1 for page in pdf.pages):
            raise ValueError("La herramienta espera el PDF original de cuatro páginas A4.")
    reader = PdfReader(str(source))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    domain_overlay = PdfReader(io.BytesIO(make_overlay(1, draw_domain))).pages[0]
    architecture_overlay = PdfReader(io.BytesIO(make_overlay(2, draw_architecture))).pages[0]
    # Only the original diagram areas are white-masked; text, captions, colors,
    # fonts, headings, footer, and pagination remain from the supplied PDF.
    writer.pages[1].merge_page(domain_overlay, over=True)
    writer.pages[2].merge_page(architecture_overlay, over=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        writer.write(stream)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    polish(args.source, args.output)
    print(args.output)


if __name__ == "__main__":
    main()

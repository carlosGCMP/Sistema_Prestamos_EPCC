#!/usr/bin/env python3
"""Create a print-ready PDF containing the revised first-exam diagrams."""

from __future__ import annotations

import tempfile
from pathlib import Path

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from generate_exam_report import draw_architecture, draw_domain


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "entregables" / "diagramas-examen1-revisados.pdf"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = landscape(letter)
    with tempfile.TemporaryDirectory(prefix="epcc-diagrams-") as temp_dir:
        temp = Path(temp_dir)
        diagrams = [
            ("01-modelo-dominio.png", "Modelo de dominio", draw_domain),
            ("02-arquitectura-capas.png", "Arquitectura en capas", draw_architecture),
        ]
        pdf = canvas.Canvas(str(OUTPUT), pagesize=(page_width, page_height), pageCompression=1)
        pdf.setTitle("Diagramas revisados para el primer examen - Sistema de Préstamos EPCC")
        pdf.setAuthor("Sistema de Préstamos EPCC")
        for filename, title, draw_diagram in diagrams:
            image_path = temp / filename
            draw_diagram(image_path)
            pdf.drawImage(
                str(image_path),
                0.2 * inch,
                0.94 * inch,
                width=10.6 * inch,
                height=6.625 * inch,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
            pdf.showPage()
        pdf.save()
    print(OUTPUT)


if __name__ == "__main__":
    main()

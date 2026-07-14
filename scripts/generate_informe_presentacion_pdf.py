#!/usr/bin/env python3
"""
Genera PDF del informe tecnico de presentacion EcoGrow y lo copia a Descargas.
Uso:
  python3 scripts/generate_informe_presentacion_pdf.py
  python3 scripts/generate_informe_presentacion_pdf.py --no-downloads
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "documentacion_equipo"
    / "entregables"
    / "INFORME_TECNICO_PRESENTACION_ECOGROW_2026-07.md"
)
OUTPUT_REPO = (
    ROOT
    / "documentacion_equipo"
    / "entregables"
    / "INFORME_TECNICO_PRESENTACION_ECOGROW_2026-07.pdf"
)
DOWNLOADS = Path.home() / "Downloads" / "INFORME_TECNICO_PRESENTACION_ECOGROW_2026-07.pdf"

# Reutilizar el generador existente
sys.path.insert(0, str(ROOT / "scripts"))
from generate_proyecto_pdf import EcoGrowPdf  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-downloads",
        action="store_true",
        help="No copiar a ~/Downloads",
    )
    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"No existe el markdown: {SOURCE}", file=sys.stderr)
        return 1

    builder = EcoGrowPdf()
    # Portada adaptada al informe
    builder.pdf.add_page()
    builder.pdf.set_fill_color(15, 118, 110)
    builder.pdf.rect(0, 0, builder.pdf.w, 55, style="F")
    builder.pdf.set_y(18)
    builder.pdf.set_font("Helvetica", "B", 26)
    builder.pdf.set_text_color(255, 255, 255)
    builder.pdf.cell(0, 12, "EcoGrow", align="C", new_x="LMARGIN", new_y="NEXT")
    builder.pdf.set_font("Helvetica", size=11)
    builder.pdf.cell(
        0,
        8,
        "Informe tecnico de presentacion",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    builder.pdf.set_text_color(0, 0, 0)
    builder.pdf.ln(22)
    builder.pdf.set_font("Helvetica", "B", 14)
    builder.pdf.cell(
        0,
        9,
        "Automatizacion agricola · Torre vegetal + Forraje",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    builder.pdf.ln(8)
    builder.pdf.set_font("Helvetica", size=10)
    for line in [
        "Fuente: documentacion y codigo en GitHub",
        "github.com/elJohn72/proyecto_ecogrow",
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "AJTecnology / AJENZA S.A.S.",
    ]:
        builder.pdf.cell(0, 6, line, align="C", new_x="LMARGIN", new_y="NEXT")
    builder._footer()

    content = SOURCE.read_text(encoding="utf-8")
    builder.render_markdown(
        content,
        section_title="Informe tecnico de presentacion",
    )
    builder.save(OUTPUT_REPO)
    print(f"PDF en repo: {OUTPUT_REPO} ({OUTPUT_REPO.stat().st_size // 1024} KB)")

    if not args.no_downloads:
        DOWNLOADS.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUTPUT_REPO, DOWNLOADS)
        print(f"PDF en Descargas: {DOWNLOADS}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

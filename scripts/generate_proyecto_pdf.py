#!/usr/bin/env python3
"""Renderizador PDF compartido por los informes de EcoGrow."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

FONT_CANDIDATES = (
    (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
    ),
    (
        "/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/Library/Fonts/Arial Italic.ttf",
        "/Library/Fonts/Arial Bold Italic.ttf",
    ),
)


class EcoGrowPdf:
    def __init__(self) -> None:
        self.pdf = FPDF(format="A4")
        self.pdf.set_auto_page_break(auto=True, margin=18)
        self.pdf.set_margins(16, 16, 16)
        self.font = self._register_font()
        self.pdf.footer = self._footer

    def _register_font(self) -> str:
        for regular, bold, italic, bold_italic in FONT_CANDIDATES:
            if all(Path(path).exists() for path in (regular, bold, italic, bold_italic)):
                self.pdf.add_font("Body", "", regular)
                self.pdf.add_font("Body", "B", bold)
                self.pdf.add_font("Body", "I", italic)
                self.pdf.add_font("Body", "BI", bold_italic)
                return "Body"
        return "Helvetica"

    def _footer(self) -> None:
        self.pdf.set_y(-12)
        self.pdf.set_font(self.font, size=8)
        self.pdf.set_text_color(90, 90, 90)
        self.pdf.cell(0, 6, f"{self.pdf.page_no()}", align="C")
        self.pdf.set_text_color(0, 0, 0)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.pdf.output(path)

    def render_markdown(self, content: str, section_title: str = "") -> None:
        del section_title
        self.pdf.add_page()
        usable = self.pdf.w - self.pdf.l_margin - self.pdf.r_margin
        lines = content.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index].rstrip()
            if not line or line.strip() == "---":
                self.pdf.ln(2)
                index += 1
                continue
            if line.startswith("```"):
                index += 1
                block: list[str] = []
                while index < len(lines) and not lines[index].startswith("```"):
                    block.append(lines[index].rstrip())
                    index += 1
                index += 1
                self._code(block, usable)
                continue
            if line.startswith("|"):
                rows: list[str] = []
                while index < len(lines) and lines[index].startswith("|"):
                    rows.append(lines[index])
                    index += 1
                self._table(rows, usable)
                continue
            if line.startswith("# "):
                self._heading(line[2:].strip(), 16)
            elif line.startswith("## "):
                self._heading(line[3:].strip(), 13)
            elif line.startswith("### "):
                self._heading(line[4:].strip(), 11)
            elif line.startswith("- "):
                self._paragraph("• " + self._plain(line[2:].strip()), 10)
            elif len(line) > 2 and line[0].isdigit() and line[1] == ".":
                self._paragraph(self._plain(line), 10)
            else:
                self._paragraph(self._plain(line), 10)
            index += 1

    def _heading(self, text: str, size: int) -> None:
        self.pdf.ln(2)
        self.pdf.set_font(self.font, "B", size)
        self.pdf.set_text_color(25, 92, 61)
        self.pdf.multi_cell(0, 7, self._plain(text), align="L")
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.ln(1)

    def _paragraph(self, text: str, size: int) -> None:
        self.pdf.set_font(self.font, size=size)
        self.pdf.multi_cell(0, 5.5, text, align="L")
        self.pdf.ln(0.6)

    def _code(self, block: list[str], usable: float) -> None:
        self.pdf.set_font("Courier", size=8)
        self.pdf.set_fill_color(244, 247, 244)
        for raw in block:
            self.pdf.multi_cell(usable, 4.4, raw if raw else " ", fill=True, align="L")
        self.pdf.ln(2)
        self.pdf.set_font(self.font, size=10)

    def _table(self, rows: list[str], usable: float) -> None:
        parsed = [self._cells(row) for row in rows]
        parsed = [row for row in parsed if not all(set(cell) <= {"-", ":", " "} for cell in row)]
        if not parsed:
            return
        columns = max(len(row) for row in parsed)
        width = usable / columns
        for row_index, row in enumerate(parsed):
            row = row + [""] * (columns - len(row))
            style = "B" if row_index == 0 else ""
            self.pdf.set_font(self.font, style, 8)
            if row_index == 0:
                self.pdf.set_fill_color(25, 92, 61)
                self.pdf.set_text_color(255, 255, 255)
            else:
                self.pdf.set_fill_color(247, 250, 247 if row_index % 2 else 255)
                self.pdf.set_text_color(23, 43, 34)
            heights = [
                max(6, self.pdf.multi_cell(width - 2, 4.2, cell, dry_run=True, output="HEIGHT", align="L"))
                for cell in row
            ]
            row_height = max(heights)
            if self.pdf.get_y() + row_height > self.pdf.h - 18:
                self.pdf.add_page()
            x0 = self.pdf.l_margin
            y0 = self.pdf.get_y()
            for column, cell in enumerate(row):
                x = x0 + column * width
                self.pdf.set_xy(x, y0)
                self.pdf.rect(x, y0, width, row_height, style="F")
                self.pdf.set_xy(x + 1, y0 + 1)
                self.pdf.multi_cell(width - 2, 4.2, cell, align="L")
            self.pdf.set_xy(x0, y0 + row_height)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.ln(3)

    @staticmethod
    def _cells(row: str) -> list[str]:
        parts = [EcoGrowPdf._plain(part.strip()) for part in row.strip().strip("|").split("|")]
        return parts

    @staticmethod
    def _plain(text: str) -> str:
        return (
            text.replace("**", "")
            .replace("*", "")
            .replace("`", "")
            .replace("\\", "")
        )

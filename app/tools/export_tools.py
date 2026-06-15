"""Report export helpers."""

from __future__ import annotations

import io
import logging
import re
import textwrap
from datetime import UTC, datetime
from pathlib import Path

from app.config import REPORTS_DIR

logger = logging.getLogger(__name__)


def slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-").lower() or "report"


def save_markdown_report(markdown: str, ticker: str, output_dir: Path | None = None) -> Path:
    output_dir = output_dir or REPORTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{slugify(ticker)}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.md"
    path = output_dir / filename
    path.write_text(markdown, encoding="utf-8")
    return path


def markdown_to_pdf_bytes(markdown: str) -> bytes:
    """Convert markdown to a simple PDF byte stream.

    Uses reportlab when present and falls back to a minimal standards-compliant
    PDF writer so the Streamlit demo can always offer a PDF download.
    """

    try:
        from reportlab.lib.pagesizes import letter  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 54
        for raw_line in markdown.splitlines():
            clean = _markdown_to_text(raw_line)
            wrapped = textwrap.wrap(clean, width=92) or [""]
            for line in wrapped:
                if y < 54:
                    pdf.showPage()
                    y = height - 54
                pdf.drawString(54, y, line[:110])
                y -= 14
        pdf.save()
        return buffer.getvalue()
    except Exception as exc:
        logger.info("Using minimal PDF fallback: %s", exc)
        return _minimal_pdf(markdown)


def _markdown_to_text(line: str) -> str:
    line = re.sub(r"^#+\s*", "", line)
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    line = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1 (\2)", line)
    return line


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _minimal_pdf(markdown: str) -> bytes:
    lines: list[str] = []
    for raw_line in markdown.splitlines():
        text = _markdown_to_text(raw_line)
        lines.extend(textwrap.wrap(text, width=90) or [""])

    pages = [lines[idx : idx + 48] for idx in range(0, len(lines), 48)] or [["CapitalLens AI Research Memo"]]
    objects: list[bytes] = []

    def add_object(payload: str) -> int:
        objects.append(payload.encode("latin-1", errors="replace"))
        return len(objects)

    catalog_id = add_object("<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add_object("<< /Type /Pages /Kids [] /Count 0 >>")
    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    content_ids: list[int] = []

    for page_lines in pages:
        commands = ["BT", "/F1 10 Tf", "54 750 Td", "14 TL"]
        for line in page_lines:
            commands.append(f"({_pdf_escape(line)}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = "\n".join(commands)
        content_id = add_object(f"<< /Length {len(stream.encode('latin-1', errors='replace'))} >>\nstream\n{stream}\nendstream")
        page_id = add_object(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>")
        content_ids.append(content_id)
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("latin-1")
    objects[catalog_id - 1] = b"<< /Type /Catalog /Pages 2 0 R >>"

    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for idx, payload in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{idx} 0 obj\n".encode("ascii"))
        output.write(payload)
        output.write(b"\nendobj\n")
    xref_pos = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode("ascii"))
    return output.getvalue()

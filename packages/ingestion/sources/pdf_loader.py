"""PDF text extractor using pdfplumber.

Extracts plain text from PDFs, preserving paragraph structure.
Degraded layout (tables, multi-column) is accepted — the text is still
useful for retrieval even if formatting is imperfect.
"""

from __future__ import annotations

import re


def extract_text(pdf_bytes: bytes) -> str:
    """Return plain text extracted from PDF bytes."""
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(__import__("io").BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if text:
                pages.append(text)

    combined = "\n\n".join(pages)
    # normalize whitespace but preserve paragraph breaks
    combined = re.sub(r"[ \t]+", " ", combined)
    combined = re.sub(r"\n{3,}", "\n\n", combined)
    return combined.strip()

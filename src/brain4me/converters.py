from __future__ import annotations

import sys
from pathlib import Path


def extract_text_from_pdf(path: str | Path) -> str:
    """Extract raw text from a PDF using pymupdf (fitz)."""
    try:
        import fitz
    except ImportError:
        print("pymupdf is required: pip install pymupdf", file=sys.stderr)
        raise

    pages: list[str] = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            text = page.get_text()
            if text:
                pages.append(text)
    return "\n".join(pages)


def extract_text_from_docx(path: str | Path) -> str:
    """Extract raw text from a DOCX using python-docx."""
    try:
        from docx import Document
    except ImportError:
        print("python-docx is required: pip install python-docx", file=sys.stderr)
        raise

    doc = Document(str(path))
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def extract_text_from_txt(path: str | Path) -> str:
    """Read a plain-text file.  Tries UTF-8 first, falls back to Latin-1."""
    path = Path(path)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def convert_file(path: str | Path) -> str:
    """Route a document file to the appropriate text extractor based on extension.

    Supported formats: .pdf, .docx, .txt

    Raises ValueError if the extension is not supported.
    """
    path = Path(path)
    suffix = path.suffix.lower()

    converters = {
        ".pdf": extract_text_from_pdf,
        ".docx": extract_text_from_docx,
        ".txt": extract_text_from_txt,
    }

    converter = converters.get(suffix)
    if converter is None:
        supported = ", ".join(converters)
        raise ValueError(
            f"Unsupported file format '{suffix}' for {path}. "
            f"Supported formats: {supported}"
        )

    return converter(path)

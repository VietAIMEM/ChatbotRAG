from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.document_processing.cleaner import clean_text

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md", ".markdown", ".text"}
EXTENSIBLE_EXTENSIONS = {".pptx", ".xlsx"}

# Mapping of file extensions to document types.
EXTENSION_TYPE = {
    ".pdf": "pdf",
    ".doc": "doc",
    ".docx": "docx",
    ".txt": "txt",
    ".md": "md",
    ".markdown": "md",
    ".text": "txt",
}


@dataclass
class ParsedPage:
    text: str
    page_number: int | None = None


@dataclass
class ParsedDocument:
    pages: list[ParsedPage] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)

    @property
    def total_pages(self) -> int:
        return len(self.pages)


class ParseError(Exception):
    pass


def extract_pdf(path: str) -> list[ParsedPage]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise ParseError("pypdf is not installed") from exc
    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise ParseError(f"Cannot read PDF file: {exc}") from exc
    pages: list[ParsedPage] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            logger.warning("PDF page %s extraction failed: %s", index, exc)
            text = ""
        text = clean_text(text)
        if text:
            pages.append(ParsedPage(text=text, page_number=index))
    if not pages:
        raise ParseError("No extractable text found in PDF (scanned image PDFs are not supported).")
    return pages


def extract_docx(path: str) -> list[ParsedPage]:
    try:
        import docx  # python-docx
    except ImportError as exc:  # pragma: no cover
        raise ParseError("python-docx is not installed") from exc
    try:
        document = docx.Document(path)
    except Exception as exc:
        raise ParseError(f"Cannot read DOCX file: {exc}") from exc

    parts: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    text = clean_text("\n".join(parts))
    if not text:
        raise ParseError("No text content found in DOCX file.")
    return [ParsedPage(text=text)]


def _run_antiword(path: str) -> str | None:
    try:
        result = subprocess.run(
            ["antiword", path],
            capture_output=True,
            text=True,
            timeout=120,
            errors="replace",
        )
        if result.returncode == 0:
            return result.stdout
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        logger.warning("antiword unavailable or failed: %s", exc)
    return None


def extract_doc(path: str) -> list[ParsedPage]:
    text = _run_antiword(path)
    if text and text.strip():
        return [ParsedPage(text=clean_text(text))]

    # Fallback: minimal OLE binary text extraction.
    try:
        import olefile

        if olefile.isOleFile(path):
            ole = olefile.OleFileIO(path)
            if ole.exists("WordDocument"):
                data = ole.openstream("WordDocument").read()
                # Decode text stream as best effort (UTF-16LE/ASCII).
                try:
                    decoded = data.decode("utf-16-le", errors="ignore")
                except Exception:
                    decoded = ""
                text = clean_text(decoded)
                if text and len(text) > 40:
                    return [ParsedPage(text=text)]
    except Exception as exc:
        logger.warning("OLE .doc extraction failed: %s", exc)

    raise ParseError(
        "Could not extract text from the .doc file. Legacy binary .doc files "
        "require the 'antiword' tool (installed in the Docker image). Please "
        "convert the file to .docx or .txt and try again."
    )


def extract_plain_text(path: str) -> list[ParsedPage]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except Exception as exc:
        raise ParseError(f"Cannot read text file: {exc}") from exc
    text = clean_text(text)
    if not text:
        raise ParseError("File is empty.")
    return [ParsedPage(text=text)]


def parse_document(path: str, extension: str) -> ParsedDocument:
    extension = extension.lower()
    if extension == ".pdf":
        return ParsedDocument(pages=extract_pdf(path))
    if extension == ".docx":
        return ParsedDocument(pages=extract_docx(path))
    if extension == ".doc":
        return ParsedDocument(pages=extract_doc(path))
    if extension in (".txt", ".md", ".markdown", ".text"):
        return ParsedDocument(pages=extract_plain_text(path))
    raise ParseError(f"Unsupported file extension: {extension}")

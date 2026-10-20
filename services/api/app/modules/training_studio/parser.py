"""Document parser for Training Studio.

Extracts text from uploaded documents (PDF, DOCX, PPTX, TXT, Markdown).
DOCX and PPTX are standard OpenXML zip archives parsed natively using Python's
built-in ``zipfile`` and ``xml.etree.ElementTree`` without external dependencies.
"""

import io
import re
import xml.etree.ElementTree as ET
import zipfile


class DocumentParseError(Exception):
    """Raised when an uploaded document cannot be parsed or exceeds safety limits."""


MAX_DOCUMENT_BYTES = 25 * 1024 * 1024  # 25 MB


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from file bytes according to file extension."""
    if len(file_bytes) > MAX_DOCUMENT_BYTES:
        raise DocumentParseError(
            f"Document exceeds maximum allowed size of {MAX_DOCUMENT_BYTES // (1024 * 1024)}MB"
        )

    lower_name = filename.lower()

    if lower_name.endswith((".txt", ".md", ".csv", ".json")):
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="replace")

    if lower_name.endswith(".docx"):
        return _extract_docx(file_bytes)

    if lower_name.endswith(".pptx"):
        return _extract_pptx(file_bytes)

    if lower_name.endswith(".pdf"):
        return _extract_pdf_stream(file_bytes)

    # Fallback to UTF-8 decoding with replacement
    return file_bytes.decode("utf-8", errors="replace")


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from a Word .docx archive using python-docx with native XML fallback."""
    try:
        import docx

        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    paragraphs.append(" | ".join(row_text))
        if paragraphs:
            return "\n\n".join(paragraphs)
    except Exception:
        pass

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs_fallback: list[str] = []
            for p in tree.iterfind(".//w:p", namespaces):
                texts = [node.text for node in p.iterfind(".//w:t", namespaces) if node.text]
                if texts:
                    paragraphs_fallback.append("".join(texts))
            return "\n\n".join(paragraphs_fallback)
    except Exception as exc:
        raise DocumentParseError(f"Failed to parse DOCX file: {exc}") from exc


def _extract_pptx(file_bytes: bytes) -> str:
    """Extract text from a PowerPoint .pptx archive using python-pptx with native XML fallback."""
    try:
        import pptx

        prs = pptx.Presentation(io.BytesIO(file_bytes))
        slides_text: list[str] = []
        for index, slide in enumerate(prs.slides, 1):
            slide_parts: list[str] = []
            for shape in slide.shapes:
                if shape.has_text_frame and shape.text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        if paragraph.text.strip():
                            slide_parts.append(paragraph.text.strip())
            if slide_parts:
                slides_text.append(f"--- Slide {index} ---\n" + "\n".join(slide_parts))
        if slides_text:
            return "\n\n".join(slides_text)
    except Exception:
        pass

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            slide_entries = sorted(
                [name for name in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml", name)]
            )
            slides_text_fallback: list[str] = []
            namespaces = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
            for index, slide_name in enumerate(slide_entries, 1):
                xml_content = z.read(slide_name)
                tree = ET.fromstring(xml_content)
                texts = [node.text for node in tree.iterfind(".//a:t", namespaces) if node.text]
                if texts:
                    slides_text_fallback.append(f"--- Slide {index} ---\n" + "\n".join(texts))
            return "\n\n".join(slides_text_fallback)
    except Exception as exc:
        raise DocumentParseError(f"Failed to parse PPTX file: {exc}") from exc


def _extract_pdf_stream(file_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF with native stream regex fallback."""
    try:
        import pymupdf

        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        pages_text: list[str] = []
        for index, page in enumerate(doc, 1):
            text = page.get_text()
            if text.strip():
                pages_text.append(f"--- Page {index} ---\n" + text.strip())
        if pages_text:
            return "\n\n".join(pages_text)
    except Exception:
        pass

    try:
        text_parts: list[str] = []
        stream_matches = re.findall(rb"stream[\r\n]+(.*?)[\r\n]+endstream", file_bytes, re.DOTALL)
        for stream in stream_matches:
            matches = re.findall(rb"\(([^)]+)\)\s*(?:Tj|'|\")", stream)
            for m in matches:
                try:
                    decoded = m.decode("utf-8", errors="ignore").strip()
                    if len(decoded) > 1 and re.search(r"[a-zA-Z0-9]", decoded):
                        text_parts.append(decoded)
                except Exception:
                    continue
        if text_parts:
            return " ".join(text_parts)

        ascii_matches = re.findall(rb"[A-Za-z0-9 .,;:!?'\"\-\n]{10,}", file_bytes)
        return "\n".join(
            [m.decode("utf-8", errors="ignore").strip() for m in ascii_matches if m.strip()]
        )
    except Exception as exc:
        raise DocumentParseError(f"Failed to parse PDF file: {exc}") from exc

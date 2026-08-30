from __future__ import annotations

import csv
import io
import json
import logging
import re
import zipfile
from dataclasses import dataclass, field, replace
from typing import Any

from defusedxml import ElementTree

from .discovery import Occurrence, discover_in_text, discover_posts_in_text

ProfileFinding = tuple[str, Occurrence]
PostFinding = tuple[str, str | None, Occurrence]
_MAX_OOXML_FILES = 10_000
_MAX_OOXML_UNCOMPRESSED_BYTES = 100 * 1024 * 1024


@dataclass(slots=True)
class IngestedLinks:
    profiles: list[ProfileFinding] = field(default_factory=list)
    posts: list[PostFinding] = field(default_factory=list)

    def extend(self, other: IngestedLinks) -> None:
        self.profiles.extend(other.profiles)
        self.posts.extend(other.posts)


class IngestError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def sniff_kind(payload: bytes, filename: str) -> str:
    """Detect the practical input kind from content, not from the filename."""
    if payload.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                members = archive.infolist()
                if (
                    len(members) > _MAX_OOXML_FILES
                    or sum(member.file_size for member in members)
                    > _MAX_OOXML_UNCOMPRESSED_BYTES
                ):
                    raise IngestError("The OOXML archive expands beyond the safe limit.")
                names = [member.filename for member in members]
        except IngestError:
            raise
        except zipfile.BadZipFile as exc:
            raise IngestError("The upload is a corrupt OOXML archive.") from exc
        if any(name.startswith("xl/") for name in names):
            return "xlsx"
        if any(name.startswith("word/") for name in names):
            return "docx"
        raise IngestError("Unsupported OOXML archive.")
    if payload.startswith(b"%PDF"):
        return "pdf"
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IngestError("Unsupported binary file format.") from exc
    if "\x00" in text:
        raise IngestError("Unsupported binary file format.")
    if text.lstrip().startswith(("{", "[")):
        return "json"
    leading = [line for line in text.splitlines()[:5] if line.strip()]
    if len(leading) >= 2 and all(line.count(",") >= 1 for line in leading[:2]):
        return "csv"
    if filename.lower().endswith(".csv"):
        return "csv"
    return "txt"


def ingest(payload: bytes, filename: str, source_name: str) -> list[tuple[str, Occurrence]]:
    """Return (canonical_url, occurrence) discoveries from one uploaded file.

    Occurrence provenance records the concrete place each URL was observed:
    line/paragraph/page numbers for text-like formats, sheet/cell for XLSX and
    the JSON key path for structured documents.
    """
    return ingest_links(payload, filename, source_name).profiles


def ingest_links(payload: bytes, filename: str, source_name: str) -> IngestedLinks:
    """Discover profile and post URLs in one bounded parse of an uploaded file."""

    kind = sniff_kind(payload, filename)
    if kind == "txt":
        return _ingest_text(payload.decode("utf-8"), source_name)
    if kind == "json":
        return _ingest_json(payload.decode("utf-8"), source_name)
    if kind == "docx":
        return _ingest_docx(payload, source_name)
    if kind == "pdf":
        return _ingest_pdf(payload, source_name)
    if kind == "xlsx":
        return _ingest_xlsx(payload, source_name)
    return _ingest_csv(payload.decode("utf-8-sig"), source_name)


def _find(text: str, **place: Any) -> IngestedLinks:
    return IngestedLinks(
        profiles=[
            (url, replace(occurrence, **place))
            for url, occurrence in discover_in_text(text, source_type="file")
        ],
        posts=[
            (url, activity_urn, replace(occurrence, **place))
            for url, activity_urn, occurrence in discover_posts_in_text(
                text, source_type="file"
            )
        ],
    )


def _ingest_text(text: str, source_name: str) -> IngestedLinks:
    findings = IngestedLinks()
    for line_number, line in enumerate(text.splitlines(), start=1):
        findings.extend(_find(line, source_name=source_name, row=line_number))
    return findings


def _ingest_json(text: str, source_name: str) -> IngestedLinks:
    try:
        document = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return _ingest_text(text, source_name)
    findings = IngestedLinks()

    def walk(value: Any, path: str, depth: int) -> None:
        if depth > 24:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{path}.{key}" if path else str(key), depth + 1)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]", depth + 1)
        elif isinstance(value, str) and "linkedin.com/" in value.lower():
            findings.extend(_find(value, source_name=source_name, column=path or None))

    walk(document, "", 0)
    return findings


def _ingest_csv(text: str, source_name: str) -> IngestedLinks:
    findings = IngestedLinks()
    reader = csv.reader(io.StringIO(text))
    header: list[str] | None = None
    for row_number, row in enumerate(reader, start=1):
        if header is None:
            header = row
            continue
        for column_index, cell in enumerate(row):
            column = (
                header[column_index]
                if column_index < len(header) and header[column_index].strip()
                else f"column_{column_index + 1}"
            )
            findings.extend(
                _find(cell, source_name=source_name, row=row_number, column=column)
            )
    return findings


def _ingest_docx(payload: bytes, source_name: str) -> IngestedLinks:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            document = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise IngestError("The DOCX archive is unreadable.") from exc
    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError as exc:
        raise IngestError("The DOCX XML is malformed.") from exc
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    findings = IngestedLinks()
    for paragraph_number, paragraph in enumerate(root.iter(f"{namespace}p"), start=1):
        text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t"))
        if "linkedin.com/" not in text.lower():
            continue
        findings.extend(_find(text, source_name=source_name, row=paragraph_number))
    return findings


def _ingest_pdf(payload: bytes, source_name: str) -> IngestedLinks:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise IngestError("PDF ingestion is not available in this deployment.") from exc
    try:
        reader = PdfReader(io.BytesIO(payload))
        if reader.is_encrypted:
            raise IngestError("Encrypted PDFs are not supported.")
        pages = reader.pages[:2000]
    except IngestError:
        raise
    except Exception as exc:  # pypdf raises heterogeneous parse errors
        raise IngestError("The PDF could not be parsed.") from exc
    findings = IngestedLinks()
    for page_number, page in enumerate(pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # pypdf raises heterogeneous per-page errors
            logging.getLogger("profile_refinery_api").debug(
                "pdf_page_extraction_failed page=%s error_type=%s", page_number, type(exc).__name__
            )
            continue
        if "linkedin.com/" not in text.lower():
            continue
        findings.extend(_find(text, source_name=source_name, row=page_number))
    return findings


def _ingest_xlsx(payload: bytes, source_name: str) -> IngestedLinks:
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise IngestError("XLSX ingestion is not available in this deployment.") from exc
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    except Exception as exc:
        raise IngestError("The XLSX workbook could not be parsed.") from exc
    findings = IngestedLinks()
    try:
        for sheet in workbook.worksheets[:20]:
            for row_number, row in enumerate(sheet.iter_rows(max_row=10_000), start=1):
                for cell in row:
                    value = cell.value
                    if isinstance(value, str) and "linkedin.com/" in value.lower():
                        findings.extend(
                            _find(
                                value,
                                source_name=source_name,
                                sheet=sheet.title,
                                row=row_number,
                                column=cell.coordinate,
                            )
                        )
    finally:
        workbook.close()
    return findings


_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str | None) -> str:
    if not name:
        return "upload"
    base = name.replace("\\", "/").split("/")[-1]
    sanitized = _SANITIZE_RE.sub("_", base).strip("._") or "upload"
    return sanitized[:120]

from __future__ import annotations

import io
import json
import zipfile

import openpyxl
import pytest

from tross_linkedin_api.batch.discovery import dedupe, discover_in_text
from tross_linkedin_api.batch.ingest import IngestError, ingest, sanitize_filename, sniff_kind


def test_discovers_bare_and_qualified_urls_with_provenance() -> None:
    text = "John: linkedin.com/in/john-smith\nnext https://www.linkedin.com/in/jane-doe/?trk=x end"
    found = discover_in_text(text, source_type="pasted_text")
    urls = [url for url, _ in found]
    assert urls == [
        "https://www.linkedin.com/in/john-smith",
        "https://www.linkedin.com/in/jane-doe",
    ]
    assert found[0][1].source_type == "pasted_text"
    assert found[0][1].offset == 6
    assert found[1][1].original_text == "https://www.linkedin.com/in/jane-doe/?trk=x"


def test_ignores_non_profile_linkedin_urls() -> None:
    text = (
        "company https://www.linkedin.com/company/acme/ "
        "jobs https://www.linkedin.com/jobs/view/123/ "
        "feed https://www.linkedin.com/feed/ person linkedin.com/in/real-person"
    )
    found = discover_in_text(text, source_type="pasted_text")
    assert [url for url, _ in found] == ["https://www.linkedin.com/in/real-person"]


def test_invalid_slug_never_becomes_a_profile() -> None:
    found = discover_in_text("see linkedin.com/in/../../admin and linkedin.com/in/ok-person", "pasted_text")
    assert [url for url, _ in found] == ["https://www.linkedin.com/in/ok-person"]


def test_dedupe_merges_occurrences_and_keeps_first_provenance() -> None:
    text = "a linkedin.com/in/dup b www.linkedin.com/in/dup c https://www.linkedin.com/in/dup/"
    occurrences = discover_in_text(text, source_type="pasted_text")
    profiles = dedupe(occurrences)
    assert len(profiles) == 1
    assert len(profiles[0].occurrences) == 3
    assert profiles[0].canonical.canonical_url == "https://www.linkedin.com/in/dup"


def test_sniff_kind_uses_content_not_extension() -> None:
    assert sniff_kind(b"%PDF-1.7 fake", "not-a-pdf.txt") == "pdf"
    workbook = openpyxl.Workbook()
    buffer = io.BytesIO()
    workbook.save(buffer)
    assert sniff_kind(buffer.getvalue(), "not-excel.txt") == "xlsx"
    assert sniff_kind(b"plain text https://www.linkedin.com/in/x", "a.txt") == "txt"
    assert sniff_kind(b'{"a": ["https://www.linkedin.com/in/x"]}', "b.txt") == "json"


def test_txt_ingestion_records_line_numbers() -> None:
    payload = b"intro\ncontact linkedin.com/in/line-two\nlinkedin.com/in/line-three"
    found = ingest(payload, "people.txt", "people.txt")
    rows = {occ.row for _, occ in found}
    assert rows == {2, 3}


def test_csv_ingestion_records_row_and_column() -> None:
    payload = b"name,linkedin\nAnn,https://www.linkedin.com/in/ann-profile/\nBob,linkedin.com/in/bob-profile"
    found = ingest(payload, "people.csv", "people.csv")
    assert len(found) == 2
    assert found[0][1].column == "linkedin"
    assert found[0][1].row == 2


def test_xlsx_ingestion_records_sheet_and_cell() -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Candidates"
    sheet["B2"] = "https://www.linkedin.com/in/sheet-person/"
    buffer = io.BytesIO()
    workbook.save(buffer)
    found = ingest(buffer.getvalue(), "people.xlsx", "people.xlsx")
    assert len(found) == 1
    occurrence = found[0][1]
    assert occurrence.sheet == "Candidates"
    assert occurrence.row == 2
    assert occurrence.column == "B2"


def test_docx_ingestion_records_paragraph() -> None:
    document = (
        '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>first</w:t></w:r></w:p>'
        "<w:p><w:r><w:t>see https://www.linkedin.com/in/docx-person</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document)
    found = ingest(buffer.getvalue(), "cv.docx", "cv.docx")
    assert len(found) == 1
    assert found[0][1].row == 2


def test_pdf_ingestion_records_page() -> None:
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.add_metadata({})
    writer.write(buffer)
    assert sniff_kind(buffer.getvalue(), "doc.pdf") == "pdf"


def test_json_ingestion_records_key_path() -> None:
    payload = json.dumps({"candidates": [{"url": "https://www.linkedin.com/in/json-person/"}]})
    found = ingest(payload.encode(), "data.json", "data.json")
    assert len(found) == 1
    assert found[0][1].column == "candidates[0].url"


def test_malformed_and_unsupported_files_are_explicit_errors() -> None:
    try:
        ingest(b"\x00\x01\x02binary", "blob.bin", "blob.bin")
    except IngestError:
        pass
    else:
        raise AssertionError("binary blob must raise IngestError")


def test_filenames_are_sanitized() -> None:
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("weird name?.xlsx") == "weird_name_.xlsx"
    assert sanitize_filename(None) == "upload"

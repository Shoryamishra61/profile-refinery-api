from __future__ import annotations

import csv
import io

import openpyxl

from tross_linkedin_api.batch.exports import FLAT_COLUMNS, csv_bytes, xlsx_bytes


def test_csv_headers_are_deterministic_and_formula_cells_are_text() -> None:
    row = {column: None for column in FLAT_COLUMNS}
    row.update(
        {
            "linkedin_url": "https://www.linkedin.com/in/formula-safe",
            "status": "SUCCEEDED",
            "name": "=WEBSERVICE(\"https://invalid.example\")",
            "headline": "+SUM(1,1)",
            "experience_count": 2,
            "education_count": 1,
        }
    )
    payload = csv_bytes([row])
    parsed = list(csv.DictReader(io.StringIO(payload.decode("utf-8"))))

    assert payload == csv_bytes([row])
    assert list(parsed[0]) == FLAT_COLUMNS
    assert parsed[0]["name"].startswith("'=")
    assert parsed[0]["headline"].startswith("'+")
    assert parsed[0]["experience_count"] == "2"
    assert parsed[0]["education_count"] == "1"


def test_xlsx_formula_like_values_are_stored_as_plain_text() -> None:
    row = {column: None for column in FLAT_COLUMNS}
    row.update(
        {
            "linkedin_url": "https://www.linkedin.com/in/formula-safe",
            "status": "SUCCEEDED",
            "name": "@SUM(1,1)",
        }
    )
    workbook = openpyxl.load_workbook(io.BytesIO(xlsx_bytes([row])))
    sheet = workbook["profiles"]
    name_cell = sheet.cell(row=2, column=FLAT_COLUMNS.index("name") + 1)
    assert name_cell.value == "'@SUM(1,1)"
    assert name_cell.data_type == "s"

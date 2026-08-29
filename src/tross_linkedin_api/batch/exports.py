from __future__ import annotations

import csv
import io
import json
from typing import Any

FLAT_COLUMNS = [
    "linkedin_url",
    "status",
    "error_code",
    "name",
    "headline",
    "location",
    "about",
    "current_title",
    "current_company",
    "company_url",
    "experience_count",
    "education_count",
    "skills",
    "certifications",
    "languages",
    "profile_image_url",
    "retrieved_at",
]


def flatten(response: dict[str, Any] | None, status: str, error_code: str | None) -> dict[str, Any]:
    if not response:
        return {"status": status, "error_code": error_code}
    profile = response.get("profile", {})

    def value(field_name: str, key: str = "value") -> Any:
        entry = profile.get(field_name) or {}
        return entry.get(key) if isinstance(entry, dict) else None

    raw_experience = value("experience")
    experience: list[dict[str, Any]] = raw_experience if isinstance(raw_experience, list) else []
    current = next((item for item in experience if item.get("is_current")), None)

    def joined(items: list[dict[str, Any]], key: str = "name") -> str:
        return "; ".join(str(item.get(key)) for item in items if item.get(key))

    image = value("profile_image") or {}
    return {
        "linkedin_url": response.get("canonical_url"),
        "status": status,
        "error_code": None,
        "name": value("name"),
        "headline": value("headline"),
        "location": value("location"),
        "about": value("about"),
        "current_title": (current or {}).get("title"),
        "current_company": (current or {}).get("company_name"),
        "company_url": (current or {}).get("company_url"),
        "experience_count": len(experience),
        "education_count": len(value("education") or []),
        "skills": joined(value("skills") or []),
        "certifications": joined(value("certifications") or []),
        "languages": joined(value("languages") or []),
        "profile_image_url": image.get("url"),
        "retrieved_at": response.get("observed_at"),
    }


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FLAT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def _spreadsheet_safe(record: dict[str, Any]) -> dict[str, Any]:
    """Deterministic scalar rendering for structured values (date dicts)."""
    safe: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, dict):
            parts = [str(value[k]) for k in ("year", "month", "day") if k in value]
            safe[key] = "-".join(parts) if parts else json.dumps(value, sort_keys=True)
        else:
            safe[key] = value
    return safe


def xlsx_bytes(
    rows: list[dict[str, Any]],
    sections_by_url: dict[str, dict[str, list[dict[str, Any]]]] | None = None,
    provenance_by_url: dict[str, list[dict[str, Any]]] | None = None,
    failures: list[dict[str, Any]] | None = None,
) -> bytes:
    """Multi-sheet workbook (governing spec §10.8).

    Sheets: profiles / experience / education / skills / certifications /
    languages / provenance / failures. Structure is deterministic: fixed
    sheet order, fixed columns, stored rows only (never a LinkedIn fetch).
    """
    import openpyxl

    sections_by_url = sections_by_url or {}
    provenance_by_url = provenance_by_url or {}
    failures = failures or []
    workbook = openpyxl.Workbook()
    default_sheet = workbook.active
    if default_sheet is not None:
        workbook.remove(default_sheet)  # write() creates every sheet explicitly

    def write(title: str, columns: list[str], records: list[dict[str, Any]]) -> None:
        sheet = workbook.create_sheet(title)
        sheet.append(columns)
        for record in records:
            sheet.append([record.get(column) for column in columns])

    write("profiles", FLAT_COLUMNS, rows)
    section_columns = {
        "experience": [
            "linkedin_url",
            "title",
            "company_name",
            "company_url",
            "location",
            "start_date",
            "end_date",
            "is_current",
        ],
        "education": [
            "linkedin_url",
            "school_name",
            "degree_name",
            "field_of_study",
            "start_date",
            "end_date",
        ],
        "skills": ["linkedin_url", "name"],
        "certifications": [
            "linkedin_url",
            "name",
            "authority",
            "license_number",
            "start_date",
            "end_date",
        ],
        "languages": ["linkedin_url", "name", "proficiency"],
    }
    for sheet_name, columns in section_columns.items():
        records: list[dict[str, Any]] = []
        for url, sections in sections_by_url.items():
            for item in sections.get(sheet_name, []) or []:
                record = {"linkedin_url": url, **item}
                records.append(_spreadsheet_safe(record))
        write(sheet_name, columns, records)
    write(
        "provenance",
        [
            "linkedin_url",
            "source_type",
            "source_name",
            "sheet",
            "row",
            "column",
            "offset",
            "original_text",
        ],
        [
            {"linkedin_url": url, **occurrence}
            for url, occurrences in provenance_by_url.items()
            for occurrence in occurrences
        ],
    )
    write("failures", ["linkedin_url", "status", "error_code", "error_detail"], failures)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def json_document(batch_summary: dict[str, Any], rows: list[dict[str, Any]]) -> bytes:
    return json.dumps(
        {"batch": batch_summary, "profiles": rows}, ensure_ascii=False, indent=2
    ).encode("utf-8")


def report_hash(report: dict[str, Any], generator_version: str) -> str:
    """Stable hash for the deterministic report (same input + version ⇒ same)."""
    import hashlib

    payload = json.dumps(
        {"generator_version": generator_version, "report": report},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def field_value(profile: dict[str, Any], name: str) -> Any:
    entry = profile.get(name) or {}
    if isinstance(entry, dict):
        return entry.get("value")
    return None


def profile_report(response: dict[str, Any]) -> dict[str, Any]:
    """Deterministic, fully grounded summary of one extracted profile.

    Every value is copied from the extracted record; absent evidence yields
    null rather than prose. No external model is involved.
    """
    profile = response.get("profile", {})
    experience = field_value(profile, "experience") or []
    current = next((item for item in experience if item.get("is_current")), None)
    return {
        "current_position": (
            {"title": current.get("title"), "company": current.get("company_name")}
            if current
            else None
        ),
        "career_timeline": [
            {
                "title": item.get("title"),
                "company": item.get("company_name"),
                "start_date": item.get("start_date"),
                "end_date": item.get("end_date"),
            }
            for item in experience
        ],
        "education": [
            {
                "institution": item.get("school_name"),
                "degree": item.get("degree_name"),
                "field_of_study": item.get("field_of_study"),
            }
            for item in field_value(profile, "education") or []
        ],
        "skills": [item.get("name") for item in field_value(profile, "skills") or []],
        "certifications": [
            item.get("name") for item in field_value(profile, "certifications") or []
        ],
        "languages": [item.get("name") for item in field_value(profile, "languages") or []],
        "location": field_value(profile, "location"),
        "retrieved_at": response.get("observed_at"),
    }


def _top(values: list[str], limit: int) -> list[dict[str, Any]]:
    from collections import Counter

    return [{"value": value, "count": count} for value, count in Counter(values).most_common(limit)]


def aggregate(batch: Any) -> dict[str, Any]:
    """Evidence-backed batch aggregates derived only from extracted records."""
    titles: list[str] = []
    companies: list[str] = []
    skills: list[str] = []
    locations: list[str] = []
    schools: list[str] = []
    experience_counts: list[int] = []
    succeeded = 0
    for job in getattr(batch, "jobs", []):
        if job.response is None:
            continue
        succeeded += 1
        response = job.response.model_dump(mode="json")
        profile = response.get("profile", {})
        experience = field_value(profile, "experience") or []
        experience_counts.append(len(experience))
        current = next((item for item in experience if item.get("is_current")), None)
        if current and current.get("title"):
            titles.append(current["title"])
        if current and current.get("company_name"):
            companies.append(current["company_name"])
        location = field_value(profile, "location")
        if location:
            locations.append(location)
        for item in field_value(profile, "skills") or []:
            if item.get("name"):
                skills.append(item["name"])
        for item in field_value(profile, "education") or []:
            if item.get("school_name"):
                schools.append(item["school_name"])
    total = len(getattr(batch, "jobs", []))
    report: dict[str, Any] = {
        "profiles_processed": total,
        "successful_extraction_ratio": round(succeeded / total, 3) if total else 0.0,
    }
    if titles:
        report["common_current_titles"] = _top(titles, 10)
    if companies:
        report["common_current_companies"] = _top(companies, 10)
    if skills:
        report["common_skills"] = _top(skills, 15)
    if locations:
        report["locations"] = _top(locations, 10)
    if schools:
        report["education_institutions"] = _top(schools, 10)
    if experience_counts:
        report["experience_distribution"] = {
            "min": min(experience_counts),
            "max": max(experience_counts),
            "mean": round(sum(experience_counts) / len(experience_counts), 2),
        }
    return report

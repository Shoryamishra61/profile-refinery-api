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


def xlsx_bytes(rows: list[dict[str, Any]]) -> bytes:
    import openpyxl

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    if sheet is None:  # pragma: no cover - a new workbook always has an active sheet
        sheet = workbook.create_sheet("profiles")
    sheet.title = "profiles"
    sheet.append(FLAT_COLUMNS)
    for row in rows:
        sheet.append([row.get(column) for column in FLAT_COLUMNS])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def json_document(batch_summary: dict[str, Any], rows: list[dict[str, Any]]) -> bytes:
    return json.dumps(
        {"batch": batch_summary, "profiles": rows}, ensure_ascii=False, indent=2
    ).encode("utf-8")


def _field(profile: dict[str, Any], name: str) -> Any:
    entry = (profile.get(name) or {})
    if isinstance(entry, dict):
        return entry.get("value")
    return None


def profile_report(response: dict[str, Any]) -> dict[str, Any]:
    """Deterministic, fully grounded summary of one extracted profile.

    Every value is copied from the extracted record; absent evidence yields
    null rather than prose. No external model is involved.
    """
    profile = response.get("profile", {})
    experience = _field(profile, "experience") or []
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
            for item in _field(profile, "education") or []
        ],
        "skills": [item.get("name") for item in _field(profile, "skills") or []],
        "certifications": [item.get("name") for item in _field(profile, "certifications") or []],
        "languages": [item.get("name") for item in _field(profile, "languages") or []],
        "location": _field(profile, "location"),
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
        experience = _field(profile, "experience") or []
        experience_counts.append(len(experience))
        current = next((item for item in experience if item.get("is_current")), None)
        if current and current.get("title"):
            titles.append(current["title"])
        if current and current.get("company_name"):
            companies.append(current["company_name"])
        location = _field(profile, "location")
        if location:
            locations.append(location)
        for item in _field(profile, "skills") or []:
            if item.get("name"):
                skills.append(item["name"])
        for item in _field(profile, "education") or []:
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

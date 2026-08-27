from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_FILES = [
    ROOT / "pyproject.toml",
    ROOT / "Dockerfile",
    *sorted((ROOT / "src").rglob("*")),
]
TEXT_SUFFIXES = {".py", ".toml", ".yaml", ".yml", ".json", ".md", ".example", ""}
BROWSER_TERMS = ("selenium", "playwright", "puppeteer", "chromium", "chromedriver")
SECRET_PATTERNS = {
    "LinkedIn li_at cookie": re.compile(r"(?i)li_at\s*[=:]\s*['\"][A-Za-z0-9_-]{20,}"),
    "LinkedIn JSESSIONID": re.compile(r"(?i)JSESSIONID\s*[=:]\s*['\"]ajax:[A-Za-z0-9_-]{8,}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
}


def main() -> None:
    failures: list[str] = []
    for path in PRODUCTION_FILES:
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lowered = text.lower()
        for term in BROWSER_TERMS:
            if term in lowered:
                failures.append(
                    f"browser dependency/reference '{term}' in {path.relative_to(ROOT)}"
                )

    scan_roots = [ROOT / "src", ROOT / "config", ROOT / "schemas", ROOT / ".github", ROOT]
    scanned: set[Path] = set()
    for scan_root in scan_roots:
        paths = [scan_root] if scan_root.is_file() else scan_root.rglob("*")
        for path in paths:
            if (
                path in scanned
                or not path.is_file()
                or {"11_ARCHIVE_ORIGINALS", ".git", ".venv", "__pycache__"}.intersection(path.parts)
            ):
                continue
            scanned.add(path)
            if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
                "Dockerfile",
                ".env.example",
            }:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for name, pattern in SECRET_PATTERNS.items():
                if pattern.search(text):
                    failures.append(f"possible {name} in {path.relative_to(ROOT)}")

    if failures:
        print("SECURITY AUDIT FAILED")
        print("\n".join(f"- {failure}" for failure in sorted(set(failures))))
        raise SystemExit(1)
    print(
        f"SECURITY AUDIT PASSED: {len(scanned)} files scanned; production browser dependencies=0; secret patterns=0"
    )


if __name__ == "__main__":
    sys.exit(main())

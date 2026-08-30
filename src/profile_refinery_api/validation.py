from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError


class SchemaValidator:
    def __init__(self, schema_path: Path) -> None:
        if not schema_path.is_file():
            raise FileNotFoundError(f"response schema is required: {schema_path}")
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except (OSError, json.JSONDecodeError, SchemaError) as exc:
            raise ValueError(f"invalid response schema: {schema_path}") from exc
        self._validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def validate(self, value: dict[str, Any]) -> None:
        errors = sorted(
            self._validator.iter_errors(value), key=lambda error: list(error.absolute_path)
        )
        if errors:
            first: ValidationError = errors[0]
            path = ".".join(str(part) for part in first.absolute_path) or "$"
            raise ValueError(f"response schema violation at {path}: {first.message}")

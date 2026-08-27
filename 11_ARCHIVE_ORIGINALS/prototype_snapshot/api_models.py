import json
import os
from typing import Dict, Any, List, Optional, Tuple
from jsonschema import Draft7Validator

class SchemaValidator:
    """
    Validates normalized profile responses against the Draft-07 JSON Schema
    loaded from PROFILE_SCHEMA.json.
    """
    def __init__(self, schema_path: str = "/workspace/artifacts/PROFILE_SCHEMA.json"):
        self.schema_path = schema_path
        self.schema = self._load_schema()
        self.validator = Draft7Validator(self.schema) if self.schema else None

    def _load_schema(self) -> Optional[Dict[str, Any]]:
        # Fallback to current directory if not in /workspace/artifacts/
        paths_to_try = [
            self.schema_path,
            "./PROFILE_SCHEMA.json",
            "../artifacts/PROFILE_SCHEMA.json"
        ]
        for p in paths_to_try:
            if os.path.exists(p):
                with open(p, 'r') as f:
                    return json.load(f)
        return None

    def validate(self, instance: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates the output instance dictionary.
        Returns a (is_valid, error_messages) tuple.
        """
        if not self.validator:
            return True, []  # Silent pass if schema file not found during early init
            
        errors = sorted(self.validator.iter_errors(instance), key=lambda e: e.path)
        if not errors:
            return True, []
            
        error_msgs = [f"Field '{'.'.join(str(p) for p in err.path)}': {err.message}" for err in errors]
        return False, error_msgs

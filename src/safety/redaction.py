"""PII and secret redaction for safe logging and storage."""

import re
from typing import Any, Dict, List


class Redactor:
    """Redact sensitive data from logs and artifacts."""

    def __init__(self, patterns: List[str]):
        """
        Initialize with PII patterns.

        Args:
            patterns: List of regex patterns to redact
        """
        self.patterns = [
            re.compile(p, re.IGNORECASE)
            for p in patterns
        ]

        # Additional secret patterns
        self.secret_patterns = [
            re.compile(
                r'(api[_-]?key|token|secret|password)\s*[:=]\s*["\']?([^"\'\s]+)',
                re.IGNORECASE,
            ),
            re.compile(
                r'Bearer\s+[A-Za-z0-9\-._~+/]+=*',
                re.IGNORECASE,
            ),
            re.compile(
                r'sk-[A-Za-z0-9]{20,}',
                re.IGNORECASE,
            ),  # API keys
        ]

    def redact(self, data: Any) -> Any:
        """
        Recursively redact sensitive data.

        Args:
            data: Data to redact (str, dict, list, or primitive)

        Returns:
            Redacted copy of data
        """
        if isinstance(data, str):
            return self._redact_string(data)

        elif isinstance(data, dict):
            return {
                key: self.redact(value)
                for key, value in data.items()
            }

        elif isinstance(data, list):
            return [
                self.redact(item)
                for item in data
            ]

        else:
            return data

    def _redact_string(self, text: str) -> str:
        """Redact sensitive patterns from string."""
        result = text

        # Redact PII patterns
        for pattern in self.patterns:
            result = pattern.sub("[REDACTED]", result)

        # Redact secrets
        for pattern in self.secret_patterns:
            result = pattern.sub(r"\1: [REDACTED]", result)

        return result

    def redact_artifact(
        self,
        artifact_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Redact artifact before saving.

        Preserves structure but removes sensitive values.
        """
        redacted = artifact_dict.copy()

        # Redact step values that might contain PII
        if "steps" in redacted:
            for step in redacted["steps"]:
                if "value" in step and step["value"]:
                    step["value"] = self._redact_string(
                        step["value"]
                    )

        return redacted
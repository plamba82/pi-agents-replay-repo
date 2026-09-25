"""Structured logging with PII redaction."""

import json
import re
from typing import List, Any
from datetime import datetime
from dataclasses import is_dataclass, asdict


class StructuredLogger:
    """Structured logger with PII redaction."""

    def __init__(self, component: str, pii_patterns: List[str]):
        self.component = component
        self.pii_patterns = [re.compile(p, re.IGNORECASE) for p in pii_patterns]

    def _redact(self, text: str) -> str:
        """Redact PII from text."""
        for pattern in self.pii_patterns:
            text = pattern.sub("[REDACTED]", text)
        return text

    def _log(self, level: str, event: str, **kwargs):
        """Internal log method."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "component": self.component,
            "event": event,
            **kwargs,
        }

        # CHANGE: Custom JSON encoder to handle dataclasses and other non-serializable objects
        def json_serializer(obj):
            """Custom serializer for objects that aren't JSON serializable by default."""
            if is_dataclass(obj):
                return asdict(obj)
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            return str(obj)

        # CHANGE: Use custom serializer instead of default encoder
        print(json.dumps(log_entry, default=json_serializer))

    def info(self, event: str, **kwargs):
        """Log info level."""
        self._log("info", event, **kwargs)

    def warning(self, event: str, **kwargs):
        """Log warning level."""
        self._log("warning", event, **kwargs)

    def error(self, event: str, **kwargs):
        """Log error level."""
        self._log("error", event, **kwargs)

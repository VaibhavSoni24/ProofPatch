"""Structured logging setup with automated secret redaction."""

import logging
import re
import sys
from typing import List

# Patterns matching sensitive keys/tokens
RE_SECRETS = [
    re.compile(r"(?i)(api[-_]?key|secret|token|password|bearer\s+)[:= ]+([a-zA-Z0-9_\-\.]{8,})"),
    re.compile(r"Bearer\s+([a-zA-Z0-9_\-\.]{8,})"),
    re.compile(r"(nebius-[a-zA-Z0-9]{16,})"),
    re.compile(r"(tvly-[a-zA-Z0-9]{16,})"),
]


class SecretScrubbingFormatter(logging.Formatter):
    """Custom logging formatter that scrubs API keys and bearer tokens."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        scrubbed = original
        for pattern in RE_SECRETS:
            scrubbed = pattern.sub(r"\1: [REDACTED]", scrubbed)
        return scrubbed


def redact_secrets(text: str, custom_secrets: List[str] = None) -> str:
    """Scrub known secrets and secret patterns from text strings."""
    if not text:
        return ""
    result = text
    if custom_secrets:
        for secret in custom_secrets:
            if secret and len(secret) >= 4:
                result = result.replace(secret, "[REDACTED]")

    for pattern in RE_SECRETS:
        result = pattern.sub(r"\1: [REDACTED]", result)
    return result


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure root and application logger."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger("proofpatch")
    logger.setLevel(level)

    # Avoid duplicate handlers on reload
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = SecretScrubbingFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()

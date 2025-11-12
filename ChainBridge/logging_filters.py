import logging
import re

# Redaction patterns - add more patterns if you need to redact other secrets
SENSITIVE_PATTERNS = [
    re.compile(r'(API_KEY\s*=\s*["\']?)[A-Za-z0-9+/=._-]{8,}([\'" ]?)', re.IGNORECASE),
    re.compile(
        r'(API_SECRET\s*=\s*["\']?)[A-Za-z0-9+/=._-]{8,}([\'" ]?)', re.IGNORECASE
    ),
    re.compile(
        r'(api_key["\']?\s*[:=]\s*["\']?)[A-Za-z0-9+/=._-]{8,}([\'" ]?)', re.IGNORECASE
    ),
    re.compile(
        r'(api_secret["\']?\s*[:=]\s*["\']?)[A-Za-z0-9+/=._-]{8,}([\'" ]?)',
        re.IGNORECASE,
    ),
]


class RedactFilter(logging.Filter):
    """Logging filter that redacts common secret patterns from messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            for pat in SENSITIVE_PATTERNS:
                msg = pat.sub(r"\1[REDACTED]\2", msg)
            # For safety, also redact long base64-like tokens anywhere
            msg = re.sub(r"([A-Za-z0-9+/]{20,}={0,2})", "[REDACTED]", msg)
            # Replace the message in the record
            record.msg = msg
            record.args = ()
        except Exception:
            pass
        return True

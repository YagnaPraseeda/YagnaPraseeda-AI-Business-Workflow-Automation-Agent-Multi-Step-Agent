import re
import time

from groq import Groq, RateLimitError

_MAX_RETRIES = 4
_RETRY_BASE_WAIT = 2.0


def groq_create_with_retry(client: Groq, **kwargs):
    """Call client.chat.completions.create with exponential backoff on 429 rate limits."""
    for attempt in range(_MAX_RETRIES):
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            if attempt == _MAX_RETRIES - 1:
                raise
            body = getattr(exc, "body", {}) or {}
            msg = (
                body.get("error", {}).get("message", "")
                if isinstance(body, dict)
                else str(exc)
            )
            m = re.search(r"try again in (\d+(?:\.\d+)?)(ms|s)", msg)
            if m:
                val, unit = float(m.group(1)), m.group(2)
                suggested = val / 1000 if unit == "ms" else val
            else:
                suggested = 0
            wait = max(suggested + 1, _RETRY_BASE_WAIT * (2**attempt))
            time.sleep(wait)

import re
import time

from groq import Groq, RateLimitError

_MAX_RETRIES = 4
_RETRY_BASE_WAIT = 2.0


def _parse_wait_seconds(msg: str) -> float:
    """Extract the suggested wait in seconds from a Groq rate-limit message.

    Handles: '10m2.208s', '240ms', '1.5s', '30s'
    """
    # Minutes + seconds: "10m2.208s"
    m = re.search(r"try again in (\d+)m(\d+(?:\.\d+)?)s", msg)
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    # Plain seconds or milliseconds: "240ms" / "1.5s"
    m = re.search(r"try again in (\d+(?:\.\d+)?)(ms|s)", msg)
    if m:
        val, unit = float(m.group(1)), m.group(2)
        return val / 1000 if unit == "ms" else val
    return 0.0


def groq_create_with_retry(client: Groq, **kwargs):
    """Call client.chat.completions.create with exponential backoff on 429 rate limits.

    Daily (TPD) quota errors are re-raised immediately — no retry will help.
    Per-minute (TPM) errors are retried up to _MAX_RETRIES times.
    """
    for attempt in range(_MAX_RETRIES):
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            body = getattr(exc, "body", {}) or {}
            msg = (
                body.get("error", {}).get("message", "")
                if isinstance(body, dict)
                else str(exc)
            )
            # Daily quota exhausted — retrying won't help until reset
            if "tokens per day" in msg or "(TPD)" in msg:
                raise RateLimitError(
                    message=(
                        "Groq daily token limit reached. "
                        "Please wait until your quota resets (usually midnight UTC) "
                        f"or upgrade your Groq plan. Details: {msg}"
                    ),
                    response=exc.response,
                    body=body,
                ) from exc
            if attempt == _MAX_RETRIES - 1:
                raise
            suggested = _parse_wait_seconds(msg)
            wait = max(suggested + 1, _RETRY_BASE_WAIT * (2**attempt))
            time.sleep(wait)

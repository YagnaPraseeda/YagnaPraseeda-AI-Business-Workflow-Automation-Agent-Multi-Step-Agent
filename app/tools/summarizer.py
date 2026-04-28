import os
import re
import time

from groq import Groq, RateLimitError

from app.tools import context as ctx
from app.tools.registry import registry

_MAX_RETRIES = 4
_RETRY_BASE_WAIT = 2.0


def _groq_create_with_retry(client: Groq, **kwargs):
    for attempt in range(_MAX_RETRIES):
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            if attempt == _MAX_RETRIES - 1:
                raise
            body = getattr(exc, "body", {}) or {}
            msg = (body.get("error", {}).get("message", "") if isinstance(body, dict) else str(exc))
            m = re.search(r"try again in (\d+(?:\.\d+)?)(ms|s)", msg)
            if m:
                val, unit = float(m.group(1)), m.group(2)
                suggested = val / 1000 if unit == "ms" else val
            else:
                suggested = 0
            wait = max(suggested + 1, _RETRY_BASE_WAIT * (2 ** attempt))
            time.sleep(wait)

_MAX_INPUT_CHARS = 8_000


@registry.register(
    name="SummarizationTool",
    description=(
        "Use AI to summarize or extract insights from the loaded file content. "
        "Reads the file content automatically — do NOT pass text as an argument. "
        "Call this after FileReaderTool (and optionally after DataAnalyzerTool)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "instruction": {
                "type": "string",
                "description": (
                    "What to do with the content, e.g. 'summarize key findings', "
                    "'extract the 5 most important insights', "
                    "'identify trends and anomalies', 'extract key risks'"
                ),
            }
        },
        "required": ["instruction"],
    },
)
def summarize_text(instruction: str) -> str:
    file_content = ctx.get("file_content", "")
    analysis = ctx.get("analysis_result", "")

    if not file_content and not analysis:
        return "Error: No content available. Call FileReaderTool first."

    combined = ""
    if analysis:
        combined += f"=== Data Analysis ===\n{analysis}\n\n"
    if file_content:
        combined += f"=== File Content ===\n{file_content}"

    truncated = combined[:_MAX_INPUT_CHARS]
    if len(combined) > _MAX_INPUT_CHARS:
        truncated += f"\n... (truncated to {_MAX_INPUT_CHARS} chars)"

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = _groq_create_with_retry(
        client,
        model=os.environ.get("MODEL", "llama-3.3-70b-versatile"),
        messages=[
            {"role": "user", "content": f"{instruction}\n\nContent:\n{truncated}"}
        ],
    )
    result = response.choices[0].message.content
    ctx.set("summary", result)
    return result

import os

from groq import Groq

from app.tools.registry import registry

_MAX_INPUT_CHARS = 8_000


@registry.register(
    name="SummarizationTool",
    description=(
        "Use AI to summarize or extract insights from a block of text or data. "
        "Pass raw file content or analysis output here to get a concise, "
        "human-readable summary."
    ),
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text or data content to summarize",
            },
            "instruction": {
                "type": "string",
                "description": (
                    "What to do with the text, e.g. 'summarize key findings', "
                    "'extract the 5 most important insights', "
                    "'identify trends and anomalies'"
                ),
            },
        },
        "required": ["text", "instruction"],
    },
)
def summarize_text(text: str, instruction: str) -> str:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    truncated = text[:_MAX_INPUT_CHARS]
    if len(text) > _MAX_INPUT_CHARS:
        truncated += f"\n... (input truncated to {_MAX_INPUT_CHARS} chars)"

    response = client.chat.completions.create(
        model=os.environ.get("MODEL", "llama-3.3-70b-versatile"),
        messages=[
            {"role": "user", "content": f"{instruction}\n\nContent:\n{truncated}"}
        ],
    )
    return response.choices[0].message.content

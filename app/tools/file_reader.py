import csv
from pathlib import Path

from app.tools.registry import registry

_SUPPORTED = {".csv", ".txt", ".md", ".json", ".log"}


@registry.register(
    name="FileReaderTool",
    description=(
        "Load the contents of a CSV or plain-text file and return it as a string. "
        "Always use this as the first step whenever a file path is referenced."
    ),
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the file to read",
            }
        },
        "required": ["file_path"],
    },
)
def read_file(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        return f"Error: File '{file_path}' not found. Make sure the file was uploaded."

    if path.stat().st_size == 0:
        return f"Error: File '{file_path}' is empty."

    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED:
        return (
            f"Error: Unsupported file type '{suffix}'. "
            f"Supported types: {', '.join(sorted(_SUPPORTED))}"
        )

    if suffix == ".csv":
        rows: list[str] = []
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    rows.append(", ".join(row))
                    if i >= 99:
                        rows.append("... (truncated — showing first 100 rows)")
                        break
        except UnicodeDecodeError:
            return f"Error: Could not decode '{file_path}'. File may use an unsupported encoding."
        return "\n".join(rows)

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Error: Could not decode '{file_path}'. File may use an unsupported encoding."

    if len(content) > 10_000:
        content = content[:10_000] + "\n... (truncated at 10,000 chars)"
    return content

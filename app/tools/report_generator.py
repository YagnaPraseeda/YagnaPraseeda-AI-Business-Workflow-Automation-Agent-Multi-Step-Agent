import os
from datetime import datetime
from pathlib import Path

from app.tools.registry import registry


@registry.register(
    name="ReportGeneratorTool",
    description=(
        "Compile analysis results into a structured Markdown report and save it to disk. "
        "Always call this as the final step to produce the deliverable for the user."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Report title",
            },
            "sections": {
                "type": "array",
                "description": "Ordered list of report sections",
                "items": {
                    "type": "object",
                    "properties": {
                        "heading": {"type": "string", "description": "Section heading"},
                        "content": {"type": "string", "description": "Section body text"},
                    },
                    "required": ["heading", "content"],
                },
            },
        },
        "required": ["title", "sections"],
    },
)
def generate_report(title: str, sections: list[dict]) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        f"# {title}",
        f"*Generated: {timestamp}*",
        "",
    ]

    for section in sections:
        lines.append(f"## {section['heading']}")
        lines.append(section["content"])
        lines.append("")

    report_md = "\n".join(lines)

    reports_dir = Path(os.environ.get("REPORTS_DIR", "reports"))
    reports_dir.mkdir(parents=True, exist_ok=True)
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    (reports_dir / filename).write_text(report_md, encoding="utf-8")

    return f"Report saved to '{reports_dir / filename}'\n\n{report_md}"

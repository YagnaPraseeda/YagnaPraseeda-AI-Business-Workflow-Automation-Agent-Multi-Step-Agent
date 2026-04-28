import os
from datetime import datetime
from pathlib import Path

from app.tools import context as ctx
from app.tools.registry import registry


@registry.register(
    name="ReportGeneratorTool",
    description=(
        "Compile all findings into a structured Markdown report and save it to disk. "
        "Reads the summary and analysis automatically — use this as the final step."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Report title, e.g. 'System Design Analysis Report'",
            }
        },
        "required": ["title"],
    },
)
def generate_report(title: str) -> str:
    summary = ctx.get("summary", "")
    analysis = ctx.get("analysis_result", "")
    file_name = ctx.get("file_name", "unknown file")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not summary and not analysis:
        return "Error: No content to report. Run SummarizationTool or DataAnalyzerTool first."

    lines: list[str] = [
        f"# {title}",
        f"*Generated: {timestamp} | Source: {file_name}*",
        "",
    ]

    if analysis:
        lines += ["## Data Analysis", analysis, ""]

    if summary:
        lines += ["## Summary & Insights", summary, ""]

    report_md = "\n".join(lines)

    reports_dir = Path(os.environ.get("REPORTS_DIR", "reports"))
    reports_dir.mkdir(parents=True, exist_ok=True)
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    (reports_dir / filename).write_text(report_md, encoding="utf-8")

    return f"Report saved to '{reports_dir / filename}'\n\n{report_md}"

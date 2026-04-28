from pathlib import Path

import pandas as pd

from app.tools import context as ctx
from app.tools.registry import registry


@registry.register(
    name="DataAnalyzerTool",
    description=(
        "Run statistical analysis on the previously loaded CSV file. "
        "Only use this after FileReaderTool confirmed the file is a CSV. "
        "Never use this on .txt, .md, .json, or .log files."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "What to analyze, e.g. 'summary statistics', "
                    "'correlation matrix', 'top 5 rows', 'missing values'"
                ),
            }
        },
        "required": ["query"],
    },
)
def analyze_data(query: str) -> str:
    file_path = ctx.get("file_path")
    file_ext = ctx.get("file_ext")

    if not file_path:
        return "Error: No file loaded. Call FileReaderTool first."

    if file_ext != ".csv":
        return (
            f"Error: DataAnalyzerTool only supports CSV files. "
            f"The loaded file is a '{file_ext}' file. Use SummarizationTool instead."
        )

    path = Path(file_path)
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return f"Error reading CSV: {exc}"

    if df.empty:
        return "Error: The CSV file is empty or has no data rows."

    parts: list[str] = []
    parts.append(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    parts.append(f"Columns: {', '.join(df.columns.tolist())}")
    parts.append(f"\nData types:\n{df.dtypes.to_string()}")
    parts.append(f"\nMissing values:\n{df.isnull().sum().to_string()}")

    numeric = df.select_dtypes(include="number")
    if not numeric.empty:
        parts.append(f"\nDescriptive statistics:\n{numeric.describe().to_string()}")

    q = query.lower()

    if "correlation" in q and len(numeric.columns) >= 2:
        parts.append(f"\nCorrelation matrix:\n{numeric.corr().round(3).to_string()}")

    if any(kw in q for kw in ("top", "highest", "largest", "best")):
        for col in numeric.columns:
            parts.append(f"\nTop 5 rows by '{col}':\n{df.nlargest(5, col).to_string()}")
            break

    if "value count" in q or "distribution" in q:
        for col in df.select_dtypes(include="object").columns[:3]:
            parts.append(f"\nValue counts — '{col}':\n{df[col].value_counts().head(10).to_string()}")

    if "null" in q or "missing" in q:
        missing_pct = (df.isnull().sum() / len(df) * 100).round(2)
        parts.append(f"\nMissing percentage:\n{missing_pct.to_string()}")

    result = "\n".join(parts)
    ctx.set("analysis_result", result)
    return result

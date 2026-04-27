from pathlib import Path

import pandas as pd

from app.tools.registry import registry


@registry.register(
    name="DataAnalyzerTool",
    description=(
        "Analyze a CSV file using pandas. Returns shape, column names, data types, "
        "missing-value counts, descriptive statistics, and query-specific insights "
        "(correlations, top-N rows, value counts). Always call this after FileReaderTool "
        "when the task involves data analysis."
    ),
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the CSV file to analyze",
            },
            "query": {
                "type": "string",
                "description": (
                    "Specific analysis to perform, e.g. 'summary statistics', "
                    "'find missing values', 'correlation matrix', "
                    "'top 5 rows by <column>'"
                ),
            },
        },
        "required": ["file_path", "query"],
    },
)
def analyze_data(file_path: str, query: str) -> str:
    path = Path(file_path)

    if not path.exists():
        return f"Error: File '{file_path}' not found."

    if path.suffix.lower() != ".csv":
        return f"Error: DataAnalyzerTool only supports CSV files. Got '{path.suffix}'."

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
    parts.append(f"\nMissing values per column:\n{df.isnull().sum().to_string()}")

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

    return "\n".join(parts)

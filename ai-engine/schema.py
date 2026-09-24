from typing import Any

import pandas as pd


def _clean_value(value: Any) -> Any:
    """Convert Pandas/Numpy values into JSON-friendly Python values."""

    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    return value


def _detect_semantic_type(
    column_name: str,
    series: pd.Series
) -> str:
    """
    Detect a useful semantic type for a column.

    Possible results:
    numeric, date, categorical, text, boolean
    """

    name = column_name.lower().strip()

    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    # Try detecting dates from actual values.
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"

    date_keywords = (
        "date",
        "time",
        "month",
        "year",
        "day",
        "timestamp",
        "created",
        "updated",
    )

    if any(keyword in name for keyword in date_keywords):
        converted = pd.to_datetime(series, errors="coerce")

        if converted.notna().mean() >= 0.7:
            return "date"

    # Low-cardinality text is generally categorical.
    non_null = series.dropna()

    if len(non_null) > 0:
        unique_ratio = non_null.nunique() / len(non_null)

        if unique_ratio <= 0.2 or non_null.nunique() <= 20:
            return "categorical"

    return "text"


def inspect_schema(df: pd.DataFrame) -> dict:
    """
    Analyze an arbitrary DataFrame and return structured schema information.
    """

    columns = []

    for column in df.columns:
        series = df[column]

        non_null = series.dropna()

        column_info = {
            "name": str(column),
            "dtype": str(series.dtype),
            "semantic_type": _detect_semantic_type(str(column), series),
            "missing_values": int(series.isna().sum()),
            "missing_percentage": round(
                float(series.isna().mean() * 100),
                2
            ),
            "unique_values": int(series.nunique(dropna=True)),
        }

        # Numeric statistics
        if pd.api.types.is_numeric_dtype(series):
            column_info["statistics"] = {
                "min": _clean_value(series.min()),
                "max": _clean_value(series.max()),
                "mean": _clean_value(series.mean()),
                "median": _clean_value(series.median()),
                "sum": _clean_value(series.sum()),
            }

        # Example values help the LLM understand the column.
        examples = non_null.head(5).tolist()

        column_info["examples"] = [
            _clean_value(value)
            for value in examples
        ]

        columns.append(column_info)

    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": columns,
    }


def build_schema_summary(df: pd.DataFrame) -> str:
    """
    Convert schema information into a concise human-readable summary.

    This summary will later be provided to the LLM so it can understand
    an unseen dataset before interpreting the user's question.
    """

    schema = inspect_schema(df)

    lines = [
        f"Rows: {schema['row_count']}",
        f"Columns: {schema['column_count']}",
        "",
        "Columns:"
    ]

    for column in schema["columns"]:
        line = (
            f"- {column['name']} | "
            f"type={column['semantic_type']} | "
            f"dtype={column['dtype']} | "
            f"unique={column['unique_values']} | "
            f"missing={column['missing_percentage']}%"
        )

        if column["examples"]:
            line += f" | examples={column['examples']}"

        lines.append(line)

    return "\n".join(lines)
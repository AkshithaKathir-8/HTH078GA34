from typing import Any

import pandas as pd


class AnalysisError(Exception):
    """Raised when an analysis operation cannot be performed."""
    pass


def _ensure_column(df: pd.DataFrame, column: str) -> None:
    """Make sure a requested column actually exists."""

    if column not in df.columns:
        raise AnalysisError(
            f"Column '{column}' does not exist in the dataset."
        )


def _clean_result(value: Any) -> Any:
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


def aggregate(
    df: pd.DataFrame,
    value_column: str,
    aggregation: str,
) -> dict:
    """Perform a single-column aggregation."""

    _ensure_column(df, value_column)

    if not pd.api.types.is_numeric_dtype(df[value_column]):
        raise AnalysisError(
            f"Column '{value_column}' is not numeric and "
            f"cannot be used for {aggregation}."
        )

    operations = {
        "sum": df[value_column].sum,
        "mean": df[value_column].mean,
        "min": df[value_column].min,
        "max": df[value_column].max,
        "median": df[value_column].median,
    }

    if aggregation not in operations:
        raise AnalysisError(
            f"Unsupported aggregation: {aggregation}"
        )

    result = operations[aggregation]()

    return {
        "value": _clean_result(result),
        "value_column": value_column,
        "aggregation": aggregation,
    }


def count(df: pd.DataFrame) -> dict:
    """Count rows in the dataset."""

    return {
        "count": int(len(df))
    }


def groupby_aggregate(
    df: pd.DataFrame,
    group_column: str,
    value_column: str,
    aggregation: str,
    sort: str | None = None,
    limit: int | None = None,
) -> dict:
    """Group data by one column and aggregate another column."""

    _ensure_column(df, group_column)
    _ensure_column(df, value_column)

    if not pd.api.types.is_numeric_dtype(df[value_column]):
        raise AnalysisError(
            f"Column '{value_column}' must be numeric for "
            f"grouped aggregation."
        )

    operations = {
        "sum": "sum",
        "mean": "mean",
        "min": "min",
        "max": "max",
        "median": "median",
    }

    if aggregation not in operations:
        raise AnalysisError(
            f"Unsupported aggregation: {aggregation}"
        )

    grouped = (
        df.groupby(group_column, dropna=False)[value_column]
        .agg(operations[aggregation])
        .reset_index()
    )

    if sort == "ascending":
        grouped = grouped.sort_values(
            by=value_column,
            ascending=True
        )

    elif sort == "descending":
        grouped = grouped.sort_values(
            by=value_column,
            ascending=False
        )

    if limit is not None:
        grouped = grouped.head(int(limit))

    records = []

    for _, row in grouped.iterrows():
        records.append({
            group_column: _clean_result(row[group_column]),
            value_column: _clean_result(row[value_column]),
        })

    return {
        "data": records,
        "group_column": group_column,
        "value_column": value_column,
        "aggregation": aggregation,
    }


def value_count(
    df: pd.DataFrame,
    group_column: str,
    sort: str | None = None,
    limit: int | None = None,
) -> dict:
    """Count occurrences of each unique value."""

    _ensure_column(df, group_column)

    result = (
        df[group_column]
        .value_counts(dropna=False)
        .rename("count")
        .reset_index()
    )

    result.columns = [group_column, "count"]

    if sort == "ascending":
        result = result.sort_values(
            by="count",
            ascending=True
        )

    elif sort == "descending":
        result = result.sort_values(
            by="count",
            ascending=False
        )

    if limit is not None:
        result = result.head(int(limit))

    records = []

    for _, row in result.iterrows():
        records.append({
            group_column: _clean_result(row[group_column]),
            "count": _clean_result(row["count"]),
        })

    return {
        "data": records,
        "group_column": group_column,
    }


def filter_data(
    df: pd.DataFrame,
    column: str,
    operator: str,
    value: Any,
) -> dict:
    """Filter rows using a structured condition."""

    _ensure_column(df, column)

    series = df[column]

    if operator == "equals":
        mask = series.astype(str).str.lower() == str(value).lower()

    elif operator == "not_equals":
        mask = series.astype(str).str.lower() != str(value).lower()

    elif operator == "contains":
        mask = series.astype(str).str.contains(
            str(value),
            case=False,
            na=False,
        )

    elif operator in {
        "greater_than",
        "less_than",
        "greater_or_equal",
        "less_or_equal",
    }:
        numeric_series = pd.to_numeric(
            series,
            errors="coerce"
        )

        try:
            numeric_value = float(value)
        except (ValueError, TypeError) as exc:
            raise AnalysisError(
                f"Value '{value}' must be numeric for "
                f"operator '{operator}'."
            ) from exc

        if operator == "greater_than":
            mask = numeric_series > numeric_value

        elif operator == "less_than":
            mask = numeric_series < numeric_value

        elif operator == "greater_or_equal":
            mask = numeric_series >= numeric_value

        else:
            mask = numeric_series <= numeric_value

    else:
        raise AnalysisError(
            f"Unsupported filter operator: {operator}"
        )

    filtered = df.loc[mask].copy()

    # Convert values to JSON-friendly records.
    records = []

    for record in filtered.to_dict(orient="records"):
        records.append({
            key: _clean_result(value)
            for key, value in record.items()
        })

    return {
        "data": records,
        "row_count": len(records),
        "filter": {
            "column": column,
            "operator": operator,
            "value": value,
        },
    }


def execute_operation(
    df: pd.DataFrame,
    operation: dict,
) -> dict:
    """
    Execute a structured operation against the actual dataset.
    """

    operation_type = operation.get("operation")

    if operation_type == "aggregate":
        return aggregate(
            df,
            operation["value_column"],
            operation["aggregation"],
        )

    if operation_type == "count":
        return count(df)

    if operation_type == "groupby_aggregate":
        return groupby_aggregate(
            df,
            operation["group_column"],
            operation["value_column"],
            operation["aggregation"],
            operation.get("sort"),
            operation.get("limit"),
        )

    if operation_type == "value_count":
        return value_count(
            df,
            operation["group_column"],
            operation.get("sort"),
            operation.get("limit"),
        )

    if operation_type == "filter":
        return filter_data(
            df,
            operation["column"],
            operation["operator"],
            operation["value"],
        )

    if operation_type == "unsupported":
        raise AnalysisError(
            operation.get(
                "reason",
                "This question cannot currently be answered.",
            )
        )

    raise AnalysisError(
        f"Unknown operation: {operation_type}"
    )


def analyze_dataset(
    file_path: str,
    question: str,
    api_key: str | None = None,
) -> dict:
    """
    Public integration function for the backend.

    Parameters:
        file_path:
            Path to the saved CSV/XLSX/XLS dataset.

        question:
            User's natural-language question.

        api_key:
            Optional OpenAI API key.

    Returns:
        Dictionary containing:
        - success
        - answer
        - explanation
        - operation
        - result
        - chart
        - schema
    """

    # Import here to avoid circular imports.
    from engine import analyze_dataset as _analyze_dataset

    return _analyze_dataset(
        file_path=file_path,
        question=question,
        api_key=api_key,
    )
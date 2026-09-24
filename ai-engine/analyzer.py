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


# ============================================================
# DATA DETECTIVE FEATURES
# ============================================================

def detect_duplicates(df: pd.DataFrame) -> dict:
    """
    Detect completely duplicated rows in the dataset.
    """

    duplicate_mask = df.duplicated(keep=False)
    duplicates = df.loc[duplicate_mask].copy()

    records = []

    for record in duplicates.to_dict(orient="records"):
        records.append({
            key: _clean_result(value)
            for key, value in record.items()
        })

    duplicate_row_count = int(len(duplicates))
    duplicate_group_count = int(
        df.duplicated(keep="first").sum()
    )

    return {
        "duplicate_row_count": duplicate_row_count,
        "duplicate_group_count": duplicate_group_count,
        "data": records,
        "has_duplicates": duplicate_row_count > 0,
    }


def detect_anomalies(
    df: pd.DataFrame,
    columns: list[str],
) -> dict:
    """
    Detect numerical outliers using the IQR method.

    Values below Q1 - 1.5*IQR or above Q3 + 1.5*IQR
    are treated as potential anomalies.
    """

    if not columns:
        raise AnalysisError(
            "No numeric columns were provided for anomaly detection."
        )

    all_anomalies = []

    for column in columns:

        _ensure_column(df, column)

        if not pd.api.types.is_numeric_dtype(df[column]):
            continue

        series = pd.to_numeric(
            df[column],
            errors="coerce"
        ).dropna()

        if len(series) < 4:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)

        iqr = q3 - q1

        if iqr == 0:
            continue

        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)

        anomaly_mask = (
            (pd.to_numeric(df[column], errors="coerce") < lower_bound)
            |
            (pd.to_numeric(df[column], errors="coerce") > upper_bound)
        )

        anomaly_rows = df.loc[anomaly_mask].copy()

        for index, row in anomaly_rows.iterrows():

            record = {
                key: _clean_result(value)
                for key, value in row.to_dict().items()
            }

            record["_anomaly_column"] = column
            record["_anomaly_value"] = _clean_result(
                row[column]
            )
            record["_lower_bound"] = _clean_result(
                lower_bound
            )
            record["_upper_bound"] = _clean_result(
                upper_bound
            )

            all_anomalies.append(record)

    return {
        "anomaly_count": len(all_anomalies),
        "columns_checked": columns,
        "method": "IQR",
        "data": all_anomalies,
        "has_anomalies": len(all_anomalies) > 0,
    }


def detect_patterns(
    df: pd.DataFrame,
    columns: list[str],
) -> dict:
    """
    Automatically inspect the dataset for useful patterns.

    This does not guess business conclusions.
    It reports measurable characteristics found in the data.
    """

    if not columns:
        raise AnalysisError(
            "No columns were provided for pattern detection."
        )

    patterns = []

    numeric_columns = [
        column
        for column in columns
        if column in df.columns
        and pd.api.types.is_numeric_dtype(df[column])
    ]

    categorical_columns = [
        column
        for column in columns
        if column in df.columns
        and not pd.api.types.is_numeric_dtype(df[column])
    ]

    # --------------------------------------------------------
    # Numeric patterns
    # --------------------------------------------------------

    for column in numeric_columns:

        series = pd.to_numeric(
            df[column],
            errors="coerce"
        ).dropna()

        if series.empty:
            continue

        mean_value = series.mean()
        median_value = series.median()
        min_value = series.min()
        max_value = series.max()

        patterns.append({
            "type": "numeric_summary",
            "column": column,
            "mean": _clean_result(mean_value),
            "median": _clean_result(median_value),
            "minimum": _clean_result(min_value),
            "maximum": _clean_result(max_value),
        })

        if mean_value > median_value * 1.2:
            patterns.append({
                "type": "distribution_pattern",
                "column": column,
                "finding": (
                    "Mean is substantially higher than median, "
                    "which may indicate high-value observations."
                ),
            })

        elif median_value > mean_value * 1.2:
            patterns.append({
                "type": "distribution_pattern",
                "column": column,
                "finding": (
                    "Median is substantially higher than mean, "
                    "which may indicate lower-value observations."
                ),
            })

    # --------------------------------------------------------
    # Categorical patterns
    # --------------------------------------------------------

    for column in categorical_columns:

        unique_count = int(df[column].nunique(dropna=True))

        if unique_count == 0:
            continue

        value_counts = (
            df[column]
            .value_counts(dropna=False)
        )

        top_value = value_counts.index[0]
        top_count = int(value_counts.iloc[0])

        patterns.append({
            "type": "category_distribution",
            "column": column,
            "unique_values": unique_count,
            "most_common_value": _clean_result(top_value),
            "most_common_count": top_count,
        })

        if top_count / len(df) >= 0.5:
            patterns.append({
                "type": "concentration_pattern",
                "column": column,
                "finding": (
                    f"'{_clean_result(top_value)}' represents "
                    f"{round((top_count / len(df)) * 100, 2)}% "
                    "of the records."
                ),
            })

    # --------------------------------------------------------
    # Numeric correlations
    # --------------------------------------------------------

    if len(numeric_columns) >= 2:

        correlation_matrix = df[numeric_columns].corr()

        for i, first_column in enumerate(numeric_columns):

            for second_column in numeric_columns[i + 1:]:

                correlation = correlation_matrix.loc[
                    first_column,
                    second_column
                ]

                if pd.isna(correlation):
                    continue

                correlation_value = float(correlation)

                if abs(correlation_value) >= 0.7:

                    direction = (
                        "positive"
                        if correlation_value > 0
                        else "negative"
                    )

                    patterns.append({
                        "type": "relationship",
                        "columns": [
                            first_column,
                            second_column,
                        ],
                        "correlation": round(
                            correlation_value,
                            3
                        ),
                        "finding": (
                            f"Strong {direction} relationship "
                            f"between '{first_column}' and "
                            f"'{second_column}'."
                        ),
                    })

    return {
        "columns_checked": columns,
        "patterns_found": len(patterns),
        "data": patterns,
    }


def generate_recommendations(
    df: pd.DataFrame,
) -> dict:
    """
    Generate evidence-based recommendations from measurable
    characteristics of the uploaded dataset.
    """

    recommendations = []
    findings = []

    numeric_columns = [
        column
        for column in df.columns
        if pd.api.types.is_numeric_dtype(df[column])
    ]

    categorical_columns = [
        column
        for column in df.columns
        if not pd.api.types.is_numeric_dtype(df[column])
    ]

    # --------------------------------------------------------
    # Find potentially important numeric columns
    # --------------------------------------------------------

    if numeric_columns:

        highest_variance_column = max(
            numeric_columns,
            key=lambda column: (
                pd.to_numeric(
                    df[column],
                    errors="coerce"
                ).var()
                if not df[column].dropna().empty
                else 0
            )
        )

        findings.append({
            "type": "highest_variability",
            "column": highest_variance_column,
        })

        recommendations.append(
            f"Investigate variation in '{highest_variance_column}' "
            "to identify the factors causing large differences."
        )

    # --------------------------------------------------------
    # Look for dominant categories
    # --------------------------------------------------------

    for column in categorical_columns:

        counts = df[column].value_counts(
            dropna=False
        )

        if counts.empty:
            continue

        top_value = counts.index[0]
        top_count = int(counts.iloc[0])

        share = top_count / len(df)

        if share >= 0.5:

            findings.append({
                "type": "dominant_category",
                "column": column,
                "value": _clean_result(top_value),
                "share": round(share * 100, 2),
            })

            recommendations.append(
                f"Review the dominant '{column}' value "
                f"'{_clean_result(top_value)}' because it represents "
                f"{round(share * 100, 2)}% of the records."
            )

    # --------------------------------------------------------
    # Detect potential anomalies
    # --------------------------------------------------------

    for column in numeric_columns:

        series = pd.to_numeric(
            df[column],
            errors="coerce"
        ).dropna()

        if len(series) < 4:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            continue

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        anomaly_count = int(
            ((series < lower) | (series > upper)).sum()
        )

        if anomaly_count > 0:

            findings.append({
                "type": "anomalies",
                "column": column,
                "count": anomaly_count,
            })

            recommendations.append(
                f"Investigate {anomaly_count} unusual "
                f"record(s) in '{column}' before making "
                "business decisions."
            )

    # --------------------------------------------------------
    # Safe fallback recommendation
    # --------------------------------------------------------

    if not recommendations:

        recommendations.append(
            "No strong automated recommendation was found. "
            "Consider examining relationships, distributions, "
            "and unusual records in the dataset."
        )

    return {
        "recommendations": recommendations,
        "findings": findings,
    }


# ============================================================
# OPERATION ROUTER
# ============================================================

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

    # ========================================================
    # DATA DETECTIVE OPERATIONS
    # ========================================================

    if operation_type == "duplicate_detection":
        return detect_duplicates(df)

    if operation_type == "anomaly_detection":
        return detect_anomalies(
            df,
            operation.get("columns", []),
        )

    if operation_type == "pattern_detection":
        return detect_patterns(
            df,
            operation.get("columns", list(df.columns)),
        )

    if operation_type == "recommendation":
        return generate_recommendations(df)

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
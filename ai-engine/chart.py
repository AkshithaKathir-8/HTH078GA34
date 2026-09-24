from typing import Any


def _get_value(record: dict[str, Any], key: str) -> Any:
    """Safely get a value from a record."""

    return record.get(key)


def build_chart(
    operation: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Convert an analysis result into frontend-friendly chart data.

    The frontend does not need to understand Pandas operations.
    It only needs the chart type, axis information, and data.
    """

    operation_type = operation.get("operation")

    # --------------------------------------------------------
    # Grouped aggregation
    # --------------------------------------------------------

    if operation_type == "groupby_aggregate":

        records = result.get("data", [])

        if not records:
            return None

        group_column = operation["group_column"]
        value_column = operation["value_column"]

        return {
            "type": "bar",
            "x": group_column,
            "y": value_column,
            "title": (
                f"{operation['aggregation'].title()} "
                f"{value_column} by {group_column}"
            ),
            "data": [
                {
                    group_column: _get_value(
                        record,
                        group_column
                    ),
                    value_column: _get_value(
                        record,
                        value_column
                    ),
                }
                for record in records
            ],
        }

    # --------------------------------------------------------
    # Value count
    # --------------------------------------------------------

    if operation_type == "value_count":

        records = result.get("data", [])

        if not records:
            return None

        group_column = operation["group_column"]

        return {
            "type": "bar",
            "x": group_column,
            "y": "count",
            "title": f"Count by {group_column}",
            "data": [
                {
                    group_column: _get_value(
                        record,
                        group_column
                    ),
                    "count": _get_value(
                        record,
                        "count"
                    ),
                }
                for record in records
            ],
        }

    # --------------------------------------------------------
    # Aggregate
    # --------------------------------------------------------

    if operation_type == "aggregate":

        return {
            "type": "metric",
            "value": result.get("value"),
            "label": (
                f"{operation['aggregation'].title()} "
                f"{operation['value_column']}"
            ),
        }

    # --------------------------------------------------------
    # Count
    # --------------------------------------------------------

    if operation_type == "count":

        return {
            "type": "metric",
            "value": result.get("count"),
            "label": "Total Records",
        }

    # --------------------------------------------------------
    # Filter
    # --------------------------------------------------------

    if operation_type == "filter":

        records = result.get("data", [])

        if not records:
            return {
                "type": "table",
                "columns": [],
                "data": [],
            }

        columns = list(records[0].keys())

        return {
            "type": "table",
            "columns": columns,
            "data": records,
        }

    # --------------------------------------------------------
    # Duplicate detection
    # --------------------------------------------------------

    if operation_type == "duplicate_detection":

        duplicate_count = result.get(
            "duplicate_row_count",
            0
        )

        group_count = result.get(
            "duplicate_group_count",
            0
        )

        return {
            "type": "metric",
            "value": duplicate_count,
            "label": "Duplicate Records",
            "duplicate_groups": group_count,
            "has_duplicates": result.get(
                "has_duplicates",
                False
            ),
        }

    # --------------------------------------------------------
    # Anomaly detection
    # --------------------------------------------------------

    if operation_type == "anomaly_detection":

        records = result.get("data", [])

        if not records:
            return {
                "type": "metric",
                "value": 0,
                "label": "Potential Anomalies",
                "columns_checked": result.get(
                    "columns_checked",
                    []
                ),
            }

        return {
            "type": "table",
            "title": "Potential Anomalies",
            "columns": list(records[0].keys()),
            "data": records,
            "columns_checked": result.get(
                "columns_checked",
                []
            ),
            "method": result.get(
                "method",
                "IQR"
            ),
        }

    # --------------------------------------------------------
    # Pattern detection
    # --------------------------------------------------------

    if operation_type == "pattern_detection":

        patterns = result.get("data", [])

        if not patterns:
            return None

        # Extract only patterns that have a numeric correlation.
        correlation_patterns = [
            pattern
            for pattern in patterns
            if pattern.get("type") == "relationship"
            and isinstance(
                pattern.get("correlation"),
                (int, float)
            )
        ]

        if correlation_patterns:

            chart_data = []

            for pattern in correlation_patterns:

                columns = pattern.get(
                    "columns",
                    []
                )

                if len(columns) < 2:
                    continue

                chart_data.append({
                    "relationship": (
                        f"{columns[0]} vs {columns[1]}"
                    ),
                    "correlation": pattern.get(
                        "correlation"
                    ),
                })

            if chart_data:

                return {
                    "type": "bar",
                    "x": "relationship",
                    "y": "correlation",
                    "title": "Detected Numeric Relationships",
                    "data": chart_data,
                }

        # If no correlation pattern exists,
        # return the detected pattern information as a table.
        return {
            "type": "table",
            "title": "Detected Patterns",
            "columns": [
                "type",
                "column",
                "finding",
            ],
            "data": [
                {
                    "type": pattern.get(
                        "type"
                    ),
                    "column": pattern.get(
                        "column"
                    ),
                    "finding": pattern.get(
                        "finding",
                        "",
                    ),
                }
                for pattern in patterns
            ],
        }

    # --------------------------------------------------------
    # Recommendations
    # --------------------------------------------------------

    if operation_type == "recommendation":

        # Recommendations are primarily textual findings.
        # Do not create a misleading chart.
        return None

    return None
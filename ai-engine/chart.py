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

    
    if operation_type == "aggregate":

        return {
            "type": "metric",
            "value": result.get("value"),
            "label": (
                f"{operation['aggregation'].title()} "
                f"{operation['value_column']}"
            ),
        }

   
    if operation_type == "count":

        return {
            "type": "metric",
            "value": result.get("count"),
            "label": "Total Records",
        }

    
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

    return None
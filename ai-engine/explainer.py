from typing import Any


def _format_value(value: Any) -> str:
    """Format values for human-readable explanations."""

    if value is None:
        return "N/A"

    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"

    if isinstance(value, int):
        return f"{value:,}"

    return str(value)


def explain_operation(
    operation: dict[str, Any],
    result: dict[str, Any],
) -> list[str]:
    """
    Generate a transparent explanation of the calculation performed.
    """

    operation_type = operation.get("operation")

    # ---------------------------------------------------------
    # Aggregate
    # ---------------------------------------------------------

    if operation_type == "aggregate":

        aggregation = operation["aggregation"]
        column = operation["value_column"]
        value = result.get("value")

        aggregation_words = {
            "sum": "total",
            "mean": "average",
            "min": "minimum",
            "max": "maximum",
            "median": "median",
        }

        description = aggregation_words.get(
            aggregation,
            aggregation,
        )

        return [
            f"Selected the '{column}' column.",
            f"Calculated the {description} using the dataset values.",
            f"The calculated value is {_format_value(value)}.",
        ]

    # ---------------------------------------------------------
    # Count
    # ---------------------------------------------------------

    if operation_type == "count":

        count = result.get("count", 0)

        return [
            "Counted all records in the dataset.",
            f"The dataset contains {_format_value(count)} records.",
        ]

    # ---------------------------------------------------------
    # Group + Aggregate
    # ---------------------------------------------------------

    if operation_type == "groupby_aggregate":

        group_column = operation["group_column"]
        value_column = operation["value_column"]
        aggregation = operation["aggregation"]

        aggregation_words = {
            "sum": "total",
            "mean": "average",
            "min": "minimum",
            "max": "maximum",
            "median": "median",
        }

        description = aggregation_words.get(
            aggregation,
            aggregation,
        )

        explanation = [
            f"Grouped the dataset by '{group_column}'.",
            (
                f"Calculated the {description} "
                f"of '{value_column}' for each group."
            ),
        ]

        sort = operation.get("sort")
        limit = operation.get("limit")

        if sort == "descending":
            explanation.append(
                f"Sorted the results from highest to lowest "
                f"'{value_column}'."
            )

        elif sort == "ascending":
            explanation.append(
                f"Sorted the results from lowest to highest "
                f"'{value_column}'."
            )

        if limit:
            explanation.append(
                f"Returned the top {limit} result(s) after sorting."
            )

        return explanation

    # ---------------------------------------------------------
    # Value count
    # ---------------------------------------------------------

    if operation_type == "value_count":

        group_column = operation["group_column"]

        explanation = [
            (
                f"Counted how many records belong to each "
                f"unique value in '{group_column}'."
            )
        ]

        sort = operation.get("sort")
        limit = operation.get("limit")

        if sort == "descending":
            explanation.append(
                "Sorted the counts from highest to lowest."
            )

        elif sort == "ascending":
            explanation.append(
                "Sorted the counts from lowest to highest."
            )

        if limit:
            explanation.append(
                f"Returned the top {limit} result(s)."
            )

        return explanation

    # ---------------------------------------------------------
    # Filter
    # ---------------------------------------------------------

    if operation_type == "filter":

        column = operation["column"]
        operator = operation["operator"]
        value = operation["value"]
        row_count = result.get("row_count", 0)

        operator_words = {
            "equals": "equal to",
            "not_equals": "not equal to",
            "greater_than": "greater than",
            "less_than": "less than",
            "greater_or_equal": "greater than or equal to",
            "less_or_equal": "less than or equal to",
            "contains": "containing",
        }

        comparison = operator_words.get(
            operator,
            operator,
        )

        return [
            (
                f"Filtered the '{column}' column for values "
                f"{comparison} '{value}'."
            ),
            (
                f"Found {_format_value(row_count)} "
                f"matching record(s)."
            ),
        ]

    # =========================================================
    # DATA DETECTIVE FEATURES
    # =========================================================

    # ---------------------------------------------------------
    # Duplicate Detection
    # ---------------------------------------------------------

    if operation_type == "duplicate_detection":

        duplicate_count = result.get(
            "duplicate_row_count",
            0,
        )

        duplicate_groups = result.get(
            "duplicate_group_count",
            0,
        )

        if result.get("has_duplicates"):

            return [
                "Compared complete rows across the dataset.",
                (
                    f"Found {_format_value(duplicate_count)} "
                    f"record(s) that belong to duplicate groups."
                ),
                (
                    f"Detected {_format_value(duplicate_groups)} "
                    f"duplicated record group(s)."
                ),
            ]

        return [
            "Compared complete rows across the dataset.",
            "No completely duplicated records were detected.",
        ]

    # ---------------------------------------------------------
    # Anomaly Detection
    # ---------------------------------------------------------

    if operation_type == "anomaly_detection":

        anomaly_count = result.get(
            "anomaly_count",
            0,
        )

        columns = result.get(
            "columns_checked",
            [],
        )

        method = result.get(
            "method",
            "IQR",
        )

        if anomaly_count > 0:

            return [
                (
                    f"Checked numeric column(s) "
                    f"{', '.join(str(column) for column in columns)} "
                    f"for unusual values."
                ),
                (
                    f"Used the {method} statistical method "
                    f"to identify potential outliers."
                ),
                (
                    f"Found {_format_value(anomaly_count)} "
                    f"potential anomalous record(s)."
                ),
            ]

        return [
            (
                f"Checked numeric column(s) "
                f"{', '.join(str(column) for column in columns)}."
            ),
            (
                f"Used the {method} method to identify "
                "potential outliers."
            ),
            "No potential anomalies were detected.",
        ]

    # ---------------------------------------------------------
    # Pattern Detection
    # ---------------------------------------------------------

    if operation_type == "pattern_detection":

        pattern_count = result.get(
            "patterns_found",
            0,
        )

        columns = result.get(
            "columns_checked",
            [],
        )

        explanation = [
            (
                f"Inspected {len(columns)} dataset column(s) "
                "for measurable patterns."
            ),
            (
                "Analyzed numeric distributions, category "
                "concentrations, and relationships between "
                "numeric columns."
            ),
            (
                f"Found {_format_value(pattern_count)} "
                f"measurable pattern(s)."
            ),
        ]

        return explanation

    # ---------------------------------------------------------
    # Recommendations
    # ---------------------------------------------------------

    if operation_type == "recommendation":

        findings = result.get(
            "findings",
            [],
        )

        recommendations = result.get(
            "recommendations",
            [],
        )

        explanation = [
            "Inspected the uploaded dataset for measurable findings.",
            (
                f"Identified {_format_value(len(findings))} "
                "data-driven finding(s)."
            ),
            (
                f"Generated {_format_value(len(recommendations))} "
                "evidence-based recommendation(s)."
            ),
        ]

        return explanation

    # ---------------------------------------------------------
    # Unsupported
    # ---------------------------------------------------------

    if operation_type == "unsupported":

        return [
            result.get(
                "reason",
                "This question is not currently supported.",
            )
        ]

    return [
        "The analysis was completed."
    ]
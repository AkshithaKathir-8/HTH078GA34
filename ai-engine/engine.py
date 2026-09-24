import json
from pathlib import Path
from typing import Any

from analyzer import AnalysisError, execute_operation
from chart import build_chart
from explainer import explain_operation
from loader import load_dataset
from question_parser import QuestionParser
from schema import build_schema_summary, inspect_schema


class DataIntelligenceEngine:
    """
    Main orchestration layer for Data Detective AI.

    Pipeline:
        Dataset
        -> Load
        -> Schema Understanding
        -> Question Understanding
        -> Pandas Analysis
        -> Chart Generation
        -> Explanation
        -> Structured Result
    """

    def __init__(self, api_key: str | None = None):
        self.question_parser = QuestionParser(api_key=api_key)

    def analyze(
        self,
        file_path: str,
        question: str,
    ) -> dict[str, Any]:

        try:
            # -------------------------------------------------
            # 1. Load dataset
            # -------------------------------------------------

            df = load_dataset(file_path)

            # -------------------------------------------------
            # 2. Understand dataset
            # -------------------------------------------------

            schema = inspect_schema(df)
            schema_summary = build_schema_summary(df)

            # -------------------------------------------------
            # 3. Understand user's question
            # -------------------------------------------------

            operation = self.question_parser.parse(
                question=question,
                schema_summary=schema_summary,
            )

            # -------------------------------------------------
            # 4. Handle unsupported questions
            # -------------------------------------------------

            if operation.get("operation") == "unsupported":
                explanation = explain_operation(
                    operation,
                    operation,
                )

                return {
                    "success": False,
                    "answer": operation.get(
                        "reason",
                        "This question is not currently supported.",
                    ),
                    "explanation": explanation,
                    "operation": operation,
                    "chart": None,
                    "schema": schema,
                }

            # -------------------------------------------------
            # 5. Perform actual calculation with Pandas
            # -------------------------------------------------

            analysis_result = execute_operation(
                df,
                operation,
            )

            # -------------------------------------------------
            # 6. Generate chart-ready data
            # -------------------------------------------------

            chart = build_chart(
                operation,
                analysis_result,
            )

            # -------------------------------------------------
            # 7. Generate calculation explanation
            # -------------------------------------------------

            explanation = explain_operation(
                operation,
                analysis_result,
            )

            # -------------------------------------------------
            # 8. Generate human-readable answer
            # -------------------------------------------------

            answer = self._build_answer(
                operation,
                analysis_result,
            )

            return {
                "success": True,
                "answer": answer,
                "explanation": explanation,
                "operation": operation,
                "result": analysis_result,
                "chart": chart,
                "schema": schema,
            }

        except (FileNotFoundError, ValueError, AnalysisError) as exc:

            return {
                "success": False,
                "answer": str(exc),
                "explanation": [],
                "operation": None,
                "result": None,
                "chart": None,
                "schema": None,
            }

        except Exception as exc:

            return {
                "success": False,
                "answer": f"Unexpected analysis error: {exc}",
                "explanation": [],
                "operation": None,
                "result": None,
                "chart": None,
                "schema": None,
            }

    @staticmethod
    def _build_answer(
        operation: dict[str, Any],
        result: dict[str, Any],
    ) -> str:

        operation_type = operation.get("operation")

        # -----------------------------------------------------
        # Aggregate answer
        # -----------------------------------------------------

        if operation_type == "aggregate":

            value = result.get("value")
            column = operation["value_column"]
            aggregation = operation["aggregation"]

            labels = {
                "sum": "total",
                "mean": "average",
                "min": "minimum",
                "max": "maximum",
                "median": "median",
            }

            label = labels.get(
                aggregation,
                aggregation,
            )

            return (
                f"The {label} of '{column}' is "
                f"{DataIntelligenceEngine._format_number(value)}."
            )

        # -----------------------------------------------------
        # Count answer
        # -----------------------------------------------------

        if operation_type == "count":

            count = result.get("count", 0)

            return (
                f"The dataset contains "
                f"{DataIntelligenceEngine._format_number(count)} "
                f"records."
            )

        # -----------------------------------------------------
        # Grouped aggregation answer
        # -----------------------------------------------------

        if operation_type == "groupby_aggregate":

            records = result.get("data", [])

            if not records:
                return "No results were found."

            group_column = operation["group_column"]
            value_column = operation["value_column"]
            aggregation = operation["aggregation"]

            labels = {
                "sum": "total",
                "mean": "average",
                "min": "minimum",
                "max": "maximum",
                "median": "median",
            }

            label = labels.get(
                aggregation,
                aggregation,
            )

            # -------------------------------------------------
            # Single result
            # Example:
            # Which country has the highest total quantity?
            # -------------------------------------------------

            if operation.get("limit") == 1:

                first = records[0]

                group_value = first.get(group_column)
                result_value = first.get(value_column)

                if operation.get("sort") == "descending":

                    return (
                        f"{group_value} has the highest "
                        f"{label} {value_column} with "
                        f"{DataIntelligenceEngine._format_number(result_value)}."
                    )

                return (
                    f"{group_value} has the lowest "
                    f"{label} {value_column} with "
                    f"{DataIntelligenceEngine._format_number(result_value)}."
                )

            # -------------------------------------------------
            # Multiple results
            # Example:
            # What are the top 5 countries by total quantity?
            # -------------------------------------------------

            lines = []

            for index, record in enumerate(
                records,
                start=1,
            ):

                group_value = record.get(
                    group_column
                )

                result_value = record.get(
                    value_column
                )

                lines.append(
                    f"{index}. {group_value} — "
                    f"{DataIntelligenceEngine._format_number(result_value)}"
                )

            if operation.get("sort") == "descending":
                direction = "Top"
            else:
                direction = "Bottom"

            return (
                f"{direction} {len(records)} "
                f"{group_column} by {label} {value_column}:\n"
                + "\n".join(lines)
            )

        # -----------------------------------------------------
        # Value count answer
        # -----------------------------------------------------

        if operation_type == "value_count":

            records = result.get("data", [])

            if not records:
                return "No values were found."

            group_column = operation["group_column"]

            if operation.get("limit") == 1:
                first = records[0]

                return (
                    f"'{first.get(group_column)}' has "
                    f"{DataIntelligenceEngine._format_number(first.get('count'))} "
                    f"record(s)."
                )

            return (
                f"Counted {len(records)} unique values "
                f"in '{group_column}'."
            )

        # -----------------------------------------------------
        # Filter answer
        # -----------------------------------------------------

        if operation_type == "filter":

            row_count = result.get("row_count", 0)

            return (
                f"Found "
                f"{DataIntelligenceEngine._format_number(row_count)} "
                f"matching record(s)."
            )

        # -----------------------------------------------------
        # Duplicate detection answer
        # -----------------------------------------------------

        if operation_type == "duplicate_detection":

            duplicate_count = result.get(
                "duplicate_row_count",
                0,
            )

            group_count = result.get(
                "duplicate_group_count",
                0,
            )

            if not result.get(
                "has_duplicates",
                False,
            ):

                return (
                    "No completely duplicated records "
                    "were detected."
                )

            return (
                f"Found "
                f"{DataIntelligenceEngine._format_number(duplicate_count)} "
                f"duplicate record(s) across "
                f"{DataIntelligenceEngine._format_number(group_count)} "
                f"duplicate group(s)."
            )

        # -----------------------------------------------------
        # Anomaly detection answer
        # -----------------------------------------------------

        if operation_type == "anomaly_detection":

            anomaly_count = result.get(
                "anomaly_count",
                0,
            )

            columns = result.get(
                "columns_checked",
                [],
            )

            if not result.get(
                "has_anomalies",
                False,
            ):

                return (
                    "No potential anomalies were detected in "
                    f"{', '.join(columns)}."
                    if columns
                    else
                    "No potential anomalies were detected."
                )

            column_text = ", ".join(columns)

            return (
                f"Found "
                f"{DataIntelligenceEngine._format_number(anomaly_count)} "
                f"potential anomalous value(s) in "
                f"{column_text} using IQR-based detection."
            )

        # -----------------------------------------------------
        # Pattern detection answer
        # -----------------------------------------------------

        if operation_type == "pattern_detection":

            # The actual pattern records are stored in "data".
            # "patterns_found" is only the integer count.

            patterns = result.get(
                "data",
                [],
            )

            if not patterns:

                return (
                    "No strong measurable patterns were detected "
                    "in the selected columns."
                )

            descriptions = []

            for pattern in patterns[:3]:

                pattern_type = pattern.get(
                    "type",
                    "pattern",
                )

                if pattern_type == "numeric_summary":

                    descriptions.append(
                        f"'{pattern.get('column')}' has a mean of "
                        f"{DataIntelligenceEngine._format_number(pattern.get('mean'))} "
                        f"and a median of "
                        f"{DataIntelligenceEngine._format_number(pattern.get('median'))}"
                    )

                elif pattern_type == "distribution_pattern":

                    descriptions.append(
                        f"'{pattern.get('column')}': "
                        f"{pattern.get('finding')}"
                    )

                elif pattern_type == "category_distribution":

                    descriptions.append(
                        f"'{pattern.get('column')}' has "
                        f"{pattern.get('unique_values')} unique values, "
                        f"with '{pattern.get('most_common_value')}' "
                        f"being the most common"
                    )

                elif pattern_type == "concentration_pattern":

                    descriptions.append(
                        f"'{pattern.get('column')}': "
                        f"{pattern.get('finding')}"
                    )

                elif pattern_type == "relationship":

                    columns = pattern.get(
                        "columns",
                        [],
                    )

                    if len(columns) >= 2:

                        descriptions.append(
                            f"'{columns[0]}' and '{columns[1]}' "
                            f"have a correlation of "
                            f"{pattern.get('correlation')}"
                        )

                elif pattern.get("finding"):

                    descriptions.append(
                        str(pattern.get("finding"))
                    )

            if descriptions:

                return (
                    f"Detected {len(patterns)} measurable pattern(s): "
                    + "; ".join(descriptions)
                    + "."
                )

            return (
                f"Detected {len(patterns)} measurable pattern(s) "
                "in the dataset."
            )

        # -----------------------------------------------------
        # Recommendation answer
        # -----------------------------------------------------

        if operation_type == "recommendation":

            recommendations = result.get(
                "recommendations",
                [],
            )

            findings = result.get(
                "findings",
                [],
            )

            if not recommendations:

                return (
                    "No specific recommendations could be generated "
                    "from the available dataset."
                )

            parts = []

            for recommendation in recommendations[:3]:

                parts.append(
                    str(recommendation)
                )

            return (
                f"Based on {len(findings)} detected finding(s), "
                "the analysis suggests: "
                + " ".join(parts)
            )

        # -----------------------------------------------------
        # Fallback
        # -----------------------------------------------------

        return "Analysis completed successfully."

    @staticmethod
    def _format_number(value: Any) -> str:

        if value is None:
            return "N/A"

        if isinstance(value, float):

            if value.is_integer():
                return f"{int(value):,}"

            return f"{value:,.2f}"

        if isinstance(value, int):
            return f"{value:,}"

        return str(value)


def analyze_dataset(
    file_path: str,
    question: str,
    api_key: str | None = None,
) -> dict[str, Any]:
    """
    Convenience function for backend integration.
    """

    engine = DataIntelligenceEngine(
        api_key=api_key
    )

    return engine.analyze(
        file_path=file_path,
        question=question,
    )


def save_result(
    result: dict[str, Any],
    output_path: str = "analysis_result.json",
) -> None:
    """Save the analysis result as JSON."""

    path = Path(output_path)

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False,
        )
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

            first = records[0]

            group_value = first.get(group_column)
            result_value = first.get(value_column)

            if operation.get("limit") == 1:
                return (
                    f"{group_value} has the highest "
                    f"{label} {value_column} with "
                    f"{DataIntelligenceEngine._format_number(result_value)}."
                    if operation.get("sort") == "descending"
                    else
                    f"{group_value} has the lowest "
                    f"{label} {value_column} with "
                    f"{DataIntelligenceEngine._format_number(result_value)}."
                )

            return (
                f"Calculated the {label} {value_column} "
                f"for {len(records)} groups."
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
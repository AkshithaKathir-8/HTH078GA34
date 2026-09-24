import json
import os
import re
from typing import Any

from openai import OpenAI


class QuestionParser:
    """
    Converts a natural-language question into a structured
    analysis operation.

    OpenAI is the primary parser.
    A local fallback parser is used when the API is unavailable.

    Pandas performs the actual calculation.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        self.client = None

        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    def parse(
        self,
        question: str,
        schema_summary: str
    ) -> dict[str, Any]:

        if not question or not question.strip():
            raise ValueError("Question cannot be empty.")

        # Try OpenAI first
        if self.client:
            try:
                return self._parse_with_llm(
                    question,
                    schema_summary
                )
            except Exception as exc:
                print(
                    f"\n[INFO] OpenAI unavailable: {exc}"
                )
                print(
                    "[INFO] Switching to local fallback parser..."
                )

        # Use local parser if OpenAI is unavailable
        return self._parse_locally(
            question,
            schema_summary
        )

    # =========================================================
    # OPENAI PARSER
    # =========================================================

    def _parse_with_llm(
        self,
        question: str,
        schema_summary: str
    ) -> dict[str, Any]:

        prompt = f"""
You are the question-understanding component of a
schema-agnostic data analysis system.

Your job is ONLY to understand the user's question and
convert it into a structured JSON analysis operation.

Do NOT calculate the answer.
Do NOT invent data.
Do NOT return the final answer.

The actual calculation will be performed by Pandas.

DATASET SCHEMA
--------------
{schema_summary}

USER QUESTION
-------------
{question}

SUPPORTED OPERATIONS

1. aggregate

Format:
{{
  "operation": "aggregate",
  "value_column": "column",
  "aggregation": "sum|mean|min|max|median"
}}

2. count

Format:
{{
  "operation": "count"
}}

3. groupby_aggregate

Format:
{{
  "operation": "groupby_aggregate",
  "group_column": "column",
  "value_column": "column",
  "aggregation": "sum|mean|min|max|median",
  "sort": "ascending|descending|null",
  "limit": number or null
}}

4. value_count

Format:
{{
  "operation": "value_count",
  "group_column": "column",
  "sort": "ascending|descending|null",
  "limit": number or null
}}

5. filter

Format:
{{
  "operation": "filter",
  "column": "column",
  "operator": "equals|not_equals|greater_than|less_than|greater_or_equal|less_or_equal|contains",
  "value": "value"
}}

6. unsupported

Format:
{{
  "operation": "unsupported",
  "reason": "short explanation"
}}

RULES

- Column names MUST exactly match the supplied schema.
- Never invent a column.
- For highest, use descending and limit=1.
- For lowest, use ascending and limit=1.
- For top N, use descending and limit=N.
- For bottom N, use ascending and limit=N.
- Return ONLY valid JSON.
"""

        response = self.client.responses.create(
            model="gpt-5-mini",
            input=prompt,
        )

        raw_output = response.output_text.strip()

        try:
            operation = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned invalid JSON: {raw_output}"
            ) from exc

        self._validate_operation(
            operation,
            schema_summary
        )

        return operation

    # =========================================================
    # LOCAL FALLBACK PARSER
    # =========================================================

    def _parse_locally(
        self,
        question: str,
        schema_summary: str
    ) -> dict[str, Any]:

        question_lower = question.lower().strip()

        columns = self._extract_columns(
            schema_summary
        )

        if not columns:
            return {
                "operation": "unsupported",
                "reason": (
                    "The dataset schema could not be "
                    "understood by the local parser."
                ),
            }

        # -----------------------------------------------------
        # COUNT
        # -----------------------------------------------------

        if any(
            phrase in question_lower
            for phrase in [
                "how many records",
                "how many rows",
                "how many entries",
                "number of records",
                "number of rows",
            ]
        ):
            return {
                "operation": "count"
            }

        # -----------------------------------------------------
        # FIND COLUMNS
        # -----------------------------------------------------

        group_column = self._find_column(
            question_lower,
            columns
        )

        value_column = self._find_numeric_column(
            question_lower,
            columns
        )

        # -----------------------------------------------------
        # AGGREGATION
        # -----------------------------------------------------

        aggregation = self._detect_aggregation(
            question_lower
        )

        # -----------------------------------------------------
        # SORTING
        # -----------------------------------------------------

        sort = None
        limit = None

        if any(
            word in question_lower
            for word in [
                "highest",
                "largest",
                "maximum",
                "max",
                "top",
                "most",
            ]
        ):
            sort = "descending"

        elif any(
            word in question_lower
            for word in [
                "lowest",
                "smallest",
                "minimum",
                "min",
                "bottom",
                "least",
            ]
        ):
            sort = "ascending"

        # -----------------------------------------------------
        # TOP N / BOTTOM N
        # -----------------------------------------------------

        number_match = re.search(
            r"\b(top|bottom)\s+(\d+)\b",
            question_lower
        )

        if number_match:
            limit = int(
                number_match.group(2)
            )

        elif sort is not None:
            limit = 1

        # -----------------------------------------------------
        # GROUP BY
        # -----------------------------------------------------

        has_grouping = any(
            phrase in question_lower
            for phrase in [
                " by ",
                " per ",
                " for each ",
                " each ",
                "grouped by",
                "group by",
            ]
        )

        if (
            group_column
            and value_column
            and (
                has_grouping
                or sort is not None
            )
        ):
            return {
                "operation": "groupby_aggregate",
                "group_column": group_column,
                "value_column": value_column,
                "aggregation": aggregation or "sum",
                "sort": sort,
                "limit": limit,
            }

        # -----------------------------------------------------
        # VALUE COUNT
        # -----------------------------------------------------

        if (
            group_column
            and any(
                phrase in question_lower
                for phrase in [
                    "how many",
                    "count",
                    "number of",
                ]
            )
        ):
            return {
                "operation": "value_count",
                "group_column": group_column,
                "sort": sort,
                "limit": limit,
            }

        # -----------------------------------------------------
        # SIMPLE AGGREGATE
        # -----------------------------------------------------

        if value_column and aggregation:
            return {
                "operation": "aggregate",
                "value_column": value_column,
                "aggregation": aggregation,
            }

        # -----------------------------------------------------
        # UNSUPPORTED
        # -----------------------------------------------------

        return {
            "operation": "unsupported",
            "reason": (
                "The local parser could not map this "
                "question to a supported operation."
            ),
        }

    # =========================================================
    # SCHEMA PARSER
    # =========================================================

    @staticmethod
    def _extract_columns(
        schema_summary: str
    ) -> list[dict[str, str]]:

        columns = []

        for line in schema_summary.splitlines():

            line = line.strip()

            # We only care about lines beginning with "-"
            if not line.startswith("-"):
                continue

            # Example:
            # - Product | type=categorical | dtype=str

            parts = [
                part.strip()
                for part in line[1:].split("|")
            ]

            if not parts:
                continue

            column_name = parts[0]

            column_type = None

            for part in parts[1:]:

                if part.startswith("type="):
                    column_type = part[
                        len("type="):
                    ].strip().lower()

            if column_name and column_type:

                columns.append({
                    "name": column_name,
                    "semantic_type": column_type,
                })

        return columns

    # =========================================================
    # COLUMN MATCHING
    # =========================================================

    @staticmethod
    def _find_column(
        question_lower: str,
        columns: list[dict[str, str]]
    ) -> str | None:

        # Exact name match
        for column in columns:

            name = column["name"]

            if name.lower() in question_lower:
                return name

        # Word match
        for column in columns:

            words = re.findall(
                r"[a-zA-Z0-9]+",
                column["name"].lower()
            )

            for word in words:

                if len(word) > 2 and word in question_lower:
                    return column["name"]

        return None

    @staticmethod
    def _find_numeric_column(
        question_lower: str,
        columns: list[dict[str, str]]
    ) -> str | None:

        numeric_columns = [
            column
            for column in columns
            if column["semantic_type"] == "numeric"
        ]

        # Exact match
        for column in numeric_columns:

            if column["name"].lower() in question_lower:
                return column["name"]

        # Word match
        for column in numeric_columns:

            words = re.findall(
                r"[a-zA-Z0-9]+",
                column["name"].lower()
            )

            for word in words:

                if len(word) > 2 and word in question_lower:
                    return column["name"]

        # Only one numeric column
        if len(numeric_columns) == 1:
            return numeric_columns[0]["name"]

        return None

    # =========================================================
    # AGGREGATION DETECTION
    # =========================================================

    @staticmethod
    def _detect_aggregation(
        question_lower: str
    ) -> str | None:

        # -----------------------------------------------------
        # IMPORTANT:
        # "highest total sales" means:
        #   aggregate = SUM
        #   sorting = DESCENDING
        #
        # "highest sales" without "total" can mean MAX.
        # -----------------------------------------------------

        if any(
            phrase in question_lower
            for phrase in [
                "total",
                "sum",
                "overall total",
            ]
        ):
            return "sum"

        # -----------------------------------------------------
        # AVERAGE / MEAN
        # -----------------------------------------------------

        if any(
            word in question_lower
            for word in [
                "average",
                "avg",
                "mean",
            ]
        ):
            return "mean"

        # -----------------------------------------------------
        # MEDIAN
        # -----------------------------------------------------

        if "median" in question_lower:
            return "median"

        # -----------------------------------------------------
        # MINIMUM
        # -----------------------------------------------------

        if any(
            word in question_lower
            for word in [
                "minimum",
                "min",
            ]
        ):
            return "min"

        # -----------------------------------------------------
        # MAXIMUM
        # -----------------------------------------------------

        if any(
            word in question_lower
            for word in [
                "maximum",
                "max",
            ]
        ):
            return "max"

        # -----------------------------------------------------
        # TOP / BOTTOM
        #
        # Top/bottom questions usually ask which groups
        # have the greatest/smallest total value.
        # -----------------------------------------------------

        if any(
            word in question_lower
            for word in [
                "top",
                "bottom",
            ]
        ):
            return "sum"

        # -----------------------------------------------------
        # "highest" / "lowest" by themselves
        # -----------------------------------------------------

        if any(
            word in question_lower
            for word in [
                "highest",
                "largest",
            ]
        ):
            return "max"

        if any(
            word in question_lower
            for word in [
                "lowest",
                "smallest",
            ]
        ):
            return "min"

        return None

    # =========================================================
    # VALIDATION
    # =========================================================

    @staticmethod
    def _validate_operation(
        operation: dict[str, Any],
        schema_summary: str
    ) -> None:

        if not isinstance(operation, dict):
            raise ValueError(
                "Parser result must be a JSON object."
            )

        operation_type = operation.get(
            "operation"
        )

        allowed = {
            "aggregate",
            "count",
            "groupby_aggregate",
            "value_count",
            "filter",
            "unsupported",
        }

        if operation_type not in allowed:
            raise ValueError(
                f"Unsupported operation returned by LLM: "
                f"{operation_type}"
            )

        if operation_type == "unsupported":

            if not operation.get("reason"):
                raise ValueError(
                    "Unsupported operation must include a reason."
                )

        if operation_type == "aggregate":
            required = [
                "value_column",
                "aggregation",
            ]

        elif operation_type == "groupby_aggregate":
            required = [
                "group_column",
                "value_column",
                "aggregation",
            ]

        elif operation_type == "value_count":
            required = [
                "group_column"
            ]

        elif operation_type == "filter":
            required = [
                "column",
                "operator",
                "value",
            ]

        else:
            required = []

        missing = [
            field
            for field in required
            if field not in operation
        ]

        if missing:
            raise ValueError(
                f"Parser response is missing fields: "
                f"{missing}"
            )

        if operation_type in {
            "aggregate",
            "groupby_aggregate",
        }:

            aggregation = operation.get(
                "aggregation"
            )

            if aggregation not in {
                "sum",
                "mean",
                "min",
                "max",
                "median",
            }:
                raise ValueError(
                    f"Invalid aggregation: {aggregation}"
                )

        if operation_type == "filter":

            valid_operators = {
                "equals",
                "not_equals",
                "greater_than",
                "less_than",
                "greater_or_equal",
                "less_or_equal",
                "contains",
            }

            if operation["operator"] not in valid_operators:
                raise ValueError(
                    f"Invalid filter operator: "
                    f"{operation['operator']}"
                )
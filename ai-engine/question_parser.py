import os
import re
import json
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


load_dotenv()


class QuestionParser:
    """
    Converts a natural-language question into a structured analysis operation.

    OpenAI is used when available.
    If OpenAI is unavailable, a local rule-based parser is used.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None

        if self.api_key and OpenAI is not None:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception:
                self.client = None

    # ---------------------------------------------------------
    # PUBLIC METHOD
    # ---------------------------------------------------------

    def parse(self, question: str, schema_summary: str) -> Dict[str, Any]:

        question = question.strip()

        if not question:
            return {
                "operation": "unsupported",
                "reason": "Question cannot be empty."
            }

        # Try OpenAI first
        if self.client:
            try:
                result = self._parse_with_openai(
                    question,
                    schema_summary
                )

                if result:
                    return result

            except Exception as exc:
                print(f"[INFO] OpenAI unavailable: {exc}")

        # Local fallback
        print("[INFO] Switching to local fallback parser...")

        return self._parse_locally(
            question,
            schema_summary
        )

    # ---------------------------------------------------------
    # OPENAI PARSER
    # ---------------------------------------------------------

    def _parse_with_openai(
        self,
        question: str,
        schema_summary: str
    ) -> Optional[Dict[str, Any]]:

        prompt = f"""
You are a data-analysis intent parser.

The user has uploaded a dataset.

Dataset schema:
{schema_summary}

User question:
{question}

Return ONLY valid JSON.

Supported operations:

1. aggregate
{{
    "operation": "aggregate",
    "value_column": "column",
    "aggregation": "sum|mean|median|min|max"
}}

2. count
{{
    "operation": "count"
}}

3. groupby_aggregate
{{
    "operation": "groupby_aggregate",
    "group_column": "column",
    "value_column": "column",
    "aggregation": "sum|mean|median|min|max",
    "sort": "ascending|descending",
    "limit": 1
}}

4. value_count
{{
    "operation": "value_count",
    "column": "column"
}}

5. filter
{{
    "operation": "filter",
    "column": "column",
    "operator": "==|!=|>|<|>=|<=",
    "value": "value"
}}

6. duplicate_detection
{{
    "operation": "duplicate_detection"
}}

7. anomaly_detection
{{
    "operation": "anomaly_detection",
    "columns": ["numeric_column"]
}}

8. pattern_detection
{{
    "operation": "pattern_detection",
    "columns": ["column1", "column2"]
}}

9. recommendation
{{
    "operation": "recommendation"
}}

10. unsupported
{{
    "operation": "unsupported",
    "reason": "reason"
}}

Rules:

- Use only columns that exist in the schema.
- Do not invent column names.
- For questions such as:
  "Which country has the highest total quantity?"
  group_column = Country
  value_column = Quantity
  aggregation = sum
  sort = descending
  limit = 1

- For:
  "What are the top 5 countries by total quantity?"
  group_column = Country
  value_column = Quantity
  aggregation = sum
  sort = descending
  limit = 5

- For:
  "What are the bottom 3 countries by total quantity?"
  group_column = Country
  value_column = Quantity
  aggregation = sum
  sort = ascending
  limit = 3

Return JSON only.
"""

        response = self.client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        text = response.output_text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    # ---------------------------------------------------------
    # LOCAL PARSER
    # ---------------------------------------------------------

    def _parse_locally(
        self,
        question: str,
        schema_summary: str
    ) -> Dict[str, Any]:

        question_lower = question.lower()

        columns = self._extract_columns(
            schema_summary
        )

        # -----------------------------------------------------
        # DUPLICATE DETECTION
        # -----------------------------------------------------

        duplicate_phrases = [
            "duplicate",
            "duplicates",
            "duplicated records",
            "duplicate records",
            "duplicate rows",
            "repeated records",
            "repeated rows"
        ]

        if any(
            phrase in question_lower
            for phrase in duplicate_phrases
        ):
            return {
                "operation": "duplicate_detection"
            }

        # -----------------------------------------------------
        # ANOMALY DETECTION
        # -----------------------------------------------------

        anomaly_phrases = [
            "anomaly",
            "anomalies",
            "anomalous",
            "outlier",
            "outliers",
            "unusual",
            "unusual values",
            "anything unusual",
            "abnormal",
            "abnormalities"
        ]

        if any(
            phrase in question_lower
            for phrase in anomaly_phrases
        ):

            numeric_columns = [
                column["name"]
                for column in columns
                if column["semantic_type"] == "numeric"
            ]

            mentioned_numeric_columns = []

            for column in columns:

                if column["semantic_type"] != "numeric":
                    continue

                if self._column_mentioned(
                    column["name"],
                    question_lower
                ):
                    mentioned_numeric_columns.append(
                        column["name"]
                    )

            if mentioned_numeric_columns:
                numeric_columns = mentioned_numeric_columns

            return {
                "operation": "anomaly_detection",
                "columns": numeric_columns
            }

        # -----------------------------------------------------
        # PATTERN / TREND DETECTION
        # -----------------------------------------------------

        pattern_phrases = [
            "what patterns",
            "patterns do you see",
            "find patterns",
            "interesting patterns",
            "trends",
            "trend",
            "what is happening",
            "what do you notice",
            "insights from the data",
            "interesting insights",
            "analyze this data",
            "analyse this data"
        ]

        if any(
            phrase in question_lower
            for phrase in pattern_phrases
        ):
            return {
                "operation": "pattern_detection",
                "columns": [
                    column["name"]
                    for column in columns
                ]
            }

        # -----------------------------------------------------
        # RECOMMENDATIONS
        # -----------------------------------------------------

        recommendation_phrases = [
            "what should i do",
            "what should we do",
            "what can i do",
            "what can we do",
            "how can i improve",
            "how can we improve",
            "how to improve",
            "how can i increase",
            "how can we increase",
            "how to increase",
            "increase sales",
            "increase revenue",
            "grow sales",
            "grow revenue",
            "improve sales",
            "improve revenue",
            "what actions should i take",
            "what actions should we take",
            "recommendations",
            "recommendation",
            "suggestions",
            "suggest"
        ]

        if any(
            phrase in question_lower
            for phrase in recommendation_phrases
        ):
            return {
                "operation": "recommendation"
            }

        # -----------------------------------------------------
        # COUNT
        # -----------------------------------------------------

        count_phrases = [
            "how many records",
            "how many rows",
            "number of records",
            "number of rows",
            "record count",
            "row count",
            "how many entries",
            "how many items"
        ]

        if any(
            phrase in question_lower
            for phrase in count_phrases
        ):
            return {
                "operation": "count"
            }

        # -----------------------------------------------------
        # AGGREGATION
        # -----------------------------------------------------

        aggregation = self._detect_aggregation(
            question_lower
        )

        # -----------------------------------------------------
        # GROUP + VALUE DETECTION
        # -----------------------------------------------------

        (
            group_column,
            value_column
        ) = self._find_group_and_value_columns(
            question_lower,
            columns
        )

        # -----------------------------------------------------
        # TOP / BOTTOM N
        # -----------------------------------------------------

        number_match = re.search(
            r"\b(top|bottom)\s+(\d+)\b",
            question_lower
        )

        if number_match:

            limit = int(
                number_match.group(2)
            )

            direction = number_match.group(1)

            sort = (
                "descending"
                if direction == "top"
                else "ascending"
            )

            if group_column and value_column:

                return {
                    "operation": "groupby_aggregate",
                    "group_column": group_column,
                    "value_column": value_column,
                    "aggregation": aggregation or "sum",
                    "sort": sort,
                    "limit": limit
                }

        # -----------------------------------------------------
        # HIGHEST / LOWEST
        # -----------------------------------------------------

        if any(
            phrase in question_lower
            for phrase in [
                "highest",
                "largest",
                "most",
                "maximum",
                "max"
            ]
        ):

            if group_column and value_column:

                return {
                    "operation": "groupby_aggregate",
                    "group_column": group_column,
                    "value_column": value_column,
                    "aggregation": aggregation or "sum",
                    "sort": "descending",
                    "limit": 1
                }

        if any(
            phrase in question_lower
            for phrase in [
                "lowest",
                "smallest",
                "least",
                "minimum",
                "min"
            ]
        ):

            if group_column and value_column:

                return {
                    "operation": "groupby_aggregate",
                    "group_column": group_column,
                    "value_column": value_column,
                    "aggregation": aggregation or "sum",
                    "sort": "ascending",
                    "limit": 1
                }

        # -----------------------------------------------------
        # BY GROUP
        # -----------------------------------------------------

        if group_column and value_column:

            if " by " in question_lower:

                return {
                    "operation": "groupby_aggregate",
                    "group_column": group_column,
                    "value_column": value_column,
                    "aggregation": aggregation or "sum"
                }

        # -----------------------------------------------------
        # VALUE COUNT
        # -----------------------------------------------------

        value_count_phrases = [
            "how many different",
            "how many unique",
            "unique values",
            "different values",
            "value counts",
            "frequency of"
        ]

        if any(
            phrase in question_lower
            for phrase in value_count_phrases
        ):

            column = self._find_column(
                question_lower,
                columns
            )

            if column:
                return {
                    "operation": "value_count",
                    "column": column
                }

        # -----------------------------------------------------
        # SIMPLE AGGREGATE
        # -----------------------------------------------------

        value_column = (
            value_column
            or self._find_numeric_column(
                question_lower,
                columns
            )
        )

        if value_column and aggregation:

            return {
                "operation": "aggregate",
                "value_column": value_column,
                "aggregation": aggregation
            }

        # -----------------------------------------------------
        # UNSUPPORTED
        # -----------------------------------------------------

        return {
            "operation": "unsupported",
            "reason": (
                "The question could not be mapped to a "
                "supported data-analysis operation."
            )
        }

    # ---------------------------------------------------------
    # EXTRACT COLUMNS FROM SCHEMA
    # ---------------------------------------------------------

    def _extract_columns(
        self,
        schema_summary: str
    ) -> List[Dict[str, str]]:

        columns = []

        for line in schema_summary.splitlines():

            line = line.strip()

            if not line.startswith("-"):
                continue

            # Example:
            # - Quantity | type=numeric | dtype=int64

            parts = [
                part.strip()
                for part in line[1:].split("|")
            ]

            if not parts:
                continue

            name = parts[0]

            semantic_type = "categorical"

            for part in parts[1:]:

                if part.startswith("type="):
                    semantic_type = part.split(
                        "=",
                        1
                    )[1].strip()

                elif part.startswith("semantic_type="):
                    semantic_type = part.split(
                        "=",
                        1
                    )[1].strip()

            columns.append({
                "name": name,
                "semantic_type": semantic_type
            })

        return columns

    # ---------------------------------------------------------
    # FIND COLUMN
    # ---------------------------------------------------------

    def _find_column(
        self,
        question: str,
        columns: List[Dict[str, str]]
    ) -> Optional[str]:

        question_lower = question.lower()

        # Exact column-name matching first
        for column in columns:

            name = column["name"]

            if name.lower() in question_lower:
                return name

        # Word-based matching
        for column in columns:

            name = column["name"].lower()

            words = re.findall(
                r"[a-zA-Z0-9]+",
                name
            )

            for word in words:

                if len(word) <= 2:
                    continue

                if re.search(
                    rf"\b{re.escape(word)}\w*\b",
                    question_lower
                ):
                    return column["name"]

                # Handle:
                # country -> countries
                # category -> categories
                # company -> companies

                if word.endswith("y"):

                    plural_form = (
                        word[:-1] + "ies"
                    )

                    if re.search(
                        rf"\b{re.escape(plural_form)}\b",
                        question_lower
                    ):
                        return column["name"]

        return None

    # ---------------------------------------------------------
    # FIND NUMERIC COLUMN
    # ---------------------------------------------------------

    def _find_numeric_column(
        self,
        question: str,
        columns: List[Dict[str, str]]
    ) -> Optional[str]:

        numeric_columns = [
            column
            for column in columns
            if column["semantic_type"] == "numeric"
        ]

        # Exact match
        for column in numeric_columns:

            if column["name"].lower() in question:
                return column["name"]

        # Word/plural match
        for column in numeric_columns:

            name = column["name"].lower()

            words = re.findall(
                r"[a-zA-Z0-9]+",
                name
            )

            for word in words:

                if len(word) <= 2:
                    continue

                if re.search(
                    rf"\b{re.escape(word)}\w*\b",
                    question
                ):
                    return column["name"]

                if word.endswith("y"):

                    plural_form = (
                        word[:-1] + "ies"
                    )

                    if re.search(
                        rf"\b{re.escape(plural_form)}\b",
                        question
                    ):
                        return column["name"]

        # If exactly one numeric column exists
        if len(numeric_columns) == 1:
            return numeric_columns[0]["name"]

        return None

    # ---------------------------------------------------------
    # FIND GROUP + VALUE COLUMNS
    # ---------------------------------------------------------

    def _find_group_and_value_columns(
        self,
        question: str,
        columns: List[Dict[str, str]]
    ):

        group_column = None
        value_column = None

        categorical_columns = [
            column
            for column in columns
            if column["semantic_type"]
            in ["categorical", "text"]
        ]

        numeric_columns = [
            column
            for column in columns
            if column["semantic_type"] == "numeric"
        ]

        # -----------------------------------------------------
        # CASE 1:
        # "top 5 countries by total quantity"
        # -----------------------------------------------------

        if " by " in question:

            before_by, after_by = question.split(
                " by ",
                1
            )

            group_text = before_by
            value_text = after_by

            # Find GROUP column
            for column in categorical_columns:

                name = column["name"]

                words = re.findall(
                    r"[a-zA-Z0-9]+",
                    name.lower()
                )

                for word in words:

                    if len(word) <= 2:
                        continue

                    # Direct / prefix match
                    #
                    # product -> products
                    # region -> regions
                    # country -> country
                    if re.search(
                        rf"\b{re.escape(word)}\w*\b",
                        group_text
                    ):
                        group_column = name
                        break

                    # -----------------------------------------
                    # IMPORTANT PLURAL FIX
                    #
                    # country -> countries
                    # category -> categories
                    # company -> companies
                    # -----------------------------------------

                    if word.endswith("y"):

                        plural_form = (
                            word[:-1] + "ies"
                        )

                        if re.search(
                            rf"\b{re.escape(plural_form)}\b",
                            group_text
                        ):
                            group_column = name
                            break

                if group_column:
                    break

            # Find VALUE column
            for column in numeric_columns:

                name = column["name"]

                words = re.findall(
                    r"[a-zA-Z0-9]+",
                    name.lower()
                )

                for word in words:

                    if len(word) <= 2:
                        continue

                    if re.search(
                        rf"\b{re.escape(word)}\w*\b",
                        value_text
                    ):
                        value_column = name
                        break

                    if word.endswith("y"):

                        plural_form = (
                            word[:-1] + "ies"
                        )

                        if re.search(
                            rf"\b{re.escape(plural_form)}\b",
                            value_text
                        ):
                            value_column = name
                            break

                if value_column:
                    break

            if group_column and value_column:
                return group_column, value_column

        # -----------------------------------------------------
        # CASE 2:
        # "which country has highest quantity?"
        # -----------------------------------------------------

        comparison_words = [
            "highest",
            "largest",
            "most",
            "lowest",
            "smallest",
            "least",
            "maximum",
            "minimum",
            "top",
            "bottom"
        ]

        has_comparison = any(
            word in question
            for word in comparison_words
        )

        if has_comparison:

            # Find categorical/group column
            for column in categorical_columns:

                if self._column_mentioned(
                    column["name"],
                    question
                ):
                    group_column = column["name"]
                    break

            # Find numeric/value column
            for column in numeric_columns:

                if self._column_mentioned(
                    column["name"],
                    question
                ):
                    value_column = column["name"]
                    break

            if group_column and value_column:
                return group_column, value_column

        # -----------------------------------------------------
        # GENERAL FALLBACK
        # -----------------------------------------------------

        possible_group = self._find_column(
            question,
            categorical_columns
        )

        possible_value = self._find_numeric_column(
            question,
            columns
        )

        return (
            possible_group,
            possible_value
        )

    # ---------------------------------------------------------
    # COLUMN MENTION HELPER
    # ---------------------------------------------------------

    def _column_mentioned(
        self,
        column_name: str,
        question: str
    ) -> bool:

        column_lower = column_name.lower()

        # Full column name
        if column_lower in question:
            return True

        words = re.findall(
            r"[a-zA-Z0-9]+",
            column_lower
        )

        for word in words:

            if len(word) <= 2:
                continue

            # Normal plural / prefix
            if re.search(
                rf"\b{re.escape(word)}\w*\b",
                question
            ):
                return True

            # country -> countries
            # category -> categories
            if word.endswith("y"):

                plural_form = (
                    word[:-1] + "ies"
                )

                if re.search(
                    rf"\b{re.escape(plural_form)}\b",
                    question
                ):
                    return True

        return False

    # ---------------------------------------------------------
    # DETECT AGGREGATION
    # ---------------------------------------------------------

    def _detect_aggregation(
        self,
        question: str
    ) -> Optional[str]:

        # SUM
        if any(
            phrase in question
            for phrase in [
                "total",
                "sum",
                "overall",
                "combined"
            ]
        ):
            return "sum"

        # MEAN
        if any(
            phrase in question
            for phrase in [
                "average",
                "avg",
                "mean"
            ]
        ):
            return "mean"

        # MEDIAN
        if "median" in question:
            return "median"

        # MAX
        if any(
            phrase in question
            for phrase in [
                "maximum",
                "max"
            ]
        ):
            return "max"

        # MIN
        if any(
            phrase in question
            for phrase in [
                "minimum",
                "min"
            ]
        ):
            return "min"

        # For top/bottom questions,
        # the value is normally SUM.
        if any(
            phrase in question
            for phrase in [
                "top",
                "bottom",
                "highest",
                "lowest",
                "largest",
                "smallest",
                "most",
                "least"
            ]
        ):
            return "sum"

        return None
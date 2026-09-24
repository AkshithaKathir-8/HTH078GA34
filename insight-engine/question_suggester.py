import pandas as pd


def find_time_column(df):
    """Find a possible date/time column."""

    for column in df.columns:

        name = column.lower()

        # First check the column name
        if any(word in name for word in [
            "date", "time", "month", "year", "day"
        ]):
            return column

        # Only try date conversion for text columns
        if df[column].dtype == "object":

            converted = pd.to_datetime(
                df[column],
                errors="coerce",
                format="mixed"
            )

            if converted.notna().sum() >= len(df) * 0.7:
                return column

    return None


def get_meaningful_categories(df):
    """Find categorical columns that are useful for analysis."""

    categories = []

    for column in df.select_dtypes(
        include=["object", "category"]
    ).columns:

        unique_count = df[column].nunique()

        # Ignore columns where every value is different
        if unique_count >= len(df):
            continue

        # Ignore columns with too many unique categories
        if unique_count > max(20, len(df) * 0.5):
            continue

        categories.append(column)

    return categories


def suggest_questions(df):

    questions = []

    # Numeric columns
    numeric_columns = list(
        df.select_dtypes(include="number").columns
    )

    # Meaningful categorical columns
    categorical_columns = get_meaningful_categories(df)

    # Possible time column
    time_column = find_time_column(df)

    # 1. Questions based on time
    if time_column and numeric_columns:

        number = numeric_columns[0]

        questions.append(
            f"Which {time_column} had the highest {number}?"
        )

        questions.append(
            f"How did {number} change over time?"
        )

    # 2. Questions based on categories
    if categorical_columns and numeric_columns:

        category = categorical_columns[0]
        number = numeric_columns[0]

        questions.append(
            f"Which {category} has the highest average {number}?"
        )

        questions.append(
            f"What is the average {number} for each {category}?"
        )

    # 3. General numerical questions
    for column in numeric_columns[:2]:

        questions.append(
            f"What is the highest {column}?"
        )

        questions.append(
            f"What is the average {column}?"
        )

    # Remove duplicate questions
    questions = list(dict.fromkeys(questions))

    # Return maximum 5
    return questions[:5]
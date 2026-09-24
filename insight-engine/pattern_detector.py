import pandas as pd


def detect_patterns(df):

    patterns = []

    # Select numeric columns
    numeric_df = df.select_dtypes(
        include="number"
    )

    # Need at least 2 numeric columns
    if numeric_df.shape[1] < 2:
        return patterns

    # Calculate correlation
    correlation = numeric_df.corr()

    columns = correlation.columns

    # Compare every pair of columns
    for i in range(len(columns)):

        for j in range(i + 1, len(columns)):

            column1 = columns[i]
            column2 = columns[j]

            value = correlation.iloc[i, j]

            # Ignore missing values
            if pd.isna(value):
                continue

            # Determine relationship
            if value >= 0.7:

                if value >= 0.9:
                    strength = "very strong"
                else:
                    strength = "strong"

                patterns.append({
                    "columns": [column1, column2],
                    "correlation": round(value, 2),
                    "type": "positive",
                    "strength": strength,
                    "message": (
                        f"{column1} and {column2} show a "
                        f"{strength} positive relationship "
                        f"(correlation: {value:.2f})."
                    )
                })

            elif value <= -0.7:

                if value <= -0.9:
                    strength = "very strong"
                else:
                    strength = "strong"

                patterns.append({
                    "columns": [column1, column2],
                    "correlation": round(value, 2),
                    "type": "negative",
                    "strength": strength,
                    "message": (
                        f"{column1} and {column2} show a "
                        f"{strength} negative relationship "
                        f"(correlation: {value:.2f})."
                    )
                })

    return patterns
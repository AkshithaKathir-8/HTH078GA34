import pandas as pd


def find_time_column(df):
    """
    Find a possible date/time column.
    """

    for column in df.columns:

        name = column.lower()

        if any(word in name for word in [
            "date",
            "time",
            "month",
            "year",
            "day"
        ]):
            return column

        converted = pd.to_datetime(
            df[column],
            errors="coerce"
        )

        if converted.notna().sum() >= len(df) * 0.7:
            return column

    return None


def detect_trends(df):

    trends = []

    # Find time column
    time_column = find_time_column(df)

    if time_column is None:
        return trends

    # Copy dataframe
    data = df.copy()

    # Convert time column
    data[time_column] = pd.to_datetime(
        data[time_column],
        errors="coerce"
    )

    # Remove invalid dates
    data = data.dropna(subset=[time_column])

    # Sort by time
    data = data.sort_values(time_column)

    # Get numeric columns
    numeric_columns = data.select_dtypes(
        include="number"
    ).columns

    for column in numeric_columns:

        values = data[column].dropna()

        if len(values) < 3:
            continue

        first_value = values.iloc[0]
        last_value = values.iloc[-1]

        if first_value == 0:
            continue

        # Calculate overall percentage change
        percentage_change = (
            (last_value - first_value)
            / abs(first_value)
        ) * 100

        # Calculate number of increases/decreases
        differences = values.diff().dropna()

        increases = (differences > 0).sum()
        decreases = (differences < 0).sum()

        total_changes = len(differences)

        # Calculate consistency
        if total_changes > 0:
            increase_ratio = increases / total_changes
            decrease_ratio = decreases / total_changes
        else:
            increase_ratio = 0
            decrease_ratio = 0

        # Significant increasing trend
        if (
            percentage_change >= 20
            and increase_ratio >= 0.5
        ):

            trends.append({
                "column": column,
                "change_percent": round(
                    percentage_change, 2
                ),
                "type": "increase",
                "message": (
                    f"{column} shows an increasing trend "
                    f"with a {percentage_change:.1f}% "
                    f"overall increase."
                )
            })

        # Significant decreasing trend
        elif (
            percentage_change <= -20
            and decrease_ratio >= 0.5
        ):

            trends.append({
                "column": column,
                "change_percent": round(
                    percentage_change, 2
                ),
                "type": "decrease",
                "message": (
                    f"{column} shows a decreasing trend "
                    f"with a {abs(percentage_change):.1f}% "
                    f"overall decrease."
                )
            })

    return trends
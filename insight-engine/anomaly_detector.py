import pandas as pd


def detect_anomalies(df):

    anomalies = []

    # Get only numeric columns
    numeric_columns = df.select_dtypes(
        include="number"
    ).columns

    for column in numeric_columns:

        # Remove empty values
        data = df[column].dropna()

        # Need enough data for anomaly detection
        if len(data) < 4:
            continue

        # Calculate Q1 and Q3
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)

        # Calculate IQR
        IQR = Q3 - Q1

        # Calculate limits
        lower_limit = Q1 - 1.5 * IQR
        upper_limit = Q3 + 1.5 * IQR

        # Find unusual values
        unusual_rows = df[
            (df[column] < lower_limit) |
            (df[column] > upper_limit)
        ]

        # Store detected anomalies
        for index, row in unusual_rows.iterrows():

            value = row[column]

            if value > upper_limit:
                reason = "unusually high"

            else:
                reason = "unusually low"

            anomalies.append({

                "column": column,

                "row": int(index),

                "value": value,

                "lower_limit": round(
                    lower_limit, 2
                ),

                "upper_limit": round(
                    upper_limit, 2
                ),

                "reason": reason,

                "message": (
                    f"{column} has an {reason} "
                    f"value of {value}."
                )
            })

    return anomalies
from anomaly_detector import detect_anomalies
from pattern_detector import detect_patterns
from trend_detector import detect_trends
from question_suggester import suggest_questions


def generate_insights(df):

    # Detect insights
    anomalies = detect_anomalies(df)

    patterns = detect_patterns(df)

    trends = detect_trends(df)

    follow_up_questions = suggest_questions(df)

    # Dataset summary
    summary = {
        "rows": len(df),
        "columns": len(df.columns),
        "numeric_columns": list(
            df.select_dtypes(include="number").columns
        ),
        "categorical_columns": list(
            df.select_dtypes(
                include=["object", "category"]
            ).columns
        )
    }

    # Final result
    result = {
        "summary": summary,
        "anomalies": anomalies,
        "patterns": patterns,
        "trends": trends,
        "follow_up_questions": follow_up_questions
    }

    return result
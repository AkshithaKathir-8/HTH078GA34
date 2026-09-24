from pathlib import Path
import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def load_dataset(file_path: str) -> pd.DataFrame:
    """
    Load a CSV or Excel dataset into a Pandas DataFrame.

    Supports:
    - .csv
    - .xlsx
    - .xls
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    try:
        if extension == ".csv":
            df = pd.read_csv(path)

        else:
            df = pd.read_excel(path)

    except Exception as exc:
        raise ValueError(f"Could not read dataset: {exc}") from exc

    if df.empty:
        raise ValueError("The uploaded dataset is empty.")

    # Remove completely empty rows and columns.
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")

    if df.empty or len(df.columns) == 0:
        raise ValueError("The dataset contains no usable data.")

    # Clean column names while preserving their meaning.
    df.columns = [
        str(column).strip() if str(column).strip() else f"column_{index}"
        for index, column in enumerate(df.columns)
    ]

    return df
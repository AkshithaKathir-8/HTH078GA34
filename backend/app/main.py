from io import BytesIO
from pathlib import Path
import math
import uuid
import sys

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# PATHS AND CONFIGURATION
# ---------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
UPLOAD_DIR = BACKEND_DIR / "uploaded_data"
AI_ENGINE_DIR = PROJECT_DIR / "ai-engine"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allow Python to locate the teammate's AI-engine module.
if str(AI_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_DIR))


# ---------------------------------------------------------
# FASTAPI APPLICATION
# ---------------------------------------------------------

app = FastAPI(
    title="Data Detective AI",
    description=(
        "Upload datasets, inspect their structure, and ask "
        "natural-language questions about the data."
    ),
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

MAX_FILE_SIZE = 20 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".csv",
    ".xlsx",
    ".xls",
}

# Temporary dataset metadata.
# The actual files are saved under backend/uploaded_data.
DATASETS = {}


# ---------------------------------------------------------
# REQUEST MODEL
# ---------------------------------------------------------

class AnalysisRequest(BaseModel):
    dataset_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, max_length=2000)
    api_key: str | None = None


# ---------------------------------------------------------
# DATA CONVERSION HELPERS
# ---------------------------------------------------------

def json_safe(value):
    """Convert Pandas and NumPy values into JSON-compatible values."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        try:
            value = value.item()
        except (ValueError, TypeError):
            pass

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, float) and not math.isfinite(value):
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


# ---------------------------------------------------------
# FILE READING
# ---------------------------------------------------------

def read_csv_file(contents: bytes) -> pd.DataFrame:
    """Read CSV files using common encodings."""

    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1"]

    for encoding in encodings:
        try:
            return pd.read_csv(
                BytesIO(contents),
                encoding=encoding,
                low_memory=False,
            )
        except UnicodeDecodeError:
            continue

    raise ValueError(
        "Could not decode the CSV file. Please check its encoding."
    )


def read_dataset(filename: str, contents: bytes) -> pd.DataFrame:
    """Read a supported CSV or Excel file into a DataFrame."""

    extension = Path(filename).suffix.lower()

    if extension == ".csv":
        return read_csv_file(contents)

    if extension == ".xlsx":
        return pd.read_excel(
            BytesIO(contents),
            engine="openpyxl",
        )

    if extension == ".xls":
        return pd.read_excel(
            BytesIO(contents),
            engine="xlrd",
        )

    raise ValueError(
        "Unsupported file type. Upload a CSV or Excel file."
    )


# ---------------------------------------------------------
# DATASET SUMMARY
# ---------------------------------------------------------

def build_dataset_summary(df: pd.DataFrame, filename: str) -> dict:
    """Infer the dataset schema and generate a summary."""

    columns = []

    for column in df.columns:
        series = df[column]

        columns.append({
            "name": str(column),
            "data_type": str(series.dtype),
            "non_null_count": int(series.count()),
            "missing_count": int(series.isna().sum()),
            "unique_count": int(series.nunique(dropna=True)),
            "sample_values": [
                json_safe(value)
                for value in series.dropna().head(5).tolist()
            ],
        })

    numeric_columns = df.select_dtypes(include="number").columns
    numeric_summary = {}

    for column in numeric_columns:
        stats = df[column].describe()

        numeric_summary[str(column)] = {
            str(key): json_safe(value)
            for key, value in stats.to_dict().items()
        }

    preview = [
        {
            str(column): json_safe(value)
            for column, value in row.items()
        }
        for row in df.head(10).to_dict(orient="records")
    ]

    return {
        "filename": filename,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": columns,
        "numeric_summary": numeric_summary,
        "preview": preview,
    }


# ---------------------------------------------------------
# BASIC ENDPOINTS
# ---------------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Data Detective AI backend is running!"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# ---------------------------------------------------------
# UPLOAD ENDPOINT
# ---------------------------------------------------------

@app.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Upload a CSV or Excel file, save it to disk,
    infer its schema, and return a unique dataset ID.
    """

    filename = file.filename or ""

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="No filename was provided.",
        )

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Upload a CSV, XLSX, or XLS file.",
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="The maximum upload size is 20 MB.",
        )

    dataset_id = str(uuid.uuid4())

    # Use a generated filename rather than trusting the user's filename.
    saved_filename = f"{dataset_id}{extension}"
    saved_path = UPLOAD_DIR / saved_filename

    try:
        df = read_dataset(filename, contents)

        if df.empty or len(df.columns) == 0:
            raise HTTPException(
                status_code=400,
                detail="The dataset contains no usable rows or columns.",
            )

        # Remove accidental spaces around column names.
        df.columns = [str(column).strip() for column in df.columns]

        # Save the original uploaded file so the AI engine can read it.
        saved_path.write_bytes(contents)

        DATASETS[dataset_id] = {
            "filename": filename,
            "file_path": str(saved_path.resolve()),
        }

        summary = build_dataset_summary(df, filename)

        return {
            "success": True,
            "message": "Dataset uploaded and analyzed successfully.",
            "dataset_id": dataset_id,
            "dataset": summary,
        }

    except HTTPException:
        raise

    except (
        ValueError,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
    ) as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read the dataset: {str(error)}",
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the dataset.",
        ) from error

    finally:
        await file.close()


# ---------------------------------------------------------
# GET DATASET SUMMARY
# ---------------------------------------------------------

@app.get("/dataset/{dataset_id}")
def get_dataset_summary(dataset_id: str):
    """Return the summary of a dataset uploaded during this session."""

    stored_dataset = DATASETS.get(dataset_id)

    if stored_dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Please upload the file again.",
        )

    file_path = Path(stored_dataset["file_path"])

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="The stored dataset file could not be found. Please upload it again.",
        )

    try:
        df = read_dataset(
            stored_dataset["filename"],
            file_path.read_bytes(),
        )

        df.columns = [str(column).strip() for column in df.columns]

        return {
            "success": True,
            "dataset_id": dataset_id,
            "dataset": build_dataset_summary(
                df,
                stored_dataset["filename"],
            ),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve the dataset summary.",
        ) from error


# ---------------------------------------------------------
# NATURAL-LANGUAGE ANALYSIS ENDPOINT
# ---------------------------------------------------------

@app.post("/analyze")
def analyze_dataset_question(request: AnalysisRequest):
    """
    Send the saved dataset path and user's question to the AI engine.
    Return the AI engine's analysis dictionary.
    """

    dataset_id = request.dataset_id
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please enter a question about your dataset.",
        )

    stored_dataset = DATASETS.get(dataset_id)

    if stored_dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Please upload the file again.",
        )

    file_path = Path(stored_dataset["file_path"])

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="The uploaded dataset file is missing. Please upload it again.",
        )

    # Import only when analysis is requested.
    # This allows the upload endpoint to work before the engine is merged.
    try:
        from analyzer import analyze_dataset

    except ImportError as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "The AI engine is not available yet. "
                "Make sure ai-engine/analyzer.py has been added and "
                "contains the analyze_dataset function."
            ),
        ) from error

    try:
        result = analyze_dataset(
            str(file_path),
            question,
            api_key=request.api_key,
        )

        if not isinstance(result, dict):
            raise HTTPException(
                status_code=500,
                detail="The AI engine returned an unexpected response format.",
            )

        if "success" not in result or "answer" not in result:
            raise HTTPException(
                status_code=500,
                detail="The AI engine response is missing required fields.",
            )

        return result

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(error)}",
        ) from error
import { useState } from "react";
import Papa from "papaparse";
import * as XLSX from "xlsx";
import Chart from "./Chart";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [data, setData] = useState([]);
  const [columns, setColumns] = useState([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [calculation, setCalculation] = useState("");
  const [insights, setInsights] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [chartType, setChartType] = useState("bar");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];

    if (!selectedFile) return;

    setFile(selectedFile);
    setError("");
    setAnswer("");
    setCalculation("");
    setInsights([]);
    setChartData([]);
    setChartType("bar");

    const fileName = selectedFile.name.toLowerCase();

    // =========================
    // CSV UPLOAD
    // =========================
    if (fileName.endsWith(".csv")) {
      Papa.parse(selectedFile, {
        header: true,
        skipEmptyLines: true,

        complete: (result) => {
          const rows = result.data;

          setData(rows);

          if (rows.length > 0) {
            const detectedColumns = Object.keys(rows[0]);

            setColumns(detectedColumns);

const sampleRows = rows.slice(0, 100);

detectLocalInsights(sampleRows, detectedColumns);
generateChartFromData(sampleRows, detectedColumns);

            // Automatically create chart from uploaded data
            
          } else {
            setColumns([]);
            setError("The CSV file does not contain any data.");
          }
        },

        error: (parseError) => {
          console.error(parseError);
          setError("Unable to read the CSV file.");
        },
      });

      return;
    }

    // =========================
    // EXCEL UPLOAD
    // =========================
    if (fileName.endsWith(".xlsx") || fileName.endsWith(".xls")) {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const workbook = XLSX.read(e.target.result, {
            type: "array",
          });

          const firstSheetName = workbook.SheetNames[0];

          const worksheet = workbook.Sheets[firstSheetName];

          const rows = XLSX.utils.sheet_to_json(worksheet, {
            defval: "",
          });

          setData(rows);

          if (rows.length > 0) {
            const detectedColumns = Object.keys(rows[0]);

            setColumns(detectedColumns);

const sampleRows = rows.slice(0, 100);

detectLocalInsights(sampleRows, detectedColumns);
generateChartFromData(sampleRows, detectedColumns);
            // Automatically create chart from uploaded data
           
          } else {
            setColumns([]);
            setError("The Excel file does not contain any data.");
          }
        } catch (readError) {
          console.error(readError);
          setError("Unable to read the Excel file.");
        }
      };

      reader.readAsArrayBuffer(selectedFile);

      return;
    }

    setError("Please upload a CSV, XLS, or XLSX file.");
  };

  // =========================
  // AUTOMATIC CHART GENERATION
  // =========================
  const generateChartFromData = (rows, cols) => {
    if (!rows || rows.length === 0 || !cols || cols.length === 0) {
      setChartData([]);
      return;
    }

    // Check whether a value is actually numeric
    const isNumeric = (value) => {
      if (
        value === undefined ||
        value === null ||
        String(value).trim() === ""
      ) {
        return false;
      }

      return !Number.isNaN(Number(value));
    };

    // Check whether a value looks like a date
    const isDateValue = (value) => {
      if (!value) return false;

      const stringValue = String(value).trim();

      // Avoid treating ordinary numbers as dates
      if (!Number.isNaN(Number(stringValue))) {
        return false;
      }

      const parsedDate = Date.parse(stringValue);

      return !Number.isNaN(parsedDate);
    };

    // Find numeric columns
    const numericColumns = cols.filter((column) => {
      const values = rows
        .map((row) => row[column])
        .filter(
          (value) =>
            value !== undefined &&
            value !== null &&
            String(value).trim() !== ""
        );

      if (values.length === 0) {
        return false;
      }

      const numericCount = values.filter(isNumeric).length;

      // Consider column numeric when most values are numeric
      return numericCount / values.length >= 0.5;
    });

    // Find date columns
    const dateColumns = cols.filter((column) => {
      const values = rows
        .map((row) => row[column])
        .filter(
          (value) =>
            value !== undefined &&
            value !== null &&
            String(value).trim() !== ""
        );

      if (values.length === 0) {
        return false;
      }

      const dateCount = values.filter(isDateValue).length;

      return dateCount / values.length >= 0.5;
    });

    // Find category/text columns
    const categoryColumns = cols.filter(
      (column) =>
        !numericColumns.includes(column) &&
        !dateColumns.includes(column)
    );

    // =========================
    // CASE 1:
    // DATE + NUMBER → LINE CHART
    // =========================
    if (dateColumns.length > 0 && numericColumns.length > 0) {
      const dateColumn = dateColumns[0];
      const numericColumn = numericColumns[0];

      const result = rows
        .map((row) => ({
          [dateColumn]: row[dateColumn],
          [numericColumn]: Number(row[numericColumn]),
        }))
        .filter(
          (row) =>
            row[dateColumn] !== undefined &&
            row[dateColumn] !== "" &&
            !Number.isNaN(row[numericColumn])
        );

      if (result.length > 0) {
        setChartType("line");
        setChartData(result);
        return;
      }
    }

    // =========================
    // CASE 2:
    // CATEGORY + NUMBER → BAR
    // =========================
    if (categoryColumns.length > 0 && numericColumns.length > 0) {
      const categoryColumn = categoryColumns[0];
      const numericColumn = numericColumns[0];

      const result = rows
        .map((row) => ({
          [categoryColumn]: row[categoryColumn],
          [numericColumn]: Number(row[numericColumn]),
        }))
        .filter(
          (row) =>
            row[categoryColumn] !== undefined &&
            row[categoryColumn] !== "" &&
            !Number.isNaN(row[numericColumn])
        );

      if (result.length > 0) {
        setChartType("bar");
        setChartData(result);
        return;
      }
    }

    // =========================
    // CASE 3:
    // TWO NUMERIC COLUMNS → SCATTER
    // =========================
    if (numericColumns.length >= 2) {
      const xColumn = numericColumns[0];
      const yColumn = numericColumns[1];

      const result = rows
        .map((row) => ({
          [xColumn]: Number(row[xColumn]),
          [yColumn]: Number(row[yColumn]),
        }))
        .filter(
          (row) =>
            !Number.isNaN(row[xColumn]) &&
            !Number.isNaN(row[yColumn])
        );

      if (result.length > 0) {
        setChartType("scatter");
        setChartData(result);
        return;
      }
    }

    // =========================
    // CASE 4:
    // ONLY ONE NUMERIC COLUMN → BAR
    // =========================
    if (numericColumns.length === 1) {
      const numericColumn = numericColumns[0];

      const result = rows
        .map((row, index) => ({
          index: index + 1,
          [numericColumn]: Number(row[numericColumn]),
        }))
        .filter((row) => !Number.isNaN(row[numericColumn]));

      if (result.length > 0) {
        setChartType("bar");
        setChartData(result);
        return;
      }
    }

    // =========================
    // NO SUITABLE CHART
    // =========================
    setChartData([]);
  };

  // =========================
  // LOCAL DATA INSIGHTS
  // =========================
  const detectLocalInsights = (rows, cols) => {
    const detected = [];

    cols.forEach((column) => {
      const missing = rows.filter(
        (row) =>
          row[column] === undefined ||
          row[column] === null ||
          String(row[column]).trim() === ""
      ).length;

      if (missing > 0) {
        detected.push({
          type: "Missing Values",
          message: `${column} contains ${missing} missing value${
            missing > 1 ? "s" : ""
          }.`,
        });
      }
    });

    const rowStrings = rows.map((row) => JSON.stringify(row));

    const uniqueRows = new Set(rowStrings);

    const duplicateCount = rows.length - uniqueRows.size;

    if (duplicateCount > 0) {
      detected.push({
        type: "Duplicate Rows",
        message: `${duplicateCount} duplicate row${
          duplicateCount > 1 ? "s were" : " was"
        } detected.`,
      });
    }

    if (detected.length === 0) {
      detected.push({
        type: "Initial Scan",
        message:
          "No missing values or duplicate rows detected in the initial scan.",
      });
    }

    setInsights(detected);
  };

  // =========================
  // ASK QUESTION
  // =========================
  const handleAskQuestion = async () => {
    if (!question.trim()) {
      setError("Please enter a question.");
      return;
    }

    if (data.length === 0) {
      setError("Please upload a dataset first.");
      return;
    }

    setError("");
    setLoading(true);

    /*
      BACKEND INTEGRATION WILL COME LATER.

      When the backend is ready:

      const response = await fetch(
        "http://localhost:8000/api/analyze",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question,
            data,
          }),
        }
      );

      const result = await response.json();

      setAnswer(result.answer);
      setCalculation(result.calculation);
      setChartData(result.chartData);
      setChartType(result.chart_type);
      setInsights(result.insights);
    */

    try {
      setAnswer(
        "Your dataset has been loaded successfully. Backend AI analysis will answer this question when the API is connected."
      );

      setCalculation(
        "The backend will provide the exact calculation steps for your question."
      );
    } catch (err) {
      console.error(err);
      setError("Unable to process the question.");
    } finally {
      setLoading(false);
    }
  };

  const askSuggestedQuestion = (text) => {
    setQuestion(text);

    document
      .getElementById("ask")
      ?.scrollIntoView({ behavior: "smooth" });
  };

  const scrollTo = (id) => {
    document
      .getElementById(id)
      ?.scrollIntoView({ behavior: "smooth" });
  };

  const issueCount =
    insights.length > 0 &&
    !(
      insights.length === 1 &&
      insights[0].type === "Initial Scan"
    )
      ? insights.length
      : 0;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">🕵️</div>

          <div>
            <strong>Data Detective</strong>
            <span>AI Data Lab</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>

        <nav className="nav">
          <button
            className="nav-item active"
            onClick={() => scrollTo("dashboard")}
          >
            <span>⌂</span> Dashboard
          </button>

          <button
            className="nav-item"
            onClick={() => scrollTo("dataset")}
          >
            <span>▣</span> My Dataset
          </button>

          <button
            className="nav-item"
            onClick={() => scrollTo("ask")}
          >
            <span>✦</span> Ask Your Data
          </button>

          <button
            className="nav-item"
            onClick={() => scrollTo("analytics")}
          >
            <span>▥</span> Analytics
          </button>

          <button
            className="nav-item"
            onClick={() => scrollTo("detective")}
          >
            <span>⌕</span> Data Detective
          </button>

          <button
            className="nav-item"
            onClick={() => scrollTo("insights")}
          >
            <span>◇</span> Insights
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="mini-tip">
            <span>✨</span>

            <div>
              <strong>Detective tip</strong>
              <p>
                Ask simple questions. Let your data do the talking.
              </p>
            </div>
          </div>

          <div className="sidebar-footer">⚙️ Workspace</div>
        </div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <div className="mobile-brand">
            <span>🕵️</span> Data Detective AI
          </div>

          <div className="topbar-status">
            <span className="status-dot"></span>
            Analysis workspace
          </div>

          <button
            className="topbar-button"
            onClick={() => scrollTo("dataset")}
          >
            + New dataset
          </button>
        </header>

        <main className="content">
          <section className="hero" id="dashboard">
            <div className="hero-copy">
              <div className="eyebrow">
                ✦ YOUR AI DATA WORKSPACE
              </div>

              <h1>
                Turn messy data into
                <span> clear discoveries.</span>
              </h1>

              <p>
                Upload a dataset, ask a question in plain English, and
                uncover the story hiding inside your numbers.
              </p>

              <div className="hero-actions">
                <button
                  className="primary-button"
                  onClick={() => scrollTo("dataset")}
                >
                  <span>📁</span> Explore my data
                </button>

                <button
                  className="ghost-button"
                  onClick={() => scrollTo("ask")}
                >
                  <span>✦</span> Ask a question
                </button>
              </div>
            </div>

            <div className="hero-orbit">
              <div className="orbit orbit-one"></div>
              <div className="orbit orbit-two"></div>

              <div className="detective-bubble">
                <span>🕵️</span>
                <strong>Let's investigate!</strong>
                <small>Your dataset is the clue.</small>
              </div>

              <div className="float-card float-card-one">
                📈 Trends
              </div>

              <div className="float-card float-card-two">
                💡 Insights
              </div>

              <div className="float-card float-card-three">
                🔎 Anomalies
              </div>
            </div>
          </section>

          <section className="stats-row">
            <div className="metric-card blue">
              <span className="metric-icon">📄</span>

              <div>
                <small>DATASET</small>
                <strong>
                  {file ? file.name : "Not uploaded"}
                </strong>
              </div>
            </div>

            <div className="metric-card purple">
              <span className="metric-icon">↕</span>

              <div>
                <small>ROWS</small>
                <strong>{data.length || "—"}</strong>
              </div>
            </div>

            <div className="metric-card pink">
              <span className="metric-icon">#</span>

              <div>
                <small>COLUMNS</small>
                <strong>{columns.length || "—"}</strong>
              </div>
            </div>

            <div className="metric-card yellow">
              <span className="metric-icon">🔎</span>

              <div>
                <small>ISSUES FOUND</small>
                <strong>{issueCount || "0"}</strong>
              </div>
            </div>
          </section>

          {error && (
            <div className="global-error">
              ⚠️ {error}
            </div>
          )}

          <section className="section-grid" id="dataset">
            <div className="section-heading">
              <div>
                <span className="section-kicker">
                  01 · DATA
                </span>

                <h2>Bring your dataset in</h2>

                <p>
                  Start your investigation with a CSV or Excel file.
                </p>
              </div>
            </div>

            <div className="upload-layout">
              <section className="panel upload-panel">
                <div className="panel-top">
                  <div>
                    <span className="icon-square blue-icon">
                      📂
                    </span>

                    <h3>Upload dataset</h3>

                    <p>
                      CSV, XLS or XLSX · Your data stays in this
                      browser for now.
                    </p>
                  </div>

                  <span className="step-pill">
                    STEP 1
                  </span>
                </div>

                <label className="upload-box">
                  <input
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={handleFileChange}
                  />

                  <div className="upload-cloud">☁️</div>

                  <strong>
                    {file
                      ? file.name
                      : "Drop your dataset here"}
                  </strong>

                  <span>
                    {file
                      ? `${(file.size / 1024).toFixed(1)} KB`
                      : "or click to browse files"}
                  </span>

                  <div className="file-types">
                    <b>CSV</b>
                    <b>XLS</b>
                    <b>XLSX</b>
                  </div>
                </label>
              </section>

              <section className="panel schema-panel">
                <div className="panel-top">
                  <div>
                    <span className="icon-square purple-icon">
                      🧩
                    </span>

                    <h3>Detected schema</h3>

                    <p>
                      Columns found in your uploaded dataset.
                    </p>
                  </div>

                  <span className="step-pill purple-pill">
                    AUTO
                  </span>
                </div>

                {columns.length > 0 ? (
                  <div className="column-list">
                    {columns.map((column, index) => (
                      <span
                        className="column-tag"
                        key={index}
                      >
                        <i>•</i> {column}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="soft-empty">
                    <span>🧩</span>

                    <p>
                      Upload a file and I'll map its columns
                      here.
                    </p>
                  </div>
                )}
              </section>
            </div>

            <section className="panel preview-panel">
              <div className="panel-top preview-heading">
                <div>
                  <span className="icon-square cyan-icon">
                    👀
                  </span>

                  <h3>Dataset preview</h3>

                  <p>
                    A quick peek at the first 10 records.
                  </p>
                </div>

                {data.length > 0 && (
                  <span className="row-pill">
                    {data.length} total rows
                  </span>
                )}
              </div>

              {data.length > 0 ? (
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        {columns.map((column, index) => (
                          <th key={index}>{column}</th>
                        ))}
                      </tr>
                    </thead>

                    <tbody>
                      {data
                        .slice(0, 10)
                        .map((row, rowIndex) => (
                          <tr key={rowIndex}>
                            {columns.map(
                              (column, columnIndex) => (
                                <td key={columnIndex}>
                                  {row[column] ===
                                    undefined ||
                                  row[column] === null ||
                                  row[column] === ""
                                    ? "—"
                                    : String(row[column])}
                                </td>
                              )
                            )}
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="soft-empty large-empty">
                  <span>📊</span>

                  <p>
                    Upload a dataset to see your rows here.
                  </p>
                </div>
              )}

              {data.length > 10 && (
                <small className="preview-count">
                  Showing first 10 of {data.length} rows
                </small>
              )}
            </section>
          </section>

          <section className="ask-section" id="ask">
            <div className="ask-glow"></div>

            <div className="section-kicker">
              02 · INVESTIGATE
            </div>

            <h2>Ask your data anything.</h2>

            <p>
              Use normal English. No formulas, SQL, or
              complicated filters required.
            </p>

            <div className="question-box">
              <span className="question-sparkle">
                ✦
              </span>

              <input
                type="text"
                value={question}
                onChange={(e) =>
                  setQuestion(e.target.value)
                }
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleAskQuestion();
                  }
                }}
                placeholder="Try: What was the total sales in 2025?"
              />

              <button
                onClick={handleAskQuestion}
                disabled={loading}
              >
                {loading
                  ? "Thinking..."
                  : "Ask AI →"}
              </button>
            </div>

            <div className="suggestion-row">
              <span>Try asking</span>

              <button
                onClick={() =>
                  askSuggestedQuestion(
                    "What are the top 5 categories?"
                  )
                }
              >
                Top 5 categories
              </button>

              <button
                onClick={() =>
                  askSuggestedQuestion(
                    "Which month had the highest sales?"
                  )
                }
              >
                Highest sales month
              </button>

              <button
                onClick={() =>
                  askSuggestedQuestion(
                    "Are there any unusual values?"
                  )
                }
              >
                Unusual values
              </button>
            </div>
          </section>

          <section
            className="results-grid"
            id="analytics"
          >
            <section className="panel answer-panel">
              <div className="result-heading">
                <span className="result-icon answer-icon">
                  ✦
                </span>

                <div>
                  <span className="section-kicker">
                    03 · ANSWER
                  </span>

                  <h3>AI Answer</h3>
                </div>
              </div>

              {answer ? (
                <div className="answer-box">
                  {answer}
                </div>
              ) : (
                <div className="soft-empty result-empty">
                  <span>💬</span>

                  <p>
                    Your AI-generated answer will appear
                    here.
                  </p>
                </div>
              )}
            </section>

            <section className="panel calculation-panel">
              <div className="result-heading">
                <span className="result-icon calc-icon">
                  ∑
                </span>

                <div>
                  <span className="section-kicker">
                    04 · EXPLAIN
                  </span>

                  <h3>
                    How was this calculated?
                  </h3>
                </div>
              </div>

              <div className="explanation">
                {calculation ||
                  "The calculation steps returned by the AI will appear here."}
              </div>
            </section>

            <section className="panel chart-panel">
              <div className="result-heading">
                <span className="result-icon chart-icon">
                  ▥
                </span>

                <div>
                  <span className="section-kicker">
                    05 · VISUALIZE
                  </span>

                  <h3>Data visualization</h3>
                </div>
              </div>

              {chartData.length > 0 ? (
                <Chart
                  type={chartType}
                  data={chartData}
                />
              ) : (
                <div className="soft-empty chart-empty">
                  <span>📈</span>

                  <p>
                    Upload a dataset with numeric data
                    to generate a chart.
                  </p>
                </div>
              )}
            </section>
          </section>

          <section
            className="detective-section"
            id="detective"
          >
            <div className="detective-header">
              <div>
                <div className="section-kicker">
                  06 · INVESTIGATION
                </div>

                <h2>🕵️ Data Detective</h2>

                <p>
                  Little clues that deserve a closer
                  look.
                </p>
              </div>

              <div className="detective-badge">
                SCAN COMPLETE
              </div>
            </div>

            {insights.length > 0 ? (
              <div className="insight-grid">
                {insights.map((insight, index) => (
                  <div
                    className="insight-card"
                    key={index}
                  >
                    <div className="insight-icon">
                      {insight.type ===
                      "Missing Values"
                        ? "⚠️"
                        : insight.type ===
                          "Duplicate Rows"
                        ? "🔁"
                        : "✨"}
                    </div>

                    <div>
                      <span>{insight.type}</span>

                      <p>{insight.message}</p>
                    </div>

                    <b>→</b>
                  </div>
                ))}
              </div>
            ) : (
              <div className="detective-empty">
                <span>🔎</span>

                <div>
                  <strong>No clues yet.</strong>

                  <p>
                    Upload a dataset to start the
                    detective scan.
                  </p>
                </div>
              </div>
            )}
          </section>

          <section
            className="insights-section"
            id="insights"
          >
            <div>
              <div className="section-kicker">
                07 · NEXT CLUES
              </div>

              <h2>
                What should we investigate next?
              </h2>

              <p>
                Keep exploring your dataset with quick
                questions.
              </p>
            </div>

            <div className="question-cards">
              <button
                onClick={() =>
                  askSuggestedQuestion(
                    "What are the top 5 categories?"
                  )
                }
              >
                <span>🏆</span>

                <strong>
                  Find the top performers
                </strong>

                <small>
                  Discover your top 5 categories
                </small>
              </button>

              <button
                onClick={() =>
                  askSuggestedQuestion(
                    "Which month had the highest sales?"
                  )
                }
              >
                <span>📅</span>

                <strong>
                  Explore time trends
                </strong>

                <small>
                  Find the strongest month or period
                </small>
              </button>

              <button
                onClick={() =>
                  askSuggestedQuestion(
                    "Are there any unusual values?"
                  )
                }
              >
                <span>🧠</span>

                <strong>
                  Look for surprises
                </strong>

                <small>
                  Ask about unusual values
                </small>
              </button>
            </div>
          </section>

          <footer className="footer">
            <div>
              <strong>
                🕵️ Data Detective AI
              </strong>

              <span>
                Make your data tell its story.
              </span>
            </div>

            <span>
              Built for Hack the Horizon · Frontend
              workspace
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}

export default App;
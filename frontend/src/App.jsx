import { useState } from "react";
import Papa from "papaparse";
import * as XLSX from "xlsx";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
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

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // --------------------------------
  // FILE UPLOAD
  // --------------------------------

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
  
    if (!selectedFile) return;
  
    setFile(selectedFile);
    setError("");
    setAnswer("");
    setCalculation("");
    setInsights([]);
    setChartData([]);
  
    const fileName = selectedFile.name.toLowerCase();
  
    // CSV
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
            detectLocalInsights(rows, detectedColumns);
          }
        },
  
        error: (error) => {
          console.error(error);
          setError("Unable to read the CSV file.");
        },
      });
  
      return;
    }
  
    // Excel
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
            detectLocalInsights(rows, detectedColumns);
          } else {
            setError("The Excel file does not contain any data.");
          }
        } catch (error) {
          console.error(error);
          setError("Unable to read the Excel file.");
        }
      };
  
      reader.readAsArrayBuffer(selectedFile);
  
      return;
    }
  
    setError("Please upload a CSV, XLS, or XLSX file.");
  };

  // --------------------------------
  // BASIC DATA DETECTION
  // --------------------------------

  const detectLocalInsights = (rows, cols) => {
    const detected = [];

    // Missing values
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

    // Duplicate rows
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
        message: "No missing values or duplicate rows detected in the initial scan.",
      });
    }

    setInsights(detected);
  };

  // --------------------------------
  // ASK AI
  // --------------------------------

  const handleAskQuestion = async () => {
    if (!question.trim()) {
      setError("Please enter a question.");
      return;
    }

    if (data.length === 0) {
      setError("Please upload a CSV dataset first.");
      return;
    }

    setError("");
    setLoading(true);

    /*
      BACKEND INTEGRATION POINT

      Your backend teammate can provide the API endpoint here.

      Example:

      const response = await fetch("http://localhost:8000/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
          data,
        }),
      });

      const result = await response.json();

      setAnswer(result.answer);
      setCalculation(result.calculation);
      setChartData(result.chartData);
      setInsights(result.insights);
    */

    try {
      // Temporary connection placeholder.
      // No fake AI answer is generated.
      setAnswer(
        "Backend analysis is not connected yet. The frontend is ready to send your question and dataset to the AI API."
      );

      setCalculation(
        "The calculation explanation will be displayed here when the backend returns the analysis steps."
      );
    } catch (err) {
      console.error(err);
      setError("Unable to connect to the analysis service.");
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------
  // SUGGESTED QUESTION
  // --------------------------------

  const askSuggestedQuestion = (text) => {
    setQuestion(text);
  };

  return (
    <div className="app">

      {/* HEADER */}

      <header className="header">
        <div>
          <h1>🔍 Data Detective AI</h1>
          <p>
            Talk to your data. Discover hidden insights.
          </p>
        </div>
      </header>

      <main className="dashboard">

        {/* UPLOAD */}

        <section className="card upload-card">

          <h2>📂 Upload Your Dataset</h2>

          <p>
            Upload a CSV or Excel dataset for AI-powered analysis.
          </p>

          <label className="upload-box">

            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileChange}
            />

            <span className="upload-icon">📁</span>

            <strong>
              {file
                ? file.name
                : "Choose a CSV or Excel file"}
            </strong>

            <small>
              {file
                ? `${(file.size / 1024).toFixed(1)} KB`
                : "Click here to browse your files"}
            </small>

          </label>

          {error && (
            <p className="error-message">
              {error}
            </p>
          )}

        </section>

        {/* DATASET OVERVIEW */}

        <section className="card">

          <h2>📊 Dataset Overview</h2>

          <div className="stats">

            <div className="stat">
              <span>Rows</span>
              <strong>
                {data.length || "--"}
              </strong>
            </div>

            <div className="stat">
              <span>Columns</span>
              <strong>
                {columns.length || "--"}
              </strong>
            </div>

            <div className="stat">
              <span>File</span>
              <strong>
                {file ? file.name : "--"}
              </strong>
            </div>

          </div>

          <div className="schema">

            <h3>Detected Schema</h3>

            {columns.length > 0 ? (

              <div className="column-list">

                {columns.map((column, index) => (

                  <span
                    className="column-tag"
                    key={index}
                  >
                    {column}
                  </span>

                ))}

              </div>

            ) : (

              <p>
                Upload a CSV dataset to detect its schema.
              </p>

            )}

          </div>

        </section>

        {/* ASK YOUR DATA */}

        <section className="card question-card">

          <h2>💬 Ask Your Data</h2>

          <p>
            Ask questions about your dataset using normal English.
          </p>

          <div className="question-input">

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
              placeholder="Example: What was the total sales in 2025?"
            />

            <button
              onClick={handleAskQuestion}
              disabled={loading}
            >
              {loading ? "Analyzing..." : "Ask AI"}
            </button>

          </div>

        </section>

        {/* AI ANSWER */}

        <section className="card">

          <h2>🤖 AI Answer</h2>

          {answer ? (

            <div className="answer-box">
              {answer}
            </div>

          ) : (

            <div className="empty-state">

              <span>💡</span>

              <p>
                Your AI-generated answer will appear here.
              </p>

            </div>

          )}

        </section>

        {/* CHART */}

        <section className="card">

          <h2>📈 Data Visualization</h2>

          {chartData.length > 0 ? (

            <div className="chart-container">

              <ResponsiveContainer
                width="100%"
                height={350}
              >

                <BarChart data={chartData}>

                  <CartesianGrid strokeDasharray="3 3" />

                  <XAxis dataKey="name" />

                  <YAxis />

                  <Tooltip />

                  <Bar dataKey="value" />

                </BarChart>

              </ResponsiveContainer>

            </div>

          ) : (

            <div className="empty-state">

              <span>📊</span>

              <p>
                Charts generated from AI analysis will appear here.
              </p>

            </div>

          )}

        </section>

        {/* CALCULATION */}

        <section className="card">

          <h2>🧮 How Was This Calculated?</h2>

          {calculation ? (

            <div className="explanation">
              {calculation}
            </div>

          ) : (

            <div className="explanation">

              The calculation steps returned by the AI
              will appear here.

            </div>

          )}

        </section>

        {/* DATA DETECTIVE */}

        <section className="card detective-card">

          <h2>🔍 Data Detective</h2>

          <p>
            Automatically detected patterns and unusual
            characteristics in your dataset.
          </p>

          {insights.length > 0 ? (

            <div className="insight-list">

              {insights.map((insight, index) => (

                <div
                  className="insight"
                  key={index}
                >

                  <span>🔎</span>

                  <div>

                    <strong>
                      {insight.type}
                    </strong>

                    <p>
                      {insight.message}
                    </p>

                  </div>

                </div>

              ))}

            </div>

          ) : (

            <div className="empty-state">

              <span>🔎</span>

              <p>
                Upload a dataset to start the detective scan.
              </p>

            </div>

          )}

        </section>

        {/* SUGGESTED QUESTIONS */}

        <section className="card">

          <h2>💡 Suggested Questions</h2>

          <div className="suggestions">

            <button
              onClick={() =>
                askSuggestedQuestion(
                  "What are the top 5 categories?"
                )
              }
            >
              What are the top 5 categories?
            </button>

            <button
              onClick={() =>
                askSuggestedQuestion(
                  "Which month had the highest sales?"
                )
              }
            >
              Which month had the highest sales?
            </button>

            <button
              onClick={() =>
                askSuggestedQuestion(
                  "Are there any unusual values?"
                )
              }
            >
              Are there any unusual values?
            </button>

          </div>

        </section>

      </main>

    </div>
  );
}

export default App;
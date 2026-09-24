import { useState } from "react";
import Papa from "papaparse";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [data, setData] = useState([]);
  const [columns, setColumns] = useState([]);

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];

    if (!selectedFile) return;

    setFile(selectedFile);

    // Check whether the file is CSV
    if (selectedFile.name.toLowerCase().endsWith(".csv")) {
      Papa.parse(selectedFile, {
        header: true,
        skipEmptyLines: true,

        complete: (result) => {
          const rows = result.data;

          setData(rows);

          if (rows.length > 0) {
            setColumns(Object.keys(rows[0]));
          }
        },

        error: (error) => {
          console.error("CSV parsing error:", error);
        },
      });
    }
  };

  return (
    <div className="app">

      <header className="header">
        <div>
          <h1>🔍 Data Detective AI</h1>
          <p>Talk to your data. Discover hidden insights.</p>
        </div>
      </header>

      <main className="dashboard">

        {/* Upload */}
        <section className="card upload-card">
          <h2>📂 Upload Your Dataset</h2>

          <p>
            Upload a CSV or Excel file and let AI analyze your data.
          </p>

          <label className="upload-box">
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileChange}
            />

            <span className="upload-icon">📁</span>

            <strong>
              {file ? file.name : "Choose a CSV or Excel file"}
            </strong>

            <small>
              {file
                ? `${(file.size / 1024).toFixed(1)} KB`
                : "Click here to browse your files"}
            </small>
          </label>
        </section>

        {/* Dataset Overview */}
        <section className="card">
          <h2>📊 Dataset Overview</h2>

          <div className="stats">

            <div className="stat">
              <span>Rows</span>
              <strong>
                {data.length > 0 ? data.length : "--"}
              </strong>
            </div>

            <div className="stat">
              <span>Columns</span>
              <strong>
                {columns.length > 0 ? columns.length : "--"}
              </strong>
            </div>

            <div className="stat">
              <span>File</span>
              <strong>
                {file ? file.name : "--"}
              </strong>
            </div>

          </div>

          {/* Schema */}
          <div className="schema">
            <h3>Detected Schema</h3>

            {columns.length > 0 ? (
              <div className="column-list">
                {columns.map((column, index) => (
                  <span className="column-tag" key={index}>
                    {column}
                  </span>
                ))}
              </div>
            ) : (
              <p>Upload a CSV dataset to see its columns.</p>
            )}
          </div>
        </section>

        {/* Ask Question */}
        <section className="card question-card">
          <h2>💬 Ask Your Data</h2>

          <p>
            Ask a question about your dataset in normal English.
          </p>

          <div className="question-input">
            <input
              type="text"
              placeholder="Example: What was the total sales in 2025?"
            />

            <button>
              Ask AI
            </button>
          </div>
        </section>

        {/* Answer */}
        <section className="card">
          <h2>🤖 AI Answer</h2>

          <div className="empty-state">
            <span>💡</span>

            <p>
              Your answer will appear here after you ask a question.
            </p>
          </div>
        </section>

        {/* Chart */}
        <section className="card">
          <h2>📈 Data Visualization</h2>

          <div className="empty-state">
            <span>📊</span>

            <p>
              A suitable chart will be generated automatically.
            </p>
          </div>
        </section>

        {/* Calculation */}
        <section className="card">
          <h2>🧮 How Was This Calculated?</h2>

          <div className="explanation">
            <p>
              The AI will explain the calculation steps used to produce
              the answer.
            </p>
          </div>
        </section>

        {/* Data Detective */}
        <section className="card detective-card">
          <h2>🔍 Data Detective</h2>

          <p>
            Automatically discovered patterns and unusual values.
          </p>

          <div className="insight">
            <span>🔎</span>

            <div>
              <strong>No insights yet</strong>

              <p>
                Upload your dataset to let Data Detective search for
                anomalies and hidden patterns.
              </p>
            </div>
          </div>
        </section>

        {/* Suggested Questions */}
        <section className="card">
          <h2>💡 Suggested Questions</h2>

          <div className="suggestions">
            <button>What are the top 5 categories?</button>

            <button>Which month had the highest sales?</button>

            <button>Are there any unusual values?</button>
          </div>
        </section>

      </main>
    </div>
  );
}

export default App;
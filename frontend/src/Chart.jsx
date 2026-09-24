import {
    BarChart,
    Bar,
    LineChart,
    Line,
    PieChart,
    Pie,
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Cell,
  } from "recharts";
  
  function Chart({ type, data }) {
    if (!data || data.length === 0) {
      return <p>No chart data available.</p>;
    }
  
    // BAR CHART
    if (type === "bar") {
      const keys = Object.keys(data[0]);
  
      const xKey = keys[0];
      const yKey = keys[1];
  
      return (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey={yKey} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      );
    }
  
    // LINE CHART
    if (type === "line") {
      const keys = Object.keys(data[0]);
  
      const xKey = keys[0];
      const yKey = keys[1];
  
      return (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey={yKey}
                strokeWidth={3}
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      );
    }
  
    // PIE CHART
    if (type === "pie") {
      const keys = Object.keys(data[0]);
  
      const nameKey = keys[0];
      const valueKey = keys[1];
  
      return (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={350}>
            <PieChart>
              <Pie
                data={data}
                dataKey={valueKey}
                nameKey={nameKey}
                cx="50%"
                cy="50%"
                outerRadius={120}
                label
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} />
                ))}
              </Pie>
  
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      );
    }
  
    // SCATTER CHART
    if (type === "scatter") {
      const keys = Object.keys(data[0]);
  
      const xKey = keys[0];
      const yKey = keys[1];
  
      const scatterData = data.map((item) => ({
        x: Number(item[xKey]),
        y: Number(item[yKey]),
      }));
  
      return (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={350}>
            <ScatterChart>
              <CartesianGrid />
  
              <XAxis
                type="number"
                dataKey="x"
                name={xKey}
              />
  
              <YAxis
                type="number"
                dataKey="y"
                name={yKey}
              />
  
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
  
              <Legend />
  
              <Scatter data={scatterData} name={`${xKey} vs ${yKey}`} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      );
    }
  
    return <p>Unsupported chart type: {type}</p>;
  }
  
  export default Chart;
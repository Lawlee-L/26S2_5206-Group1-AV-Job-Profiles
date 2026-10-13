import React, { useEffect, useRef } from "react";
import { Chart, registerables } from "chart.js";

Chart.register(...registerables);
export const CHART_COLORS = ["#183a7a", "#bc861e", "#00857d", "#8b58a3", "#c56145"];

export function chartConfig({ type, labels, series, horizontal = false, percent = false }) {
  return {
    type,
    data: { labels, datasets: series.map((item, index) => ({
      label: item.name, data: item.values, borderColor: CHART_COLORS[index % CHART_COLORS.length],
      backgroundColor: type === "bar" ? "#284f87" : `${CHART_COLORS[index % CHART_COLORS.length]}18`,
      borderWidth: type === "line" ? 2 : 0, borderRadius: type === "bar" ? 4 : 0,
      pointRadius: 4, pointHoverRadius: 6, tension: 0, spanGaps: false,
    })) },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      indexAxis: horizontal ? "y" : "x",
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: series.length > 1, position: "bottom", labels: { usePointStyle: true, boxWidth: 8, padding: 18, color: "#53627b", font: { size: 12 } } },
        tooltip: { callbacks: { label: (context) => `${context.dataset.label}: ${context.parsed[horizontal ? "x" : "y"]}${percent ? "%" : ""}` } },
      },
      scales: {
        x: { beginAtZero: horizontal, offset: type === "line" && labels.length === 1, grid: { display: horizontal, color: "#edf0f5" }, ticks: { color: "#53627b", font: { size: 12 } } },
        y: { beginAtZero: !horizontal, max: percent ? 100 : undefined, grid: { display: !horizontal, color: "#edf0f5" },
          ticks: { color: "#53627b", precision: 0, font: { size: 12 }, ...(percent ? { callback: (value) => `${value}%` } : {}),
            ...(horizontal ? { callback: function(value) { const label = this.getLabelForValue(value); return label.length > 30 ? `${label.slice(0, 28)}…` : label; } } : {}) } },
      },
    },
  };
}

export default function InsightChart({ title, description, type = "bar", labels, series, horizontal = false, percent = false }) {
  const canvas = useRef(null);
  useEffect(() => {
    const chart = new Chart(canvas.current, chartConfig({ type, labels, series, horizontal, percent }));
    return () => chart.destroy();
  }, [type, labels, series, horizontal, percent]);
  return <section className="card border-0 insight-chart-card">
    <h2>{title}</h2><p className="chart-description">{description}</p>
    <div className="insight-chart-container"><canvas ref={canvas} role="img" aria-label={`${title}. Exact values are available in the data table below.`} /></div>
    <details className="chart-data"><summary>View chart data</summary>
      <div className="table-responsive"><table className="table table-sm"><caption className="visually-hidden">{title}</caption>
        <thead><tr><th scope="col">{type === "line" ? "Snapshot date" : "Category"}</th>{series.map((item) => <th scope="col" key={item.name}>{item.name}</th>)}</tr></thead>
        <tbody>{labels.map((label, index) => <tr key={`${label}-${index}`}><th scope="row">{label}</th>
          {series.map((item) => <td key={item.name}>{item.values[index] == null ? "Not available" : `${item.values[index].toLocaleString()}${percent ? "%" : ""}`}</td>)}
        </tr>)}</tbody></table></div>
    </details>
  </section>;
}

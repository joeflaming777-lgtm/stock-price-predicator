/* ─── Chart IDs ─────────────────────────────────────────── */
const CHARTS = [
    { container: "historicalChart",      payload: "historical-chart-json"      },
    { container: "actualPredictedChart", payload: "actual-predicted-chart-json" },
    { container: "movingAverageChart",   payload: "moving-average-chart-json"   },
    { container: "futureChart",          payload: "future-chart-json"           },
];

/* ─── Theme helpers ──────────────────────────────────────── */
function isDark() {
    return document.documentElement.getAttribute("data-theme") === "dark";
}

function getPlotlyLayout(dark) {
    return {
        paper_bgcolor: dark ? "#161b22" : "#ffffff",
        plot_bgcolor:  dark ? "#161b22" : "#ffffff",
        font:          { color: dark ? "#8b949e" : "#374151" },
        xaxis: { gridcolor: dark ? "#30363d" : "#e5e7eb", linecolor: dark ? "#30363d" : "#d1d5db" },
        yaxis: { gridcolor: dark ? "#30363d" : "#e5e7eb", linecolor: dark ? "#30363d" : "#d1d5db" },
    };
}

/* ─── Chart rendering ────────────────────────────────────── */
function renderChart(containerId, payloadId) {
    const container = document.getElementById(containerId);
    const payload   = document.getElementById(payloadId);
    if (!container || !payload || !window.Plotly) return;

    try {
        const figure = JSON.parse(payload.textContent);
        const layout = Object.assign({}, figure.layout, getPlotlyLayout(isDark()));
        Plotly.newPlot(container, figure.data, layout, {
            responsive: true,
            displaylogo: false,
            modeBarButtonsToRemove: ["lasso2d", "select2d"],
        });
    } catch {
        container.innerHTML = "<div class='alert alert-warning mb-0'>Chart data could not be rendered.</div>";
    }
}

function renderAllCharts() {
    CHARTS.forEach(({ container, payload }) => renderChart(container, payload));
}

/* Re-theme already-rendered Plotly charts without a full redraw */
function reThemeCharts() {
    const layoutPatch = getPlotlyLayout(isDark());
    CHARTS.forEach(({ container }) => {
        const el = document.getElementById(container);
        if (el && el.data) {
            Plotly.relayout(el, layoutPatch).catch(() => {});
        }
    });
}

/* ─── Dark / light toggle ────────────────────────────────── */
function applyTheme(dark, save) {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    if (save) localStorage.setItem("theme", dark ? "dark" : "light");
    reThemeCharts();
}

document.addEventListener("DOMContentLoaded", function () {
    renderAllCharts();

    const btn = document.getElementById("theme-toggle");
    if (btn) {
        btn.addEventListener("click", function () {
            applyTheme(!isDark(), true);
        });
    }
});

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

    // Attach listeners for stock refresh buttons
    const btnPrice = document.getElementById("refresh-stock-btn");
    const btnNews = document.getElementById("refresh-news-btn");
    if (btnPrice) {
        btnPrice.addEventListener("click", refreshStockPriceAndNews);
    }
    if (btnNews) {
        btnNews.addEventListener("click", refreshStockPriceAndNews);
    }
});

/* ─── Price & News Live Refresh ──────────────────────────── */

function formatCurrency(val, currencyCode) {
    const symbolMap = {
        'USD': '$',
        'INR': '₹',
        'EUR': '€',
        'GBP': '£'
    };
    const symbol = symbolMap[currencyCode] || currencyCode;
    const formattedVal = Number(val).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    return symbol.length > 1 ? `${symbol} ${formattedVal}` : `${symbol}${formattedVal}`;
}

function formatSignedCurrency(val, currencyCode) {
    const amount = Number(val);
    const sign = amount >= 0 ? '+' : '-';
    const symbolMap = {
        'USD': '$',
        'INR': '₹',
        'EUR': '€',
        'GBP': '£'
    };
    const symbol = symbolMap[currencyCode] || currencyCode;
    const absVal = Math.abs(amount).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    return symbol.length > 1 ? `${sign}${symbol} ${absVal}` : `${sign}${symbol}${absVal}`;
}

function formatSignedPercent(val) {
    const amount = Number(val);
    const sign = amount >= 0 ? '+' : '';
    return `${sign}${amount.toFixed(2)}%`;
}

async function refreshStockPriceAndNews() {
    const symbol = window.TRADE_CONTEXT ? window.TRADE_CONTEXT.symbol : null;
    const currency = window.TRADE_CONTEXT ? window.TRADE_CONTEXT.currency : 'USD';
    
    if (!symbol) return;

    // Grab both buttons to show loading states on both
    const btnPrice = document.getElementById("refresh-stock-btn");
    const btnNews = document.getElementById("refresh-news-btn");
    
    [btnPrice, btnNews].forEach(btn => {
        if (btn) btn.classList.add("loading");
    });

    try {
        const response = await fetch(`/api/stock-update?symbol=${encodeURIComponent(symbol)}`);
        const data = await response.json();

        if (data.error) {
            console.error("API error during refresh:", data.error);
            return;
        }

        // 1. Update Price Card
        const priceValEl = document.getElementById("price-val");
        const priceChangeValEl = document.getElementById("price-change-val");
        const priceCardEl = document.getElementById("price-card-el");

        if (priceValEl && priceChangeValEl) {
            priceValEl.textContent = formatCurrency(data.current_price, data.currency);
            
            const isPositive = data.price_change >= 0;
            priceChangeValEl.textContent = `${formatSignedCurrency(data.price_change, data.currency)} (${formatSignedPercent(data.price_change_percent)})`;
            
            // Set text class matching change
            priceChangeValEl.className = isPositive ? 'text-positive' : 'text-negative';

            // Trigger card glow animation
            if (priceCardEl) {
                // Remove existing animation classes
                priceCardEl.classList.remove("glow-up", "glow-down");
                // Force layout reflow to restart animation
                void priceCardEl.offsetWidth;
                priceCardEl.classList.add(isPositive ? "glow-up" : "glow-down");
            }
        }

        // 2. Update News Card Grid
        const newsContainer = document.getElementById("news-grid-container");
        const updatedTimeEl = document.getElementById("news-updated-time");

        if (updatedTimeEl) {
            updatedTimeEl.textContent = data.fetched_at;
        }

        if (newsContainer) {
            if (data.news && data.news.length > 0) {
                newsContainer.innerHTML = data.news.map((article, idx) => {
                    const thumbHtml = article.thumbnail 
                        ? `<div class="news-thumb"><img src="${article.thumbnail}" alt="" loading="lazy"></div>`
                        : '';
                    const summaryHtml = article.summary 
                        ? `<p class="news-summary">${article.summary}</p>`
                        : '';
                    
                    return `
                        <a class="news-card news-fade-in" href="${article.url}" target="_blank" rel="noopener noreferrer" style="animation-delay: ${idx * 0.08}s;">
                            ${thumbHtml}
                            <div class="news-body">
                                <div class="news-meta">
                                    <span class="news-publisher">${article.publisher}</span>
                                    <span class="news-time">${article.published}</span>
                                </div>
                                <h3 class="news-title">${article.title}</h3>
                                ${summaryHtml}
                            </div>
                        </a>
                    `;
                }).join('');
            } else {
                newsContainer.innerHTML = `<div class="text-center py-4 w-100 text-muted">No news articles found for ${symbol}.</div>`;
            }
        }

        // 3. Update window.TRADE_CONTEXT to trigger chatbot bar update via its setter
        if (window.TRADE_CONTEXT) {
            window.TRADE_CONTEXT = Object.assign({}, window.TRADE_CONTEXT, {
                price: data.current_price,
                change: data.price_change_percent,
                news: data.news && data.news.length > 0 ? data.news.slice(0, 3).map(a => a.title) : window.TRADE_CONTEXT.news
            });
        }

    } catch (err) {
        console.error("Failed to fetch stock updates:", err);
    } finally {
        // Stop spinning
        [btnPrice, btnNews].forEach(btn => {
            if (btn) btn.classList.remove("loading");
        });
    }
}

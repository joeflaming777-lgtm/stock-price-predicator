/* ─── Chart IDs ─────────────────────────────────────────── */
const CHARTS = [
    { container: "historicalChart",      payload: "historical-chart-json"      },
    { container: "actualPredictedChart", payload: "actual-predicted-chart-json" },
    { container: "movingAverageChart",   payload: "moving-average-chart-json"   },
    { container: "futureChart",          payload: "future-chart-json"           },
];

/* ─── Constants ──────────────────────────────────────────── */
const PRICE_REFRESH_INTERVAL_MS  = 30_000;   // 30 seconds
const INDICES_REFRESH_INTERVAL_MS = 60_000;  // 60 seconds

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

/* ─── Countdown Timer ────────────────────────────────────── */
let _priceCountdownTimer   = null;
let _priceCountdownSeconds = PRICE_REFRESH_INTERVAL_MS / 1000;

function startPriceCountdown() {
    _priceCountdownSeconds = PRICE_REFRESH_INTERVAL_MS / 1000;
    clearInterval(_priceCountdownTimer);
    _priceCountdownTimer = setInterval(() => {
        _priceCountdownSeconds = Math.max(0, _priceCountdownSeconds - 1);
        const el = document.getElementById("refresh-countdown");
        if (el) {
            el.textContent = `Auto-refresh in ${_priceCountdownSeconds}s`;
        }
    }, 1000);
}

/* ─── DOMContentLoaded ───────────────────────────────────── */
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
    const btnNews  = document.getElementById("refresh-news-btn");
    if (btnPrice) btnPrice.addEventListener("click", () => triggerPriceAndNewsRefresh(true));
    if (btnNews)  btnNews.addEventListener("click",  () => triggerPriceAndNewsRefresh(true));

    // Set up automatic live update polling every 30 seconds
    if (window.TRADE_CONTEXT && window.TRADE_CONTEXT.symbol) {
        startPriceCountdown();
        setInterval(() => {
            triggerPriceAndNewsRefresh(false);
            startPriceCountdown();
        }, PRICE_REFRESH_INTERVAL_MS);
    }

    // Load market indices immediately
    loadMarketIndices();

    // Auto-refresh indices every 60 seconds
    setInterval(loadMarketIndices, INDICES_REFRESH_INTERVAL_MS);
});

/* ─── Market Indices ─────────────────────────────────────── */
async function loadMarketIndices() {
    const inner = document.getElementById("indices-inner");
    if (!inner) return;

    // Show spinner while loading
    const wasEmpty = inner.querySelector(".idx-loading") !== null;
    if (wasEmpty) {
        inner.innerHTML = `<span class="idx-loading"><span class="idx-spinner"></span> Loading market data…</span>`;
    }

    try {
        const res  = await fetch("/api/market-indices");
        const data = await res.json();
        if (!data.indices || !data.indices.length) return;

        inner.innerHTML = data.indices.map(idx => {
            const pct = idx.change_pct;
            const cls = pct == null ? "" : pct >= 0 ? "idx-up" : "idx-down";
            const arrow = pct == null ? "" : pct >= 0 ? "▲" : "▼";
            const priceStr = idx.price != null
                ? Number(idx.price).toLocaleString("en-IN", { maximumFractionDigits: 2 })
                : "—";
            const pctStr = pct != null ? `${arrow} ${Math.abs(pct).toFixed(2)}%` : "";
            return `<span class="idx-item"><span class="idx-name">${idx.name}</span><span class="idx-val">${priceStr}</span><span class="idx-chg ${cls}">${pctStr}</span></span>`;
        }).join(`<span class="idx-divider">|</span>`);

        // Duplicate for seamless scroll marquee
        inner.innerHTML += inner.innerHTML;

    } catch (e) {
        if (inner) inner.innerHTML = `<span class="idx-error">Market data unavailable</span>`;
    }
}

/* ─── Currency Formatters ────────────────────────────────── */
function formatCurrency(val, currencyCode) {
    const symbolMap = { "USD": "$", "INR": "₹", "EUR": "€", "GBP": "£" };
    const symbol = symbolMap[currencyCode] || currencyCode;
    const formattedVal = Number(val).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    return symbol.length > 1 ? `${symbol} ${formattedVal}` : `${symbol}${formattedVal}`;
}

function formatSignedCurrency(val, currencyCode) {
    const amount = Number(val);
    const sign = amount >= 0 ? "+" : "-";
    const symbolMap = { "USD": "$", "INR": "₹", "EUR": "€", "GBP": "£" };
    const symbol = symbolMap[currencyCode] || currencyCode;
    const absVal = Math.abs(amount).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    return symbol.length > 1 ? `${sign}${symbol} ${absVal}` : `${sign}${symbol}${absVal}`;
}

function formatSignedPercent(val) {
    const amount = Number(val);
    const sign = amount >= 0 ? "+" : "";
    return `${sign}${amount.toFixed(2)}%`;
}

/* ─── Price & News Live Refresh ──────────────────────────── */
async function triggerPriceAndNewsRefresh(manual = false) {
    const symbol   = window.TRADE_CONTEXT ? window.TRADE_CONTEXT.symbol   : null;
    const currency = window.TRADE_CONTEXT ? window.TRADE_CONTEXT.currency : "USD";
    if (!symbol) return;

    const btnPrice = document.getElementById("refresh-stock-btn");
    const btnNews  = document.getElementById("refresh-news-btn");
    [btnPrice, btnNews].forEach(btn => { if (btn) btn.classList.add("loading"); });

    // Show skeleton loaders for manual refresh
    if (manual) {
        const newsContainer = document.getElementById("news-grid-container");
        if (newsContainer) {
            newsContainer.innerHTML = Array(4).fill(`
                <div class="news-card news-skeleton">
                    <div class="news-thumb skel-block"></div>
                    <div class="news-body">
                        <div class="skel-line skel-line-sm"></div>
                        <div class="skel-line"></div>
                        <div class="skel-line skel-line-lg"></div>
                    </div>
                </div>`).join("");
        }
    }

    try {
        const response = await fetch(`/api/stock-update?symbol=${encodeURIComponent(symbol)}`);
        const data     = await response.json();

        if (data.error) {
            console.error("API error during refresh:", data.error);
            return;
        }

        // ── 1. Update Price Card ──────────────────────────
        const priceValEl       = document.getElementById("price-val");
        const priceChangeValEl = document.getElementById("price-change-val");
        const priceCardEl      = document.getElementById("price-card-el");

        if (priceValEl && priceChangeValEl) {
            const oldPrice  = parseFloat(priceValEl.dataset.raw || 0);
            const newPrice  = data.current_price;
            const isPositive = data.price_change >= 0;

            priceValEl.textContent   = formatCurrency(newPrice, data.currency);
            priceValEl.dataset.raw   = newPrice;
            priceChangeValEl.textContent = `${formatSignedCurrency(data.price_change, data.currency)} (${formatSignedPercent(data.price_change_percent)})`;
            priceChangeValEl.className   = isPositive ? "text-positive" : "text-negative";

            // Glow animation
            if (priceCardEl) {
                priceCardEl.classList.remove("glow-up", "glow-down");
                void priceCardEl.offsetWidth;
                priceCardEl.classList.add(isPositive ? "glow-up" : "glow-down");
            }

            // Flash price value briefly
            priceValEl.classList.remove("price-flash-up", "price-flash-down");
            void priceValEl.offsetWidth;
            priceValEl.classList.add(newPrice >= oldPrice ? "price-flash-up" : "price-flash-down");
        }

        // ── 2. Update fetched_at timestamp ───────────────
        const updatedTimeEl = document.getElementById("news-updated-time");
        if (updatedTimeEl && data.fetched_at) {
            updatedTimeEl.textContent = data.fetched_at;
        }

        // ── 3. Update News Grid ───────────────────────────
        const newsContainer = document.getElementById("news-grid-container");
        if (newsContainer) {
            if (data.news && data.news.length > 0) {
                newsContainer.innerHTML = data.news.map((article, idx) => {
                    const thumbHtml = article.thumbnail
                        ? `<div class="news-thumb"><img src="${article.thumbnail}" alt="" loading="lazy"></div>`
                        : "";
                    const summaryHtml = article.summary
                        ? `<p class="news-summary">${article.summary}</p>`
                        : "";
                    return `
                        <a class="news-card news-fade-in" href="${article.url}" target="_blank" rel="noopener noreferrer" style="animation-delay: ${idx * 0.06}s;">
                            ${thumbHtml}
                            <div class="news-body">
                                <div class="news-meta">
                                    <span class="news-publisher">${article.publisher}</span>
                                    <span class="news-time">${article.published}</span>
                                </div>
                                <h3 class="news-title">${article.title}</h3>
                                ${summaryHtml}
                            </div>
                        </a>`;
                }).join("");
            } else {
                newsContainer.innerHTML = `<div class="text-center py-4 w-100 text-muted">No news articles found for ${symbol}.</div>`;
            }
        }

        // ── 4. Sync TRADE_CONTEXT ────────────────────────
        if (window.TRADE_CONTEXT) {
            window.TRADE_CONTEXT = Object.assign({}, window.TRADE_CONTEXT, {
                price:  data.current_price,
                change: data.price_change_percent,
                news:   data.news && data.news.length > 0
                    ? data.news.slice(0, 3).map(a => a.title)
                    : window.TRADE_CONTEXT.news,
            });
        }

    } catch (err) {
        console.error("Failed to fetch stock updates:", err);
    } finally {
        [btnPrice, btnNews].forEach(btn => { if (btn) btn.classList.remove("loading"); });
        // Reset countdown after manual refresh
        if (manual) startPriceCountdown();
    }
}

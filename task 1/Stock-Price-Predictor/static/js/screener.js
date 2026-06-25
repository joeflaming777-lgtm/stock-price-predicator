/* ═══════════════════════════════════════════════════════════
   Stock Screener — live table with sort, filter, tabs
   ═══════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    // ── State ────────────────────────────────────────────────
    let allStocks    = [];   // full fetched list for current tab
    let sortCol      = '';
    let sortDir      = 'asc';
    let activeList   = 'nifty50';

    // ── Helpers ──────────────────────────────────────────────
    function fmt(n, decimals = 2) {
        if (n == null || isNaN(n)) return '—';
        return Number(n).toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    }

    function fmtPrice(n, exchange) {
        if (n == null || isNaN(n)) return '—';
        const sym = (exchange === 'NSE' || exchange === 'BSE') ? '₹' : '$';
        return sym + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function changeClass(pct) {
        if (pct == null) return 'scr-neutral';
        return pct >= 0 ? 'scr-up' : 'scr-down';
    }

    function changeLabel(pct) {
        if (pct == null) return '—';
        const sign = pct >= 0 ? '+' : '';
        return `${sign}${fmt(pct)}%`;
    }

    // ── DOM refs ─────────────────────────────────────────────
    const skeleton   = () => document.getElementById('scr-skeleton');
    const tableWrap  = () => document.getElementById('scr-table-container');
    const tbody      = () => document.getElementById('scr-tbody');
    const errBox     = () => document.getElementById('scr-error');
    const countEl    = () => document.getElementById('scr-count');
    const sectorSel  = () => document.getElementById('scr-sector');
    const sortSel    = () => document.getElementById('scr-sort');
    const searchInp  = () => document.getElementById('scr-search');

    // ── Market Indices bar ───────────────────────────────────
    async function loadIndices() {
        const inner = document.getElementById('indices-inner');
        if (!inner) return;
        try {
            const res  = await fetch('/api/market-indices');
            const data = await res.json();
            if (!data.indices || !data.indices.length) return;

            inner.innerHTML = data.indices.map(idx => {
                const pct = idx.change_pct;
                const cls = pct == null ? '' : pct >= 0 ? 'idx-up' : 'idx-down';
                const arrow = pct == null ? '' : pct >= 0 ? '▲' : '▼';
                const priceStr = idx.price != null ? Number(idx.price).toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '—';
                const pctStr   = pct != null ? `${arrow} ${Math.abs(pct).toFixed(2)}%` : '';
                return `<span class="idx-item"><span class="idx-name">${idx.name}</span><span class="idx-val">${priceStr}</span><span class="idx-chg ${cls}">${pctStr}</span></span>`;
            }).join('');
        } catch (e) {
            inner.innerHTML = '';
        }
    }

    // ── Sector filter population ─────────────────────────────
    function populateSectors(stocks) {
        const sel = sectorSel();
        if (!sel) return;
        const sectors = [...new Set(stocks.map(s => s.sector).filter(Boolean))].sort();
        const cur = sel.value;
        sel.innerHTML = '<option value="">All Sectors</option>' +
            sectors.map(s => `<option value="${s}"${s === cur ? ' selected' : ''}>${s}</option>`).join('');
    }

    // ── Sorting ──────────────────────────────────────────────
    function applySort(stocks) {
        const val = sortSel() ? sortSel().value : 'name-asc';
        const [col, dir] = val.split('-');
        return [...stocks].sort((a, b) => {
            let av = a[col === 'change' ? 'change_pct' : col];
            let bv = b[col === 'change' ? 'change_pct' : col];
            if (av == null) return 1;
            if (bv == null) return -1;
            if (typeof av === 'string') {
                av = av.toLowerCase(); bv = (bv || '').toString().toLowerCase();
                return dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
            }
            return dir === 'asc' ? av - bv : bv - av;
        });
    }

    // ── Render table ─────────────────────────────────────────
    function renderTable() {
        const sector  = sectorSel()  ? sectorSel().value  : '';
        const query   = searchInp()  ? searchInp().value.toLowerCase().trim() : '';

        let stocks = allStocks;

        if (sector) stocks = stocks.filter(s => s.sector === sector);
        if (query)  stocks = stocks.filter(s =>
            s.name.toLowerCase().includes(query) ||
            s.symbol.toLowerCase().includes(query)
        );

        stocks = applySort(stocks);

        const tb = tbody();
        if (!tb) return;

        if (stocks.length === 0) {
            tb.innerHTML = `<tr><td colspan="9" class="text-center py-5 text-muted">No stocks match your filter.</td></tr>`;
            if (countEl()) countEl().textContent = '';
            return;
        }

        tb.innerHTML = stocks.map((s, i) => {
            const cls  = changeClass(s.change_pct);
            const chg  = changeLabel(s.change_pct);
            const priceStr = fmtPrice(s.price, s.exchange);
            const hiStr    = s.week_high != null ? fmtPrice(s.week_high, s.exchange) : '—';
            const loStr    = s.week_low  != null ? fmtPrice(s.week_low,  s.exchange) : '—';
            const ticker   = encodeURIComponent(s.symbol);
            const exBadge  = `<span class="scr-exchange-badge">${s.exchange || ''}</span>`;
            return `
            <tr class="scr-row" data-symbol="${s.symbol}">
                <td class="scr-num">${i + 1}</td>
                <td>
                    <div class="scr-company">
                        <div class="scr-avatar">${s.name.charAt(0)}</div>
                        <div>
                            <div class="scr-name">${s.name}</div>
                            <div class="scr-sector-tag">${s.sector || '—'}</div>
                        </div>
                    </div>
                </td>
                <td><span class="scr-sym">${s.symbol.replace('.NS', '').replace('.BO', '')}</span>${exBadge}</td>
                <td class="d-none d-sm-table-cell">${s.sector || '—'}</td>
                <td class="text-end scr-price">${priceStr}</td>
                <td class="text-end"><span class="scr-badge ${cls}">${chg}</span></td>
                <td class="text-end d-none d-md-table-cell scr-muted">${hiStr}</td>
                <td class="text-end d-none d-md-table-cell scr-muted">${loStr}</td>
                <td class="text-center">
                    <a href="/?symbol=${ticker}" class="btn btn-sm scr-analyze-btn" title="Run ML Analysis">
                        📊 Analyze
                    </a>
                </td>
            </tr>`;
        }).join('');

        if (countEl()) countEl().textContent = `Showing ${stocks.length} of ${allStocks.length} stocks`;
    }

    // ── Fetch stock data ─────────────────────────────────────
    async function loadStocks(listName) {
        // Show skeleton, hide table
        skeleton().classList.remove('d-none');
        tableWrap().classList.add('d-none');
        errBox().classList.add('d-none');

        try {
            const res  = await fetch(`/api/screener-data?list=${listName}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            allStocks = data.stocks || [];
            populateSectors(allStocks);

            skeleton().classList.add('d-none');
            tableWrap().classList.remove('d-none');
            renderTable();
        } catch (err) {
            skeleton().classList.add('d-none');
            const eb = errBox();
            eb.textContent = `⚠️ Could not load stock data: ${err.message}`;
            eb.classList.remove('d-none');
        }
    }

    // ── Tab switching ────────────────────────────────────────
    function switchTab(listName) {
        activeList = listName;
        document.querySelectorAll('.scr-tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.list === listName);
            btn.setAttribute('aria-selected', btn.dataset.list === listName ? 'true' : 'false');
        });
        loadStocks(listName);
    }

    // ── Theme toggle (reuse dashboard.js applyTheme if available) ──
    function initTheme() {
        const btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.addEventListener('click', function () {
                if (typeof applyTheme === 'function') {
                    applyTheme(document.documentElement.getAttribute('data-theme') !== 'dark', true);
                } else {
                    const dark = document.documentElement.getAttribute('data-theme') !== 'dark';
                    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
                    localStorage.setItem('theme', dark ? 'dark' : 'light');
                }
            });
        }
    }

    // ── Init ─────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        initTheme();
        loadIndices();

        // Tab buttons
        document.querySelectorAll('.scr-tab').forEach(btn => {
            btn.addEventListener('click', () => switchTab(btn.dataset.list));
        });

        // Sector filter
        const sec = sectorSel();
        if (sec) sec.addEventListener('change', renderTable);

        // Sort dropdown
        const srt = sortSel();
        if (srt) srt.addEventListener('change', renderTable);

        // Search filter (debounced)
        let searchTimer;
        const srch = searchInp();
        if (srch) {
            srch.addEventListener('input', () => {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(renderTable, 200);
            });
        }

        // Column header sort (click on <th>)
        document.querySelectorAll('.scr-th-sortable').forEach(th => {
            th.style.cursor = 'pointer';
            th.addEventListener('click', () => {
                const col = th.dataset.col;
                const map = { name: 'name-asc', sector: 'name-asc', price: 'price-desc', change_pct: 'change-desc' };
                if (srt) {
                    const curVal = srt.value;
                    const newVal = curVal === (col === 'change_pct' ? 'change-desc' : col + '-desc')
                        ? (col === 'change_pct' ? 'change-asc' : col + '-asc')
                        : (col === 'change_pct' ? 'change-desc' : col + '-desc');
                    srt.value = newVal;
                }
                renderTable();
            });
        });

        // Load default tab
        switchTab('nifty50');
    });
})();

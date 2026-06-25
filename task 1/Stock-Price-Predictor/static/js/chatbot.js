/* ═══════════════════════════════════════════════════
   TradeMind AI — Floating Trading Chatbot
   ═══════════════════════════════════════════════════ */
(function () {
    'use strict';

    const API_URL   = '/api/chat';
    const MAX_HIST  = 20;      // max stored history turns
    const TYPING_MS = 600;     // typing indicator delay

    const SUGGESTIONS = [
        '💡 Explain moving averages',
        '📊 What is RSI indicator?',
        '🟢 When should I buy a stock?',
        '🔴 When should I sell?',
        '🛡️ How to set a stop-loss?',
        '💰 Explain position sizing',
        '📈 What is swing trading?',
        '🧠 Trading psychology tips',
        '📰 How to trade earnings news?',
        '🕯️ Explain candlestick patterns',
    ];

    // ── State ────────────────────────────────────────
    let history     = [];
    let isOpen      = false;
    let isTyping    = false;
    let stockCtx    = '';

    // ── Inject HTML ──────────────────────────────────
    function injectHTML() {
        const wrap = document.createElement('div');
        wrap.id    = 'tm-chatbot';
        wrap.innerHTML = `
<!-- Floating Bubble -->
<button id="tm-bubble" aria-label="Open TradeMind AI chat" title="TradeMind AI – Trading Assistant">
  <span class="tm-bubble-icon">🤖</span>
  <span class="tm-bubble-badge">AI</span>
  <span class="tm-pulse-ring"></span>
</button>

<!-- Chat Window -->
<div id="tm-window" class="tm-hidden" role="dialog" aria-label="TradeMind AI Chat">

  <!-- Header -->
  <div class="tm-header">
    <div class="tm-header-left">
      <div class="tm-avatar">🤖</div>
      <div class="tm-header-info">
        <span class="tm-bot-name">TradeMind AI</span>
        <span class="tm-bot-status"><span class="tm-status-dot"></span>Online</span>
      </div>
    </div>
    <div class="tm-header-actions">
      <button id="tm-clear" title="Clear conversation" aria-label="Clear chat">🗑️</button>
      <button id="tm-close" title="Close chat" aria-label="Close chat">✕</button>
    </div>
  </div>

  <!-- Messages -->
  <div id="tm-messages" class="tm-messages">
    <div class="tm-welcome">
      <div class="tm-welcome-icon">🤖</div>
      <p><strong>TradeMind AI</strong> — your expert trading coach!</p>
      <p>Ask me anything about stocks, strategies, technical analysis, and risk management.</p>
      <div class="tm-suggestions" id="tm-suggestions">
        ${SUGGESTIONS.slice(0, 5).map(s =>
            `<button class="tm-chip">${s}</button>`
        ).join('')}
      </div>
    </div>
  </div>

  <!-- Context badge (shown when stock is loaded) -->
  <div id="tm-ctx-bar" class="tm-ctx-bar tm-hidden">
    <span>📊 Analyzing: <strong id="tm-ctx-symbol">—</strong></span>
  </div>

  <!-- Input -->
  <div class="tm-input-row">
    <textarea id="tm-input"
              placeholder="Ask about trading strategies, signals, risk…"
              rows="1"
              maxlength="500"
              aria-label="Chat message"></textarea>
    <button id="tm-send" aria-label="Send message">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="22" y1="2" x2="11" y2="13"></line>
        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
      </svg>
    </button>
  </div>
  <div class="tm-footer">⚠️ For educational purposes only — not financial advice.</div>
</div>
`;
        document.body.appendChild(wrap);
    }

    // ── Markdown → HTML (lightweight) ───────────────
    function mdToHtml(text) {
        return text
            // Code blocks
            .replace(/```[\s\S]*?```/g, m => {
                const code = m.replace(/^```[^\n]*\n?/, '').replace(/```$/, '');
                return `<pre><code>${esc(code.trim())}</code></pre>`;
            })
            // Bold
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            // Bullet lines (•, -, ✅, ❌, etc.)
            .replace(/^([•\-✅❌🟢🔴⚡📊📈💰🛡️🧠📰🕯️💡⚠️📌🎯💼✓→←])\s+(.+)$/gm, '<li>$1 $2</li>')
            // Numbered list
            .replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
            // Wrap consecutive <li> in <ul>
            .replace(/(<li>[\s\S]+?<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
            // Line breaks
            .replace(/\n{2,}/g, '</p><p>')
            .replace(/\n/g, '<br>')
            // Wrap in paragraph
            .replace(/^(?!<)/, '<p>')
            .replace(/(?<!>)$/, '</p>');
    }

    function esc(s) {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    // ── Message rendering ────────────────────────────
    function appendMessage(role, text, isHtml) {
        const msgs  = document.getElementById('tm-messages');
        const div   = document.createElement('div');
        div.className = `tm-msg tm-msg-${role}`;

        const bubble = document.createElement('div');
        bubble.className = 'tm-bubble';

        if (isHtml || role === 'bot') {
            bubble.innerHTML = mdToHtml(text);
        } else {
            bubble.textContent = text;
        }

        if (role === 'bot') {
            const avatar = document.createElement('div');
            avatar.className = 'tm-msg-avatar';
            avatar.textContent = '🤖';
            div.appendChild(avatar);
        }

        div.appendChild(bubble);
        msgs.appendChild(div);
        msgs.scrollTop = msgs.scrollHeight;
        return div;
    }

    function showTyping() {
        const msgs = document.getElementById('tm-messages');
        const div  = document.createElement('div');
        div.id = 'tm-typing';
        div.className = 'tm-msg tm-msg-bot';
        div.innerHTML = `
            <div class="tm-msg-avatar">🤖</div>
            <div class="tm-bubble tm-typing-bubble">
                <span></span><span></span><span></span>
            </div>`;
        msgs.appendChild(div);
        msgs.scrollTop = msgs.scrollHeight;
    }

    function hideTyping() {
        const t = document.getElementById('tm-typing');
        if (t) t.remove();
    }

    // ── Send message ─────────────────────────────────
    async function sendMessage(text) {
        if (!text || isTyping) return;
        text = text.trim();
        if (!text) return;

        // Hide suggestions after first message
        const suggestions = document.getElementById('tm-suggestions');
        if (suggestions) suggestions.style.display = 'none';

        appendMessage('user', text);
        history.push({ role: 'user', content: text });
        if (history.length > MAX_HIST) history.splice(0, 2);

        // Clear input
        const input = document.getElementById('tm-input');
        input.value = '';
        input.style.height = 'auto';

        isTyping = true;
        document.getElementById('tm-send').disabled = true;

        setTimeout(showTyping, 200);

        // Abort controller — cancel the request if it takes > 30 seconds
        const controller = new AbortController();
        const timeoutId  = setTimeout(() => controller.abort(), 30000);

        try {
            const body = { message: text, stock_context: stockCtx, history: history.slice(-6) };
            const res  = await fetch(API_URL, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify(body),
                signal:  controller.signal,
            });
            clearTimeout(timeoutId);
            const data = await res.json();
            hideTyping();
            const reply = data.reply || 'Sorry, I had trouble responding. Please try again.';
            appendMessage('bot', reply);
            history.push({ role: 'bot', content: reply });
            if (history.length > MAX_HIST) history.splice(0, 2);
        } catch (err) {
            clearTimeout(timeoutId);
            hideTyping();
            if (err.name === 'AbortError') {
                appendMessage('bot', '⏱️ The request timed out. Please try again.');
            } else {
                appendMessage('bot', '⚠️ Could not reach the server. Make sure the Flask app is running and try again.');
            }
        } finally {
            isTyping = false;
            document.getElementById('tm-send').disabled = false;
            document.getElementById('tm-input').focus();
        }
    }

    // ── Stock context (built from dashboard page data) ─
    function buildStockContext() {
        if (!window.TRADE_CONTEXT) return '';
        const c = window.TRADE_CONTEXT;
        if (!c.symbol) return '';
        return [
            `Stock Symbol: ${c.symbol}`,
            c.company   ? `Company: ${c.company}`           : null,
            c.price     ? `Current Price: $${c.price}`      : null,
            c.change    ? `Price Change: ${c.change}%`      : null,
            c.trend     ? `ML Trend Signal: ${c.trend}`     : null,
            c.nextDay   ? `ML Next-Day Prediction: $${c.nextDay}` : null,
            c.sector    ? `Sector: ${c.sector}`             : null,
            c.marketCap ? `Market Cap: ${c.marketCap}`      : null,
            c.news      ? `Recent Headlines: ${c.news}`     : null,
        ].filter(Boolean).join('\n');
    }

    function updateContextBar() {
        stockCtx = buildStockContext();
        const bar = document.getElementById('tm-ctx-bar');
        const sym = document.getElementById('tm-ctx-symbol');
        if (!bar || !sym) return;
        if (window.TRADE_CONTEXT && window.TRADE_CONTEXT.symbol) {
            sym.textContent = window.TRADE_CONTEXT.symbol;
            bar.classList.remove('tm-hidden');
        } else {
            bar.classList.add('tm-hidden');
        }
    }

    // ── Open / close ─────────────────────────────────
    function openChat() {
        isOpen = true;
        document.getElementById('tm-window').classList.remove('tm-hidden');
        document.getElementById('tm-window').classList.add('tm-open');
        document.getElementById('tm-bubble').classList.add('tm-bubble-active');
        updateContextBar();
        setTimeout(() => document.getElementById('tm-input').focus(), 300);
    }

    function closeChat() {
        isOpen = false;
        document.getElementById('tm-window').classList.remove('tm-open');
        document.getElementById('tm-window').classList.add('tm-hidden');
        document.getElementById('tm-bubble').classList.remove('tm-bubble-active');
    }

    function clearChat() {
        history = [];
        const msgs = document.getElementById('tm-messages');
        msgs.innerHTML = `
            <div class="tm-welcome">
              <div class="tm-welcome-icon">🤖</div>
              <p><strong>TradeMind AI</strong> — your expert trading coach!</p>
              <p>Ask me anything about stocks, strategies, technical analysis, and risk management.</p>
              <div class="tm-suggestions" id="tm-suggestions">
                ${SUGGESTIONS.slice(0, 5).map(s =>
                    `<button class="tm-chip">${s}</button>`
                ).join('')}
              </div>
            </div>`;
        bindChips();
    }

    // ── Event bindings ───────────────────────────────
    function bindChips() {
        document.querySelectorAll('.tm-chip').forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.textContent.replace(/^[^\w]+/, '').trim();
                sendMessage(text);
            });
        });
    }

    function bindEvents() {
        document.getElementById('tm-bubble').addEventListener('click', () => {
            isOpen ? closeChat() : openChat();
        });

        document.getElementById('tm-close').addEventListener('click', closeChat);

        document.getElementById('tm-clear').addEventListener('click', clearChat);

        document.getElementById('tm-send').addEventListener('click', () => {
            sendMessage(document.getElementById('tm-input').value);
        });

        const input = document.getElementById('tm-input');

        input.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage(input.value);
            }
        });

        // Auto-resize textarea
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 110) + 'px';
        });

        bindChips();

        // Close on Escape
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && isOpen) closeChat();
        });
    }

    // ── Init ─────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        injectHTML();
        bindEvents();

        // If TRADE_CONTEXT is set by the page, update bar
        updateContextBar();

        // Mirror the existing TRADE_CONTEXT value into _tm_ctx so the
        // getter always reads the live value, even if it was set before
        // this script ran (server-side rendered inline script).
        if (window.TRADE_CONTEXT !== undefined) {
            window._tm_ctx = window.TRADE_CONTEXT;
        }
        try {
            Object.defineProperty(window, 'TRADE_CONTEXT', {
                set(val) {
                    window._tm_ctx = val;
                    updateContextBar();
                },
                get() { return window._tm_ctx; },
                configurable: true,
            });
        } catch (e) {
            // Property already non-configurable — context bar may not auto-update
        }
    });
})();

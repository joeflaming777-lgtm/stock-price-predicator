"""Flask entry point for the Stock Price Predictor application."""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

import yfinance as yf
from flask import Flask, render_template, request, jsonify

from predictor import StockPredictionError, analyze_stock

_STOCKS_JSON = Path(__file__).resolve().parent / "static" / "data" / "stocks.json"

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; rely on system env vars


app = Flask(__name__)
app.config["SECRET_KEY"] = "stock-price-predictor-dev-key"

# ─── Groq AI setup ──────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
_groq_client = None

try:
    from groq import Groq
    _GROQ_AVAILABLE = True
    print("[TradeMind] groq imported OK. API key", "SET [OK]" if GROQ_API_KEY else "NOT SET [MISSING] - add GROQ_API_KEY to .env file")
except ImportError:
    _GROQ_AVAILABLE = False
    print("[TradeMind] groq NOT installed - run: pip install groq")

def _get_groq_client():
    global _groq_client
    # Always re-read the key in case .env was loaded after module init
    key = os.environ.get("GROQ_API_KEY", "") or GROQ_API_KEY
    if key and key != "your_groq_api_key_here" and _GROQ_AVAILABLE:
        if _groq_client is None:
            _groq_client = Groq(api_key=key)
    return _groq_client


TRADING_SYSTEM_PROMPT = """You are TradeMind AI, an expert stock market trading assistant built into a live Stock Price Predictor dashboard powered by machine learning.

YOUR EXPERTISE covers:

📊 TECHNICAL ANALYSIS
- Moving Averages: SMA, EMA, Golden Cross (50MA > 200MA = bullish), Death Cross (50MA < 200MA = bearish)
- Momentum Indicators: RSI (>70 overbought, <30 oversold), MACD (signal line crossovers), Stochastic Oscillator
- Volatility: Bollinger Bands (price above upper band = overbought; below lower = oversold), ATR (Average True Range)
- Volume Analysis: High volume confirms trend strength; low volume = weak signal
- Chart Patterns: Head & Shoulders, Double Top/Bottom, Triangles (ascending/descending/symmetrical), Flags, Cups, Wedges, Pennants
- Candlestick Patterns: Doji, Hammer, Shooting Star, Engulfing, Morning/Evening Star, Spinning Top

📈 TRADING STRATEGIES
- Trend Following: Buy in uptrend, sell in downtrend; use MA crossovers to confirm
- Swing Trading: Hold 2–10 days; look for pullbacks in uptrends as entry points; target 5–15% moves
- Day Trading: Intraday moves; use 5/15-min charts; strict stop-losses; high discipline required
- Scalping: Very short holds (seconds to minutes); small profits per trade; requires fast execution
- Position Trading: Long-term (weeks to months); based on fundamentals + macro trends
- Breakout Trading: Enter when price breaks above resistance or below support with volume
- Mean Reversion: Trade when price deviates far from historical average, expecting return to mean

💰 BUY SIGNALS (Bullish)
- Price above 50-day AND 200-day MA (strong uptrend)
- Golden Cross just occurred
- RSI between 40–60 (healthy momentum) or recovering from oversold (<30)
- MACD line crosses above signal line
- Price breaking above resistance on high volume
- Positive earnings surprise or strong revenue growth
- Sector tailwind / favorable macro environment
- Stock forming higher highs and higher lows

🔴 SELL / SHORT SIGNALS (Bearish)
- Death Cross (50MA crosses below 200MA)
- RSI above 70 and declining (losing momentum)
- MACD line crosses below signal line
- Price breaks below key support level on high volume
- Negative news catalyst (earnings miss, regulatory issues, management change)
- Distribution pattern (rising price, falling volume)
- Forming lower highs and lower lows

🛡️ RISK MANAGEMENT (CRITICAL)
- Never risk more than 1–2% of total portfolio on a single trade
- Always set a Stop-Loss before entering any trade (typically 2–7% below entry)
- Target Risk/Reward ratio of at least 1:2 (risk $1 to potentially make $2)
- Take partial profits at 50% of target, let rest run with trailing stop
- Diversify: No more than 5–10% of portfolio in any single stock
- Avoid trading during earnings announcements (unless intentional strategy)
- Never trade money you can't afford to lose
- Keep a trading journal: log every trade, reason, outcome

🧠 MARKET PSYCHOLOGY
- Fear & Greed Index: Extreme Fear = buy opportunity; Extreme Greed = consider reducing exposure
- FOMO (Fear Of Missing Out) is the #1 cause of bad trades — avoid chasing pumps
- Panic Selling locks in losses — stick to your plan
- The trend is your friend until it ends
- "Cut losses short, let winners run" — the most important trading rule
- Emotion-free trading: follow rules, not feelings
- Market moves in cycles: accumulation → markup → distribution → markdown

📰 NEWS-BASED TRADING
- Market-moving news: Fed interest rate decisions, inflation data, earnings, geopolitical events
- Positive news + strong technicals = high-conviction buy
- Negative news + weak technicals = avoid or short
- "Buy the rumor, sell the news" — often price runs up before news, then drops
- Sector rotation: money flows from sector to sector; follow the flow

🎯 WHEN GIVEN STOCK DATA, provide:
1. Clear trend assessment (bullish / bearish / sideways)
2. Entry price range suggestion
3. Stop-loss level (specific price)
4. Target price (1 and 2)
5. Position sizing recommendation
6. Key risks to watch

Always format your responses clearly with emojis and bullet points for readability.
Always include relevant disclaimers.
Be encouraging, educational, and actionable.

⚠️ DISCLAIMER: All information is strictly for educational purposes. This is NOT financial advice. Always conduct your own research and consult a licensed financial advisor before making any investment decisions. Past performance does not guarantee future results."""


# ─── Fallback rule-based responses ──────────────────────────────────────────
_FALLBACK_RULES: list[tuple[list[str], str]] = [
    (["golden cross", "death cross"], """📊 **Moving Average Crossovers**

• **Golden Cross** 🟢 — 50-day MA crosses ABOVE 200-day MA
  → Strong **bullish** signal; historically precedes major uptrends
  → Strategy: Buy on the cross with a stop-loss just below the 200MA

• **Death Cross** 🔴 — 50-day MA crosses BELOW 200-day MA
  → Strong **bearish** signal; often leads to extended downtrends
  → Strategy: Reduce longs, consider defensive assets or shorts

💡 Tip: Always confirm crossovers with rising volume for stronger signals."""),

    (["moving average", "sma", "ema", "ma "], """📉 **Moving Averages Explained**

Moving averages smooth out price noise to reveal the trend direction.

• **SMA (Simple)** — equal weight to all periods; slower to react
• **EMA (Exponential)** — more weight to recent prices; faster signals

**Key levels traders watch:**
• 20-day MA → Short-term trend
• 50-day MA → Medium-term trend
• 200-day MA → Long-term trend (bull/bear market line)

**Rule of thumb:**
✅ Price > 50MA > 200MA = Strong uptrend (buy dips)
❌ Price < 50MA < 200MA = Strong downtrend (avoid or short)"""),

    (["rsi", "relative strength"], """📊 **RSI (Relative Strength Index)**

RSI measures momentum on a scale of 0–100.

• **RSI > 70** 🔴 = Overbought → Potential sell/pullback ahead
• **RSI 40–60** 🟢 = Healthy momentum → Trend is intact
• **RSI < 30** 🟢 = Oversold → Potential bounce / buy opportunity
• **RSI 30–40** ⚠️ = Weakening, watch for reversal

**Advanced RSI:**
• RSI Divergence: Price makes new high but RSI doesn't → bearish warning
• RSI > 50 crossing upward in an uptrend = buy signal confirmation"""),

    (["macd"], """📈 **MACD Indicator**

MACD = 12-day EMA minus 26-day EMA, plotted with a 9-day signal line.

🟢 **Bullish Signals:**
• MACD line crosses ABOVE signal line → Buy
• MACD histogram turns from negative to positive
• MACD crosses above the zero line

🔴 **Bearish Signals:**
• MACD line crosses BELOW signal line → Sell
• Histogram shrinks while price rises (divergence)
• MACD crosses below zero line

💡 Best used in combination with trend confirmation (e.g., price above 50MA)."""),

    (["bollinger", "band"], """📊 **Bollinger Bands**

Three bands: Middle (20-day SMA) + Upper/Lower (2 standard deviations)

• **Price touches upper band** 🔴 = Overbought; potential pullback
• **Price touches lower band** 🟢 = Oversold; potential bounce
• **Band squeeze (bands narrow)** ⚡ = Volatility contraction; big move coming!
• **Band expansion** = Volatility spike; trend acceleration

**Strategy:**
• In an uptrend: Buy dips to the middle band (20-day SMA)
• Breakout above upper band on high volume = strong continuation signal"""),

    (["stop loss", "stop-loss", "stoploss"], """🛡️ **Stop-Loss Strategy**

A stop-loss is your most important risk management tool. NEVER trade without one.

**How to set stop-losses:**
• **Fixed %**: Set 3–7% below entry (use 2–3% for volatile stocks)
• **ATR-based**: Entry minus 1.5–2× ATR (adapts to stock's volatility)
• **Below support**: Place just below the nearest support level
• **Below moving average**: Below 20MA for short trades, 50MA for swing trades

**Trailing Stop-Loss** (for winners):
• Move stop up as price rises to lock in profits
• Trail by 5–10% below the recent high

⚠️ Rule: If your stop is hit, EXIT. No exceptions. No "hoping it recovers."
The market doesn't know your entry price — protect your capital."""),

    (["position size", "position sizing", "how much to buy", "how many shares"], """💰 **Position Sizing — The Most Underrated Skill**

**The 2% Rule:**
→ Never risk more than 2% of your total portfolio on one trade

**Formula:**
```
Position Size = (Portfolio × Risk %) ÷ (Entry Price - Stop-Loss)
```

**Example:**
• Portfolio: $10,000
• Risk per trade: 2% = $200
• Entry: $50, Stop-Loss: $47 (Risk per share = $3)
• Position Size = $200 ÷ $3 = **66 shares** ($3,300 total position)

This way, even if your stop is hit, you only lose $200 (2% of portfolio) — not devastating!

📌 Consistent position sizing prevents one bad trade from wiping you out."""),

    (["swing trading", "swing trade"], """📈 **Swing Trading Strategy**

Hold trades for 2–10 days to capture short-to-medium term moves.

**Entry Criteria:**
✅ Stock in a clear uptrend (price > 50MA)
✅ Recent pullback to support or moving average
✅ RSI pulling back from overbought, not yet oversold
✅ Volume dried up during pullback (healthy consolidation)

**Entry Trigger:**
→ Buy when price bounces from support with rising volume

**Targets:**
• Target 1: Previous swing high (+5–8%)
• Target 2: Next resistance level (+10–15%)

**Stop-Loss:**
→ Just below the recent swing low or pullback low

🕐 Best time frames: Daily chart for setup, 4-hour for entry timing"""),

    (["day trading", "intraday"], """⚡ **Day Trading Basics**

Buy and sell within the same trading day. No overnight positions.

**Requirements:**
• Pattern Day Trader rule (US): Minimum $25,000 account
• Reliable broker with fast execution
• Level 2 quotes and direct access
• Strict emotional discipline

**Day Trading Strategies:**
• **Momentum**: Trade stocks with pre-market news catalysts
• **Opening Range Breakout**: Buy break above first 15–30 min high
• **VWAP Trading**: Use VWAP as dynamic support/resistance

⚠️ Warning: 70–80% of day traders lose money. Only do this with extensive practice on paper trading first.

📌 Recommended: Start with swing trading to learn before day trading."""),

    (["scalping", "scalp"], """⚡ **Scalping Strategy**

Ultra-short-term trades lasting seconds to minutes. Very small profits per trade.

• Target: $0.10–$0.50 profit per share
• High frequency: 10–100+ trades per day
• Requires: Extremely fast execution, low commission broker, intense focus

**Scalping Setups:**
• Level 2 order flow analysis
• Time & Sales (tape reading)
• 1-minute and tick charts
• Tight bid-ask spreads (liquid stocks only)

⚠️ Not recommended for beginners. Requires significant time, capital, and psychological discipline.

💡 Better starting strategy: Swing trading or trend following."""),

    (["risk management", "risk reward", "risk/reward"], """🛡️ **Risk Management — Your Most Important Skill**

**The Golden Rules:**
1. **Never risk more than 1–2% of portfolio per trade**
2. **Always set a stop-loss before entering**
3. **Target minimum 1:2 risk/reward ratio** (risk $1 to make $2)
4. **Diversify across sectors** (max 5–10% per stock)
5. **Never average down into a losing trade**
6. **Keep cash reserves** (30–50%) for opportunities

**Risk/Reward Calculation:**
• Entry: $100, Stop-Loss: $95, Target: $110
• Risk = $5, Reward = $10 → Ratio = 1:2 ✅

**Common Risk Mistakes:**
❌ No stop-loss (hoping it recovers)
❌ Moving stop-loss to avoid being stopped out
❌ Over-leveraging (trading too large)
❌ Revenge trading after a loss"""),

    (["buy", "should i buy", "when to buy", "good time to buy"], """🟢 **When to Buy a Stock**

**Strong Buy Signals:**
✅ Price above 50-day AND 200-day moving averages
✅ Golden Cross (50MA > 200MA)
✅ RSI between 40–60 (healthy momentum, not overbought)
✅ MACD crosses above signal line
✅ Stock breaking out of consolidation on HIGH volume
✅ Strong recent earnings / revenue growth
✅ Sector in favor / positive market sentiment

**Best Entry Points:**
• Pullbacks to rising 20-day or 50-day MA
• Breakout retest (price breaks resistance, pulls back, holds as support)
• After a basing period (flat consolidation after a downtrend)

⚠️ Always set a stop-loss at entry.
⚠️ Don't chase stocks that have already run 20%+ without consolidation."""),

    (["sell", "when to sell", "take profit", "exit"], """🔴 **When to Sell a Stock**

**Strong Sell / Exit Signals:**
❌ Death Cross (50MA crosses below 200MA)
❌ RSI above 70 and rolling over (losing momentum)
❌ MACD crosses below signal line
❌ Price breaks below key support on high volume
❌ Negative earnings surprise or guidance cut
❌ Stock forms lower highs and lower lows (downtrend confirmed)

**Profit-Taking Strategy:**
• Sell 50% of position at Target 1 (8–12% gain)
• Move stop-loss to breakeven for remaining shares
• Let remaining 50% run to Target 2 with trailing stop

**The Hard Rule:**
→ If your stop-loss is hit → EXIT. No excuses.
→ A small loss is far better than a catastrophic one.

💡 Remember: "The first loss is the best loss." Cut losers fast."""),

    (["candlestick", "candle", "doji", "hammer", "engulfing"], """🕯️ **Candlestick Patterns**

**Bullish Reversal Patterns:**
🟢 **Hammer** — small body, long lower wick; after a downtrend = reversal signal
🟢 **Bullish Engulfing** — large green candle engulfs previous red candle
🟢 **Morning Star** — 3-candle pattern; red, small doji, green = strong reversal
🟢 **Dragonfly Doji** — open/close at top with long lower wick

**Bearish Reversal Patterns:**
🔴 **Shooting Star** — small body at bottom, long upper wick; after uptrend = warning
🔴 **Bearish Engulfing** — large red candle engulfs previous green candle
🔴 **Evening Star** — 3-candle pattern; green, small doji, red = reversal
🔴 **Gravestone Doji** — open/close at bottom with long upper wick

💡 Candlestick patterns work best at key support/resistance levels."""),

    (["support", "resistance", "level"], """📊 **Support & Resistance Levels**

**Support** — A price floor where buyers step in (demand > supply)
**Resistance** — A price ceiling where sellers dominate (supply > demand)

**How to Identify:**
• Previous swing highs/lows
• Round numbers ($50, $100, $200)
• Moving averages (20MA, 50MA, 200MA)
• Volume profile high nodes

**Trading Rules:**
• **Buy near support** with stop-loss just below it
• **Sell/take profits near resistance**
• **Breakout above resistance** = new support level formed (buy the retest)
• **Break below support** = new resistance (avoid or short)

💡 The more times a level has been tested, the more significant it is."""),

    (["portfolio", "diversif"], """💼 **Portfolio Management**

**Diversification Rules:**
• Max 5–10% of portfolio in any single stock
• Spread across at least 5–10 different stocks
• Hold exposure in multiple sectors (tech, healthcare, finance, energy, etc.)
• Consider geographic diversification (US, international, emerging markets)

**Portfolio Types:**
• **Aggressive Growth**: 80% growth stocks, 20% cash/bonds
• **Balanced**: 60% stocks, 20% bonds, 20% cash/alternatives
• **Conservative**: 40% stocks, 40% bonds, 20% defensive assets

**Rebalancing:**
→ Review and rebalance portfolio quarterly
→ Trim winners that grow too large (>15% of portfolio)
→ Add to positions at support levels during healthy pullbacks"""),

    (["psychology", "emotion", "fomo", "fear", "greed"], """🧠 **Trading Psychology**

The #1 reason traders fail: **Emotions, not strategy**.

**Common Psychological Traps:**
❌ **FOMO** (Fear Of Missing Out) — Chasing a stock after it's already up 30%
❌ **Panic Selling** — Selling at the bottom due to fear
❌ **Overconfidence** — Trading too large after a winning streak
❌ **Revenge Trading** — Doubling down after a loss to "get it back"
❌ **Analysis Paralysis** — Over-thinking and missing good setups

**How to Trade Emotion-Free:**
✅ Write down your trading plan BEFORE you enter
✅ Define entry, stop-loss, and target in advance
✅ Never check your P&L while in a trade
✅ Accept losses as the cost of doing business
✅ Take breaks after 3 consecutive losses
✅ Keep a trading journal

💡 "The market rewards discipline and punishes emotion." """),

    (["news", "catalyst", "earnings"], """📰 **Trading with News & Catalysts**

**High-Impact News Events:**
• Earnings reports (EPS beat/miss)
• Fed interest rate decisions
• Inflation data (CPI, PPI)
• GDP and employment data
• Geopolitical events
• Sector-specific news (FDA approvals, product launches)

**"Buy the Rumor, Sell the News" Pattern:**
→ Stocks often run up INTO an expected positive event
→ Then DROP after the news is confirmed ("sell the news")
→ Wait for post-announcement direction before trading

**Earnings Strategy:**
• Avoid holding through earnings unless intentional (high risk)
• If bullish, buy a week before earnings, sell the day before
• After a positive earnings surprise: buy the first pullback

💡 Always check upcoming earnings dates before buying a stock."""),

    (["hello", "hi", "hey", "start", "help", "what can you do"], """👋 **Welcome to TradeMind AI!**

I'm your personal trading assistant. Here's what I can help you with:

📊 **Technical Analysis** — Moving averages, RSI, MACD, Bollinger Bands, candlestick patterns
📈 **Trading Strategies** — Swing trading, day trading, scalping, trend following, breakout trading
🛡️ **Risk Management** — Stop-losses, position sizing, risk/reward ratios
🧠 **Market Psychology** — Overcoming FOMO, trading discipline, emotion control
📰 **News Trading** — How to trade earnings, catalysts, and market-moving events
💼 **Portfolio Management** — Diversification, rebalancing, asset allocation
🟢 **Buy/Sell Signals** — When to enter and exit trades

**Try asking:**
• "Should I buy this stock?"
• "Explain the golden cross"
• "What is proper position sizing?"
• "How do I set a stop-loss?"
• "Explain swing trading strategy"

⚠️ I provide education and analysis — always do your own research!"""),
]

_GENERIC_FALLBACK = [
    """📊 Great question! I'm here to help you with trading education and market analysis.

**I can explain:**
• Technical indicators (RSI, MACD, Moving Averages, Bollinger Bands)
• Trading strategies (swing trading, day trading, scalping, trend following)
• Risk management techniques (stop-loss, position sizing, risk/reward)
• Buy and sell signals based on technical analysis
• Trading psychology and discipline

Try asking me about a specific topic, or if you've analyzed a stock using the dashboard above, I can give you more targeted insights!

⚠️ Educational purposes only — not financial advice.""",

    """💡 I specialize in trading education and market analysis!

**Popular topics to explore:**
• "What does the RSI indicator mean?"
• "How do I use moving averages?"
• "Explain support and resistance"
• "What is swing trading?"
• "How do I manage risk in trading?"

If you have a stock loaded in the dashboard, ask me: "Should I buy [SYMBOL]?" and I'll analyze the available data for you!""",
]


def _fallback_reply(message: str) -> str:
    msg = message.lower()
    for keywords, response in _FALLBACK_RULES:
        if any(kw in msg for kw in keywords):
            return response
    return random.choice(_GENERIC_FALLBACK)


def _groq_reply(user_message: str, stock_context: str, history: list) -> str:
    client = _get_groq_client()
    if client is None:
        print("[TradeMind] No Groq client - using rule-based fallback. Set GROQ_API_KEY in .env")
        return _fallback_reply(user_message)
    try:
        # Build message list for Groq (OpenAI-compatible format)
        messages = [{"role": "system", "content": TRADING_SYSTEM_PROMPT}]

        # Add conversation history (last 6 turns)
        for turn in history[-6:]:
            role = turn.get("role", "user")
            if role == "bot":
                role = "assistant"
            messages.append({"role": role, "content": turn.get("content", "")})

        # Build the current user message (inject stock context if available)
        full_message = user_message
        if stock_context:
            full_message = f"[CURRENT STOCK DATA]\n{stock_context}\n\n[USER QUESTION]\n{user_message}"

        messages.append({"role": "user", "content": full_message})

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.65,
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as exc:
        print(f"[TradeMind] Groq API error: {exc}")
        return _fallback_reply(user_message)


# ─── Jinja2 filters ─────────────────────────────────────────────────────────
@app.template_filter("currency")
def currency_filter(value: float) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


@app.template_filter("signed_currency")
def signed_currency_filter(value: float) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0
    sign = "+" if amount >= 0 else "-"
    return f"{sign}${abs(amount):,.2f}"


@app.template_filter("signed_percent")
def signed_percent_filter(value: float) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0
    sign = "+" if amount >= 0 else ""
    return f"{sign}{amount:.2f}%"


# ─── Routes ─────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    symbol = "AAPL"
    result = None
    error = None

    if request.method == "POST":
        symbol = request.form.get("symbol", "AAPL").strip().upper()
    elif request.args.get("symbol"):
        symbol = request.args.get("symbol", "AAPL").strip().upper()

    try:
        result = analyze_stock(symbol)
    except StockPredictionError as exc:
        error = str(exc)
    except Exception as exc:
        error = f"Unexpected error while analyzing {symbol}: {exc}"

    return render_template("index.html", result=result, symbol=symbol, error=error)


@app.route("/api/chat", methods=["POST"])
def chat():
    """AI trading chatbot endpoint."""
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    stock_context = (data.get("stock_context") or "").strip()
    history = data.get("history") or []

    if not user_message:
        return jsonify({"reply": "Please type a message."})

    if len(user_message) > 600:
        user_message = user_message[:600]

    reply = _groq_reply(user_message, stock_context, history)
    return jsonify({"reply": reply, "ai_powered": _get_groq_client() is not None})


@app.route("/about")
def about():
    return render_template("about.html")


# ─── Screener routes ─────────────────────────────────────────────────────────
@app.route("/screener")
def screener():
    return render_template("screener.html")


@app.route("/api/screener-data")
def screener_data():
    """Batch-fetch last-close prices for Nifty50 or US30."""
    list_name = request.args.get("list", "nifty50")
    try:
        with open(_STOCKS_JSON, encoding="utf-8") as fh:
            stocks_db = json.load(fh)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    tickers_info = stocks_db.get(list_name, [])
    if not tickers_info:
        return jsonify({"stocks": [], "list": list_name})

    symbols = [s["symbol"] for s in tickers_info]

    try:
        raw = yf.download(
            symbols,
            period="5d",
            interval="1d",
            auto_adjust=False,
            progress=False,
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    results = []
    for stock in tickers_info:
        sym = stock["symbol"]
        try:
            # Multi-ticker download → raw["Close"] is a DataFrame
            # Single-ticker download → raw["Close"] is a Series
            if len(symbols) == 1:
                close_series = raw["Close"].dropna()
                high_series  = raw["High"].dropna()
                low_series   = raw["Low"].dropna()
            else:
                close_series = raw["Close"][sym].dropna()
                high_series  = raw["High"][sym].dropna()
                low_series   = raw["Low"][sym].dropna()

            if len(close_series) == 0:
                raise ValueError("no data")

            curr  = float(close_series.iloc[-1])
            prev  = float(close_series.iloc[-2]) if len(close_series) >= 2 else curr
            chg   = ((curr - prev) / prev * 100) if prev else 0
            hi52  = round(float(high_series.max()), 2) if len(high_series) else None
            lo52  = round(float(low_series.min()),  2) if len(low_series)  else None

            results.append({
                "symbol":     sym,
                "name":       stock["name"],
                "sector":     stock.get("sector", ""),
                "exchange":   stock.get("exchange", ""),
                "price":      round(curr, 2),
                "change_pct": round(chg,  2),
                "week_high":  hi52,
                "week_low":   lo52,
            })
        except Exception:
            results.append({
                "symbol":     sym,
                "name":       stock["name"],
                "sector":     stock.get("sector", ""),
                "exchange":   stock.get("exchange", ""),
                "price":      None,
                "change_pct": None,
                "week_high":  None,
                "week_low":   None,
            })

    return jsonify({"stocks": results, "list": list_name})


@app.route("/api/market-indices")
def market_indices():
    """Return live quotes for the 4 major indices."""
    indices = [
        {"symbol": "^NSEI",  "name": "NIFTY 50"},
        {"symbol": "^BSESN", "name": "SENSEX"},
        {"symbol": "^GSPC",  "name": "S&P 500"},
        {"symbol": "^IXIC",  "name": "NASDAQ"},
    ]
    results = []
    for idx in indices:
        try:
            raw  = yf.download(idx["symbol"], period="5d", interval="1d",
                               auto_adjust=False, progress=False)
            vals = raw["Close"].dropna()
            curr = float(vals.iloc[-1])
            prev = float(vals.iloc[-2]) if len(vals) >= 2 else curr
            chg  = ((curr - prev) / prev * 100) if prev else 0
            results.append({
                "name":       idx["name"],
                "symbol":     idx["symbol"],
                "price":      round(curr, 2),
                "change_pct": round(chg, 2),
            })
        except Exception:
            results.append({
                "name":       idx["name"],
                "symbol":     idx["symbol"],
                "price":      None,
                "change_pct": None,
            })
    return jsonify({"indices": results})


@app.route("/api/search")
def search_stocks():
    """Autocomplete: return up to 10 matching stocks from stocks.json."""
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify({"results": []})

    try:
        with open(_STOCKS_JSON, encoding="utf-8") as fh:
            stocks_db = json.load(fh)
        all_stocks: list[dict] = []
        seen: set[str] = set()
        for lst in stocks_db.values():
            for s in lst:
                if s["symbol"] not in seen:
                    seen.add(s["symbol"])
                    all_stocks.append(s)
        matches = [
            s for s in all_stocks
            if q in s["symbol"].lower() or q in s["name"].lower()
        ][:10]
        return jsonify({"results": matches})
    except Exception:
        return jsonify({"results": []})


if __name__ == "__main__":
    app.run(debug=True)

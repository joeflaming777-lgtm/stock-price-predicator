"""Stock data retrieval, feature engineering, modelling, and chart creation."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import yfinance as yf
from plotly.subplots import make_subplots
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parent
STOCK_DATA_PATH = PROJECT_ROOT / "stock_data.csv"

FEATURE_COLUMNS = [
    "Open",
    "High",
    "Low",
    "Volume",
    "Prev_Close",
    "MA_5",
    "MA_10",
    "MA_20",
    "MA_50",
    "MA_200",
    "Return_1D",
    "Volatility_5",
    "Daily_Range",
]


class StockPredictionError(Exception):
    """Raised when stock data cannot be fetched or modelled cleanly."""


def _clean_symbol(symbol: str) -> str:
    cleaned = (symbol or "").strip().upper()
    if not cleaned:
        raise StockPredictionError("Please enter a stock ticker symbol.")
    return cleaned


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_market_cap(value: Any) -> str:
    market_cap = _safe_float(value)
    if market_cap <= 0:
        return "Not available"
    units = [("T", 1_000_000_000_000), ("B", 1_000_000_000), ("M", 1_000_000)]
    for label, divisor in units:
        if market_cap >= divisor:
            return f"${market_cap / divisor:,.2f}{label}"
    return f"${market_cap:,.0f}"


def fetch_stock_data(symbol: str, period: str = "5y") -> tuple[pd.DataFrame, yf.Ticker]:
    """Download historical stock data from Yahoo Finance."""

    symbol = _clean_symbol(symbol)
    ticker = yf.Ticker(symbol)

    try:
        data = ticker.history(period=period, interval="1d", auto_adjust=False)
    except Exception as exc:  # yfinance can raise several provider/network exceptions
        raise StockPredictionError(
            "Unable to fetch stock data right now. Check your internet connection and ticker symbol."
        ) from exc

    if data.empty:
        raise StockPredictionError(f"No historical data was found for '{symbol}'.")

    data = data.reset_index()
    if "Date" not in data.columns:
        raise StockPredictionError("Yahoo Finance returned data in an unexpected format.")

    data["Date"] = pd.to_datetime(data["Date"]).dt.tz_localize(None)
    required_columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
    data = data[required_columns].dropna()

    if len(data) < 260:
        raise StockPredictionError(
            "At least one year of valid daily data is required to train the prediction models."
        )

    data.to_csv(STOCK_DATA_PATH, index=False)
    return data, ticker


def get_company_info(ticker: yf.Ticker, symbol: str) -> dict[str, Any]:
    """Return key company metadata with graceful fallbacks."""

    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    return {
        "symbol": symbol,
        "name": info.get("longName") or info.get("shortName") or symbol,
        "sector": info.get("sector") or "Not available",
        "industry": info.get("industry") or "Not available",
        "market_cap": _format_market_cap(info.get("marketCap")),
        "currency": info.get("currency") or "USD",
        "exchange": info.get("exchange") or "Not available",
    }


def fetch_stock_news(ticker: yf.Ticker, max_items: int = 10) -> list[dict[str, Any]]:
    """Fetch the latest news articles for a stock ticker via yfinance."""

    try:
        raw_news = ticker.news or []
    except Exception:
        return []

    articles: list[dict[str, Any]] = []
    now_ts = datetime.now(tz=timezone.utc).timestamp()

    for item in raw_news[:max_items]:
        try:
            content = item.get("content", {}) if isinstance(item, dict) else {}

            # Title
            title = (
                content.get("title")
                or item.get("title")
                or "Untitled"
            )

            # Publisher / provider
            provider = content.get("provider", {}) or {}
            publisher = (
                provider.get("displayName")
                or content.get("canonicalUrl", {}).get("site", "")
                or item.get("publisher")
                or "Unknown"
            )

            # URL
            canonical = content.get("canonicalUrl", {}) or {}
            url = (
                canonical.get("url")
                or item.get("link")
                or item.get("url")
                or "#"
            )

            # Thumbnail
            thumbnail = ""
            thumb_data = content.get("thumbnail", {}) or {}
            resolutions = thumb_data.get("resolutions", [])
            if resolutions:
                thumbnail = resolutions[0].get("url", "")

            # Summary / description
            summary = content.get("summary") or content.get("description") or ""
            if summary and len(summary) > 200:
                summary = summary[:200].rstrip() + "…"

            # Published time → human-readable relative string
            pub_ts_raw = content.get("pubDate") or item.get("providerPublishTime")
            pub_display = "Recently"
            if pub_ts_raw:
                try:
                    if isinstance(pub_ts_raw, str):
                        pub_dt = datetime.fromisoformat(pub_ts_raw.replace("Z", "+00:00"))
                        pub_ts = pub_dt.timestamp()
                    else:
                        pub_ts = float(pub_ts_raw)

                    diff = int(now_ts - pub_ts)
                    if diff < 3600:
                        pub_display = f"{diff // 60}m ago"
                    elif diff < 86400:
                        pub_display = f"{diff // 3600}h ago"
                    else:
                        pub_display = f"{diff // 86400}d ago"
                except Exception:
                    pub_display = "Recently"

            articles.append(
                {
                    "title": title,
                    "publisher": publisher,
                    "url": url,
                    "thumbnail": thumbnail,
                    "summary": summary,
                    "published": pub_display,
                }
            )
        except Exception:
            continue

    return articles


def add_price_features(data: pd.DataFrame, include_target: bool = True) -> pd.DataFrame:
    """Create model-ready features from OHLCV data."""

    frame = data.copy()
    frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize(None)
    frame = frame.sort_values("Date").reset_index(drop=True)

    numeric_columns = ["Open", "High", "Low", "Close", "Volume"]
    frame[numeric_columns] = frame[numeric_columns].apply(pd.to_numeric, errors="coerce")

    frame["Prev_Close"] = frame["Close"].shift(1)
    frame["MA_5"] = frame["Close"].rolling(window=5).mean()
    frame["MA_10"] = frame["Close"].rolling(window=10).mean()
    frame["MA_20"] = frame["Close"].rolling(window=20).mean()
    frame["MA_50"] = frame["Close"].rolling(window=50).mean()
    frame["MA_200"] = frame["Close"].rolling(window=200).mean()
    frame["Return_1D"] = frame["Close"].pct_change()
    frame["Volatility_5"] = frame["Return_1D"].rolling(window=5).std()
    frame["Daily_Range"] = (frame["High"] - frame["Low"]) / frame["Close"]

    if include_target:
        frame["Target"] = frame["Close"].shift(-1)

    return frame


def train_and_compare_models(data: pd.DataFrame) -> dict[str, Any]:
    """Train Linear Regression and Random Forest models, then select the best."""

    featured = add_price_features(data, include_target=True).dropna().reset_index(drop=True)
    if len(featured) < 120:
        raise StockPredictionError("Not enough complete historical rows remain after feature engineering.")

    split_index = int(len(featured) * 0.8)
    X = featured[FEATURE_COLUMNS]
    y = featured["Target"]
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

    models = {
        "Linear Regression": Pipeline(
            steps=[("scaler", StandardScaler()), ("model", LinearRegression())]
        ),
        "Random Forest Regressor": RandomForestRegressor(
            n_estimators=220,
            max_depth=12,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),
    }

    metrics: dict[str, dict[str, float]] = {}
    predictions: dict[str, np.ndarray] = {}

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        predictions[name] = y_pred
        metrics[name] = {
            "r2": _safe_float(r2_score(y_test, y_pred)),
            "mae": _safe_float(mean_absolute_error(y_test, y_pred)),
            "rmse": _safe_float(math.sqrt(mean_squared_error(y_test, y_pred))),
        }

    best_model_name = max(metrics, key=lambda model_name: metrics[model_name]["r2"])

    return {
        "featured": featured,
        "models": models,
        "metrics": metrics,
        "best_model_name": best_model_name,
        "best_model": models[best_model_name],
        "test_dates": featured["Date"].iloc[split_index:],
        "y_test": y_test,
        "best_predictions": predictions[best_model_name],
    }


def predict_future_prices(
    model: Any,
    historical_data: pd.DataFrame,
    days: int = 30,
) -> list[dict[str, Any]]:
    """Predict future closing prices through iterative daily forecasting."""

    simulated = historical_data.copy().sort_values("Date").reset_index(drop=True)
    predictions: list[dict[str, Any]] = []
    median_volume = _safe_float(simulated["Volume"].tail(30).median(), 1_000_000)
    avg_range_pct = max(_safe_float(((simulated["High"] - simulated["Low"]) / simulated["Close"]).tail(30).mean()), 0.005)

    for next_date in pd.bdate_range(simulated["Date"].iloc[-1] + pd.Timedelta(days=1), periods=days):
        feature_frame = add_price_features(simulated, include_target=False).dropna()
        latest_features = feature_frame[FEATURE_COLUMNS].iloc[[-1]]
        predicted_close = max(_safe_float(model.predict(latest_features)[0]), 0.01)
        previous_close = _safe_float(simulated["Close"].iloc[-1], predicted_close)

        projected_open = previous_close
        projected_high = max(projected_open, predicted_close) * (1 + avg_range_pct / 2)
        projected_low = min(projected_open, predicted_close) * (1 - avg_range_pct / 2)

        simulated = pd.concat(
            [
                simulated,
                pd.DataFrame(
                    [
                        {
                            "Date": next_date.to_pydatetime(),
                            "Open": projected_open,
                            "High": projected_high,
                            "Low": projected_low,
                            "Close": predicted_close,
                            "Volume": median_volume,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

        predictions.append(
            {
                "date": next_date.strftime("%Y-%m-%d"),
                "price": round(predicted_close, 2),
            }
        )

    return predictions


def classify_trend(current_price: float, predictions_30d: list[dict[str, Any]], data: pd.DataFrame) -> dict[str, Any]:
    """Classify the projected trend using forecast change and moving averages."""

    if not predictions_30d:
        return {"label": "Sideways Trend", "class": "sideways", "description": "Forecast is neutral."}

    projected_price = _safe_float(predictions_30d[-1]["price"], current_price)
    change_percent = ((projected_price - current_price) / current_price) * 100 if current_price else 0
    featured = add_price_features(data, include_target=False)
    latest = featured.dropna().iloc[-1]
    ma_50 = _safe_float(latest["MA_50"], current_price)
    ma_200 = _safe_float(latest["MA_200"], current_price)

    if change_percent >= 3 and ma_50 >= ma_200 * 0.98:
        label = "Bullish Trend"
        trend_class = "bullish"
        description = "The forecast points upward and short-term momentum is holding above the long-term average."
    elif change_percent <= -3 and ma_50 <= ma_200 * 1.02:
        label = "Bearish Trend"
        trend_class = "bearish"
        description = "The forecast points lower and price momentum is below the long-term average."
    else:
        label = "Sideways Trend"
        trend_class = "sideways"
        description = "The forecast is range-bound, with no strong directional signal."

    return {
        "label": label,
        "class": trend_class,
        "description": description,
        "change_percent": round(change_percent, 2),
    }


def create_historical_chart(data: pd.DataFrame, symbol: str) -> str:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.72, 0.28],
    )
    fig.add_trace(
        go.Candlestick(
            x=data["Date"],
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="OHLC",
            increasing_line_color="#16a34a",
            decreasing_line_color="#dc2626",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(x=data["Date"], y=data["Volume"], name="Volume", marker_color="#64748b"),
        row=2,
        col=1,
    )
    fig.update_layout(
        title=f"{symbol} Historical Price and Volume",
        template="plotly_white",
        height=520,
        margin=dict(l=30, r=20, t=55, b=30),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.04, x=0),
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    return pio.to_json(fig, validate=False)


def create_actual_vs_predicted_chart(test_dates: pd.Series, actual: pd.Series, predicted: np.ndarray) -> str:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=test_dates, y=actual, mode="lines", name="Actual Close", line=dict(color="#0f766e", width=2)))
    fig.add_trace(go.Scatter(x=test_dates, y=predicted, mode="lines", name="Predicted Close", line=dict(color="#f59e0b", width=2)))
    fig.update_layout(
        title="Actual vs Predicted Closing Price",
        template="plotly_white",
        height=430,
        margin=dict(l=30, r=20, t=55, b=35),
        legend=dict(orientation="h", y=1.08, x=0),
    )
    fig.update_yaxes(title_text="Close Price")
    return pio.to_json(fig, validate=False)


def create_moving_average_chart(data: pd.DataFrame, symbol: str) -> str:
    featured = add_price_features(data, include_target=False)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=featured["Date"], y=featured["Close"], mode="lines", name="Close", line=dict(color="#2563eb", width=1.8)))
    fig.add_trace(go.Scatter(x=featured["Date"], y=featured["MA_50"], mode="lines", name="50-Day MA", line=dict(color="#16a34a", width=2)))
    fig.add_trace(go.Scatter(x=featured["Date"], y=featured["MA_200"], mode="lines", name="200-Day MA", line=dict(color="#dc2626", width=2)))
    fig.update_layout(
        title=f"{symbol} Moving Averages",
        template="plotly_white",
        height=430,
        margin=dict(l=30, r=20, t=55, b=35),
        legend=dict(orientation="h", y=1.08, x=0),
    )
    fig.update_yaxes(title_text="Price")
    return pio.to_json(fig, validate=False)


def create_future_chart(current_price: float, predictions_30d: list[dict[str, Any]]) -> str:
    dates = [item["date"] for item in predictions_30d]
    prices = [item["price"] for item in predictions_30d]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=prices, mode="lines+markers", name="Forecast", line=dict(color="#7c3aed", width=2)))
    fig.add_hline(y=current_price, line_dash="dot", line_color="#475569", annotation_text="Current Close")
    fig.update_layout(
        title="30-Day Forecast Trend",
        template="plotly_white",
        height=430,
        margin=dict(l=30, r=20, t=55, b=35),
        showlegend=False,
    )
    fig.update_yaxes(title_text="Predicted Close")
    return pio.to_json(fig, validate=False)


def latest_price_table(data: pd.DataFrame, rows: int = 10) -> list[dict[str, Any]]:
    table = data.tail(rows).copy()
    table["Date"] = table["Date"].dt.strftime("%Y-%m-%d")
    for column in ["Open", "High", "Low", "Close"]:
        table[column] = table[column].map(lambda value: round(_safe_float(value), 2))
    table["Volume"] = table["Volume"].map(lambda value: f"{int(_safe_float(value)):,}")
    return table[["Date", "Open", "High", "Low", "Close", "Volume"]].to_dict(orient="records")


def analyze_stock(symbol: str) -> dict[str, Any]:
    """Run the full stock analysis and prediction pipeline."""

    symbol = _clean_symbol(symbol)
    data, ticker = fetch_stock_data(symbol)
    model_output = train_and_compare_models(data)
    current_price = _safe_float(data["Close"].iloc[-1])
    previous_price = _safe_float(data["Close"].iloc[-2], current_price)
    price_change = current_price - previous_price
    price_change_percent = (price_change / previous_price) * 100 if previous_price else 0

    predictions_30d = predict_future_prices(model_output["best_model"], data, days=30)
    predictions_7d = predictions_30d[:7]
    next_day_price = predictions_30d[0]["price"]
    trend = classify_trend(current_price, predictions_30d, data)
    news = fetch_stock_news(ticker)

    metrics = {
        name: {
            "r2": round(values["r2"], 4),
            "mae": round(values["mae"], 2),
            "rmse": round(values["rmse"], 2),
        }
        for name, values in model_output["metrics"].items()
    }

    return {
        "symbol": symbol,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "company": get_company_info(ticker, symbol),
        "current_price": round(current_price, 2),
        "price_change": round(price_change, 2),
        "price_change_percent": round(price_change_percent, 2),
        "row_count": len(data),
        "date_start": data["Date"].min().strftime("%Y-%m-%d"),
        "date_end": data["Date"].max().strftime("%Y-%m-%d"),
        "metrics": metrics,
        "best_model_name": model_output["best_model_name"],
        "next_day_price": next_day_price,
        "predictions_7d": predictions_7d,
        "predictions_30d": predictions_30d,
        "trend": trend,
        "latest_rows": latest_price_table(data),
        "news": news,
        "charts": {
            "historical": create_historical_chart(data, symbol),
            "actual_predicted": create_actual_vs_predicted_chart(
                model_output["test_dates"],
                model_output["y_test"],
                model_output["best_predictions"],
            ),
            "moving_average": create_moving_average_chart(data, symbol),
            "future": create_future_chart(current_price, predictions_30d),
        },
    }

# Stock Price Predictor

A complete internship-level Flask web application that predicts stock prices using historical Yahoo Finance data, supervised machine learning, and interactive Plotly dashboards.

## Features

- Search any Yahoo Finance ticker symbol, including examples like `AAPL`, `TSLA`, `MSFT`, `INFY.NS`, and `TCS.NS`
- Download at least five years of daily historical OHLCV stock data with `yfinance`
- Display open, high, low, close, and volume data
- Train and compare:
  - Linear Regression
  - Random Forest Regressor
- Select the best model using R² Score
- Show model evaluation metrics:
  - R² Score
  - Mean Absolute Error
  - Root Mean Squared Error
- Predict:
  - Next-day closing price
  - 7-day future price trend
  - 30-day future price trend
- Display company information:
  - Company name
  - Sector
  - Industry
  - Market cap
- Identify bullish, bearish, or sideways trend signals
- Render interactive Plotly charts:
  - Historical candlestick and volume chart
  - Actual vs predicted closing price chart
  - 50-day and 200-day moving average chart
  - 30-day forecast chart

## Tech Stack

- Python
- Flask
- HTML5
- CSS3
- Bootstrap 5
- JavaScript
- Pandas
- NumPy
- Scikit-Learn
- yfinance
- Plotly

## Folder Structure

```text
Stock-Price-Predictor/
|
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── dashboard.js
│   └── images/
|
├── templates/
│   ├── index.html
│   └── about.html
|
├── models/
├── app.py
├── predictor.py
├── requirements.txt
├── README.md
└── stock_data.csv
```

## Installation

Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python app.py
```

Open the local Flask URL shown in the terminal, usually:

```text
http://127.0.0.1:5000
```

## How It Works

1. The user enters a stock ticker symbol.
2. `yfinance` downloads five years of daily historical stock data from Yahoo Finance.
3. The application engineers features such as previous close, moving averages, daily return, volatility, price range, and volume.
4. Linear Regression and Random Forest Regressor models are trained using a time-ordered train/test split.
5. The model with the highest R² Score is selected.
6. The selected model predicts next-day, 7-day, and 30-day closing-price trends.
7. Plotly charts and Bootstrap dashboard cards present the results.

## Machine Learning Details

The target variable is the next trading day's closing price. The project uses a time-based holdout split instead of random shuffling because stock data is chronological. This keeps the testing process closer to a real forecasting task.

Feature columns include:

- Open
- High
- Low
- Volume
- Previous close
- 5-day, 10-day, 20-day, 50-day, and 200-day moving averages
- 1-day return
- 5-day volatility
- Daily price range

## Notes

This project is intended for academic and internship demonstration purposes. Stock market prediction is uncertain, and the output should not be treated as financial advice.

# 📈 TradeMind: Stock Price Predictor & AI Trading Assistant

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-lightgrey?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.4%2B-orange?logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![Plotly](https://img.shields.io/badge/Plotly-5.22%2B-blueviolet?logo=plotly&logoColor=white)](https://plotly.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

An intelligent, interactive stock forecasting dashboard powered by **Supervised Machine Learning** (Scikit-Learn) and integrated with **TradeMind AI**—a context-aware trading assistant capable of running live technical analysis queries directly on Yahoo Finance data.

---

## 🌟 Core Visuals

### 1. Dynamic Currency Dashboard (Indian Rupee Support)
The dashboard dynamically formats pricing and predictions based on the stock's listing exchange currency (e.g., `₹` for NSE and `$` for NASDAQ/NYSE).

![TCS.NS Dashboard in INR](task%201/Stock-Price-Predictor/static/images/dashboard_inr.png)

---

### 2. TradeMind AI Chatbot (Live Yahoo Finance & Technical Indicators)
The floating AI chatbot automatically scans user messages for stock tickers, fetches historical data, calculates indicators on-the-fly (**RSI, MACD, Moving Averages**), and returns expert analytical feedback.

![TradeMind AI Chatbot Analysis](task%201/Stock-Price-Predictor/static/images/chatbot_analysis.png)

---

## ✨ Features

### 📊 Multi-Model ML Forecasting
- Train and compare **Linear Regression** and **Random Forest Regressor** pipelines using time-ordered holdout splits.
- Automated selection of the best-performing model based on **R² Score**.
- Metrics display for validation: **R² Score, Mean Absolute Error (MAE), and Root Mean Squared Error (RMSE)**.
- Full prediction output: **Next-day price**, **7-day trend**, and **30-day forecast**.

### 💬 Smart Trading Assistant (TradeMind AI)
- Powered by **Llama-3.3-70b-versatile** via Groq API.
- **Selective Context matching**: Chatbot remains conversational for generic greetings like *"hi"* or *"hello"*, but triggers full technical analysis if you ask about the current stock (e.g., *"Should I buy?"*) or a specific ticker (e.g., *"What is the RSI of Reliance?"*).
- Custom yfinance parser calculates **14-period RSI**, **MACD crossovers**, and **50/200-day SMAs** to verify Golden/Death crosses dynamically.

### 📈 Interactive Plotly Visualizations
- **Historical Candlestick & Volume** charts.
- **Actual vs. Predicted** comparison line chart to gauge model fit.
- **50-Day & 200-Day Moving Average** trendlines.
- **30-Day Future Forecast** trendline.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, Flask, python-dotenv
- **Frontend**: HTML5, CSS3 (Vanilla), Bootstrap 5, Javascript (ES6)
- **Data & Math**: Pandas, NumPy
- **Machine Learning**: Scikit-Learn (StandardScaler, RandomForestRegressor, LinearRegression)
- **APIs**: yfinance (Yahoo Finance), Groq SDK (Llama 3.3 model)
- **Charts**: Plotly.js (v2.35)

---

## 📂 Folder Structure

```text
Stock-Price-Predictor/
├── static/
│   ├── css/
│   │   └── style.css            # Custom dashboard layout & styling
│   ├── data/
│   │   └── stocks.json          # Predefined Nifty 50 and US 30 stock watchlists
│   ├── images/
│   │   ├── dashboard_inr.png
│   │   └── chatbot_analysis.png
│   └── js/
│       ├── chatbot.js           # Floating chatbot client-side logic
│       ├── dashboard.js         # Plotly rendering and theme switching
│       └── screener.js          # Batch-fetch stock screener data
├── templates/
│   ├── about.html               # About/Project information page
│   ├── index.html               # Core dashboard interface
│   └── screener.html            # Nifty50/US30 market screener
├── models/                      # Saved ML model binaries (if persisted)
├── app.py                       # Flask application router & API endpoints
├── predictor.py                 # Feature engineering & ML training pipeline
├── requirements.txt             # Python dependency list
├── stock_data.csv               # Cache of recently downloaded stock history
└── README.md                    # Project documentation
```

---

## 🚀 Installation & Local Setup

### 1. Clone the Project & Navigate
```powershell
cd "task 1/Stock-Price-Predictor"
```

### 2. Set Up Virtual Environment
**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```
**macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the `Stock-Price-Predictor` root directory and add your **Groq API Key**:
```env
GROQ_API_KEY=your_actual_groq_api_key_here
```

### 5. Launch the Server
```powershell
python app.py
```
Open **http://127.0.0.1:5000** in your browser to view the application.

---

## 🧠 Under the Hood: Machine Learning Pipeline

### 1. Feature Engineering
The model transforms basic OHLCV (Open, High, Low, Close, Volume) data into high-value trading features:
- **Lag Features**: Previous Day Close
- **Moving Averages**: 5, 10, 20, 50, and 200-day Simple Moving Averages (SMAs)
- **Volatility & Momentum**: 1-Day Return, 5-Day Volatility (rolling standard deviation)
- **Range Metrics**: Daily Price Spread (`(High - Low) / Close`)

### 2. Time-Series Split
Unlike traditional random train/test splits which leak future information, TradeMind uses a **time-based sequential split** (first 80% of rows for training, last 20% for testing). This ensures models learn to forecast *forward* in time.

### 3. Model Training & Evaluation
We train two separate pipelines:
- **Linear Regression**: Ideal for linear trends.
- **Random Forest Regressor**: Highly effective at capturing complex, non-linear market regimes.
R² Score is computed on test predictions, and the best model is selected automatically to generate predictions.

---

## ⚠️ Disclaimer
All information is strictly for educational purposes. This application does not constitute financial advice. Past stock market performance does not guarantee future results.

---

## 📜 License
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.


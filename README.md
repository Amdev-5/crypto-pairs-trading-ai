# 🚀 AI-Powered Cryptocurrency Pairs Trading System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Bybit](https://img.shields.io/badge/Exchange-Bybit-orange.svg)](https://www.bybit.com)
[![AI](https://img.shields.io/badge/AI-Gemini%202.5-green.svg)](https://deepmind.google/technologies/gemini/)
[![Trading Strategy](https://img.shields.io/badge/Strategy-Statistical%20Arbitrage-red.svg)](https://en.wikipedia.org/wiki/Statistical_arbitrage)

> **A production-grade, research-backed algorithmic trading system combining statistical arbitrage, AI-powered decision making, and institutional-grade risk management for cryptocurrency futures markets.**

---

## ⚠️ DISCLAIMER: Educational Research Project Only

**NOT FINANCIAL ADVICE** • This is a technical demonstration for learning purposes. Cryptocurrency trading is high-risk. Authors assume NO liability for losses. Consult licensed professionals before any real trading.

---

## 🎯 Key Features

- **🧠 Multi-Agent AI**: Google Gemini 2.5 orchestrating quant, sentiment, and risk analysis
- **📊 4 Concurrent Strategies**: Cointegration, OBI, Correlation+RSI, Mean Reversion
- **⚡ High Performance**: Sub-100ms latency via WebSocket streaming
- **🛡️ Risk Management**: Dynamic sizing, trailing stops, drawdown limits
- **📈 Research-Backed**: 2024-2025 academic papers from Financial Innovation
- **📊 Live Dashboard**: Real-time P&L, positions, and performance metrics

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR AGENT                              │
│           Multi-Strategy Coordination & Decision Engine              │
│        (Consensus-based execution with override controls)            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼────────────────────────┐
          ↓                       ↓                        ↓
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│   QUANT AGENT     │   │  SENTIMENT AGENT  │   │    RISK AGENT     │
│                   │   │   (Gemini 2.5)    │   │                   │
│ • Cointegration   │   │ • News Analysis   │   │ • Position Sizing │
│ • Z-Score         │   │ • Event Detection │   │ • Stop-Loss       │
│ • Hedge Ratios    │   │ • Market Regime   │   │ • Drawdown Limit  │
│ • OBI Signals     │   │ • Google Search   │   │ • Exposure Mgmt   │
│ • RSI/Correlation │   │   Grounding       │   │ • Risk Metrics    │
└───────────────────┘   └───────────────────┘   └───────────────────┘
          │                       │                        │
          └───────────────────────┴────────────────────────┘
                                  ↓
          ┌─────────────────────────────────────────────────────┐
          │           EXECUTION & DATA LAYER                    │
          │  • Smart Order Router (Limit → Market Fallback)     │
          │  • WebSocket Streaming (Trade & Orderbook)          │
          │  • PostgreSQL + TimescaleDB (Time-Series Storage)   │
          │  • Redis Cache (Low-latency Access)                 │
          └─────────────────────────────────────────────────────┘
                                  ↓
                         Bybit Futures API
                    (Linear Perpetual Contracts)
```

---

## 💡 Trading Strategies

**Engle-Granger Cointegration** • Statistical arbitrage on BTC/ETH pairs via OLS regression hedge ratios

**Order Book Imbalance (OBI)** • Real-time bid/ask pressure analysis for momentum capture

**Correlation + RSI** • RSI divergence detection on correlated pairs with multi-timeframe confirmation

**Mean Reversion** • Z-score entry (±2σ) with Bollinger Bands and adaptive volatility thresholds

---

## 🛠️ Technical Stack

**Statistics** • Engle-Granger, ADF tests, OLS/Kalman filtering, Kelly Criterion, Z-score normalization

**AI** • Google Gemini 2.5 (sentiment + news), Multi-agent consensus, Google Search grounding

**Infrastructure** • WebSocket → Redis → PostgreSQL/TimescaleDB, Smart order routing, FastAPI dashboard

**Performance** • Real-time Sharpe ratio, win rate, drawdown tracking, <100ms execution latency

---

## 📊 Trading Pairs

10 research-backed pairs across BTC/ETH majors, L1 ecosystems, DeFi, and Layer 2s:
- **BTC/ETH** (R² > 0.95) • **BTC/LTC** • **ETH/SOL** • **LTC/DOGE** • **DOT/ATOM** • [6 more](config.yaml)

Source: [Financial Innovation 2025](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-024-00702-7)

---

## 🚀 Quick Start

**Prerequisites**: Python 3.11+, PostgreSQL/TimescaleDB, Redis, Bybit API

```bash
# Setup
git clone https://github.com/Amdev-5/crypto-pairs-trading-ai.git
cd crypto-pairs-trading-ai
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env  # Add your Bybit API keys
nano config.yaml      # Customize pairs, thresholds, risk limits

# Run (Testnet)
python -m src.main                    # Trading engine
python -m src.dashboard.app           # Dashboard → localhost:3000
```

⚠️ **Live Trading**: Set `BYBIT_TESTNET=False` in `.env` (high risk, start small)

---

## 📈 Performance & Risk

**Targets**: Sharpe >1.5 | Win Rate >55% | Drawdown <20% | Latency <100ms

**Risk Controls**: Position stop-loss (-3%) • Daily loss limit • Max 10 concurrent positions • Dynamic sizing • Trailing stops

---

## 🗂️ Project Structure

```
.
├── src/
│   ├── agents/                 # Multi-agent system
│   │   ├── orchestrator.py     # Central coordinator
│   │   ├── quant_agent.py      # Statistical analysis
│   │   ├── sentiment_agent.py  # Gemini AI + news
│   │   └── risk_agent.py       # Risk management
│   ├── data/
│   │   ├── bybit_client.py     # WebSocket + REST API
│   │   ├── database.py         # PostgreSQL/TimescaleDB
│   │   └── models.py           # Data models
│   ├── strategy/
│   │   ├── cointegration.py    # Statistical tests
│   │   ├── zscore.py           # Z-score calculation
│   │   ├── signals.py          # Signal generation
│   │   └── strategies/         # Individual strategy implementations
│   ├── execution/
│   │   ├── order_manager.py    # Smart order routing
│   │   └── position_manager.py # Position tracking
│   ├── monitoring/
│   │   └── performance_tracker.py  # Real-time metrics
│   ├── backtesting/
│   │   └── backtest_engine.py  # Historical simulation
│   ├── dashboard/
│   │   ├── app.py              # FastAPI server
│   │   └── templates/          # Dashboard UI
│   └── main.py                 # Entry point
├── tests/                      # Unit & integration tests
├── logs/                       # Trading logs
├── config.yaml                # Trading configuration
├── requirements.txt           # Python dependencies
└── .env.example              # Environment template
```

---

## 🧪 Testing

```bash
# Backtesting
python -m src.backtesting.backtest_engine --start-date 2024-01-01 --end-date 2024-11-26

# Paper Trading (Testnet - Free $10K-$100K)
BYBIT_TESTNET=True python -m src.main

# Unit Tests
pytest tests/ -v --cov=src
```

---

## 🔐 Security

- Never commit API keys (use `.env`)
- Use testnet for development
- Start live trading with minimal sizes
- Enable stop-loss and loss limits
- Bybit API: `Order` + `Position` only (never `Withdrawal`)

---

## ⚠️ Risks

High volatility, leverage amplification, cointegration breakdown, system failures, regulatory changes. **Educational use only. Trade at your own risk with capital you can afford to lose.**

---

## 📚 Research

Based on peer-reviewed papers:
- [Copula-based cryptocurrency pairs trading](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-024-00702-7) (Financial Innovation 2025)
- [Dynamic Cointegration Pairs Trading](https://arxiv.org/pdf/2109.10662) (arXiv 2024)
- [HF cryptocurrency relationships](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-021-00290-w) (Financial Innovation 2021)

---

## 🤝 Contributing

PRs welcome! Add tests, ensure `pytest` passes. Ideas: Johansen testing, ML regime detection, multi-exchange support, mobile dashboard.

---

## 📊 Monitoring

**Dashboard** (localhost:3000): Live P&L, strategy breakdown, z-score charts, execution timeline

**Logging**: JSON logs (`logs/trading.log`) with agent decisions and order details

**Alerts**: Telegram/Email/Discord (optional)

---

## 🎯 Roadmap

✅ Multi-agent AI, 4 strategies, smart routing, dashboard, risk management, testnet

🚧 ML strategy selection, enhanced backtesting, portfolio optimization

🔮 Multi-exchange, options trading, social sentiment, RL strategy discovery

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

**Use at your own risk. This software is provided "AS IS" without warranty of any kind.**

---

## 📞 Support

Issues: [GitHub Issues](https://github.com/Amdev-5/crypto-pairs-trading-ai/issues) • Docs: `ARCHITECTURE.md`

Built with: Bybit API • Google Gemini • statsmodels • pandas • PostgreSQL/TimescaleDB

---

**⭐ Star this repo if you found it valuable!**

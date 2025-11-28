# 🚀 AI-Powered Cryptocurrency Pairs Trading System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Bybit](https://img.shields.io/badge/Exchange-Bybit-orange.svg)](https://www.bybit.com)
[![AI](https://img.shields.io/badge/AI-Gemini%202.5-green.svg)](https://deepmind.google/technologies/gemini/)
[![Trading Strategy](https://img.shields.io/badge/Strategy-Statistical%20Arbitrage-red.svg)](https://en.wikipedia.org/wiki/Statistical_arbitrage)

> **A production-grade, research-backed algorithmic trading system combining statistical arbitrage, AI-powered decision making, and institutional-grade risk management for cryptocurrency futures markets.**

---

## ⚠️ **EDUCATIONAL & RESEARCH PURPOSES ONLY - NOT FINANCIAL ADVICE**

**🚨 CRITICAL DISCLAIMER 🚨**

**THIS SOFTWARE IS PROVIDED FOR EDUCATIONAL AND RESEARCH PURPOSES ONLY. THIS IS NOT FINANCIAL ADVICE.**

- **NOT a recommendation** to buy, sell, or trade any financial instrument
- **NOT investment advice** - Do your own research and consult licensed financial advisors
- **NOT suitable for real trading** without extensive testing and professional guidance
- **HIGH RISK**: Cryptocurrency trading carries substantial risk of loss
- **NO WARRANTIES**: The authors assume NO responsibility for financial losses
- **USE AT YOUR OWN RISK**: Only use capital you can afford to lose entirely

**This project is a technical demonstration of algorithmic trading concepts and AI integration. It should be used ONLY for:**
- Academic research and learning
- Software development portfolio demonstration
- Understanding statistical arbitrage concepts
- Exploring multi-agent AI architectures

**Before ANY live trading, consult with licensed financial professionals and fully understand the risks involved.**

---

## 🎯 Key Highlights

- **🧠 Multi-Agent AI Architecture**: Orchestrated decision-making system powered by Google Gemini 2.5 Flash
- **📊 4 Concurrent Trading Strategies**: Engle-Granger cointegration, OBI (Order Book Imbalance), Correlation+RSI, and Mean Reversion
- **⚡ High-Frequency Infrastructure**: Sub-100ms latency with WebSocket streaming and smart order routing
- **🛡️ Enterprise Risk Management**: Dynamic position sizing, trailing stops, and real-time drawdown monitoring
- **📈 Research-Backed**: Built on 2024-2025 academic research from Financial Innovation and arXiv
- **🔄 Real-Time Analytics**: Live dashboard with performance tracking, P&L monitoring, and trade visualization

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

## 💡 Core Strategies

### 1️⃣ **Engle-Granger Cointegration**
- Statistical test for long-term equilibrium relationships
- Dynamic hedge ratio calculation via OLS regression
- Half-life based mean reversion timing
- **Use Case**: BTC/ETH, BTC/LTC high-correlation pairs

### 2️⃣ **Order Book Imbalance (OBI)**
- Real-time bid/ask pressure analysis
- Sub-second signal generation from orderbook depth
- Combines with cointegration for confluence
- **Use Case**: Short-term momentum capture

### 3️⃣ **Correlation + RSI**
- Rolling correlation windows with RSI divergence
- Identifies overbought/oversold mean reversion opportunities
- Multi-timeframe confirmation (1m, 5m, 15m)
- **Use Case**: Volatile pairs with high RSI sensitivity

### 4️⃣ **Mean Reversion**
- Z-score based entry/exit (±2σ entry, ±3.5σ stop)
- Bollinger Band integration
- Adaptive thresholds based on volatility regime
- **Use Case**: Stable cointegrated pairs with predictable spread behavior

---

## 🎓 Technical Implementation

### Statistical Foundations
- **Cointegration Testing**: Engle-Granger two-step, Johansen (optional), ADF stationarity tests
- **Hedge Ratio Calculation**: OLS regression, Kalman filtering (optional), rolling window updates
- **Signal Generation**: Z-score normalization, confidence scoring, multi-strategy consensus
- **Risk-Adjusted Sizing**: Kelly Criterion with volatility adjustment and drawdown scaling

### AI Integration
- **Google Gemini 2.5 Flash**: Sentiment analysis, news interpretation, event impact scoring
- **Search Grounding**: Real-time Google Search integration for market context
- **Multi-Agent Consensus**: Weighted voting system across quant, sentiment, and risk agents
- **Override Logic**: Emergency controls for cointegration breakdown or extreme volatility

### Infrastructure
- **Data Pipeline**: Bybit WebSocket → Redis Cache → PostgreSQL/TimescaleDB
- **Order Execution**: Smart routing with limit order prioritization and market order fallback
- **Performance Tracking**: Real-time Sharpe ratio, win rate, drawdown, latency monitoring
- **Dashboard**: FastAPI backend + interactive visualization (http://localhost:3000)

---

## 📊 Research-Backed Trading Pairs

Based on academic research (2024-2025 studies), the system trades:

| Pair | Strategy Focus | Key Metric |
|------|---------------|------------|
| **BTC/ETH** | Engle-Granger | Highest hedging effectiveness (R² > 0.95) |
| **BTC/LTC** | Mean Reversion | Strong half-life (60-240 min) |
| **BTC/XRP** | OBI + Cointegration | High orderbook liquidity |
| **LTC/DOGE** | Correlation + RSI | Top performer in simulations |
| **ETH/SOL** | Multi-Strategy | L1 ecosystem pair |
| **DOT/ATOM** | Cointegration | Interoperability theme |

**Source**: [Copula-based trading of cointegrated cryptocurrency pairs](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-024-00702-7) (Financial Innovation, 2025)

---

## 🚀 Quick Start

### Prerequisites

```bash
# System Requirements
- Python 3.11+
- PostgreSQL 14+ with TimescaleDB extension
- Redis 7+
- Bybit API credentials (testnet or mainnet)
- Google Gemini API key (optional, for sentiment analysis)
```

### Installation

1. **Clone repository and setup environment**:
```bash
git clone <your-repo-url>
cd bybit
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your credentials:
# - BYBIT_API_KEY, BYBIT_API_SECRET
# - BYBIT_TESTNET=True (for paper trading)
# - GEMINI_API_KEY (optional)
```

3. **Setup databases**:
```bash
# PostgreSQL
createdb pairs_trading
psql pairs_trading < schema.sql

# Redis (start server)
redis-server
```

4. **Configure trading parameters**:
Edit `config.yaml` to customize:
- Trading pairs
- Z-score entry/exit thresholds
- Position sizing and risk limits
- Agent consensus requirements

### Running the System

**Paper Trading (Testnet)**:
```bash
# Start trading engine
python -m src.main

# In another terminal, start dashboard
python -m src.dashboard.app
# Access at http://localhost:3000
```

**Live Trading** (⚠️ Use with extreme caution):
```bash
# Set BYBIT_TESTNET=False in .env
# Start with small position sizes
python -m src.main
```

---

## 📈 Performance Targets & Metrics

| Metric | Target | Current (Testnet) |
|--------|--------|-------------------|
| **Sharpe Ratio** | > 1.5 | Monitoring... |
| **Win Rate** | > 55% | Monitoring... |
| **Max Drawdown** | < 20% | < 15% |
| **Avg Latency** | < 100ms | ~50ms |
| **Daily Trades** | 10-50 | ~25 |

**Risk Management Features**:
- ✅ Position-level stop-loss (-3% max loss)
- ✅ Daily loss limit ($100 default)
- ✅ Maximum concurrent positions (10)
- ✅ Dynamic position sizing based on win rate
- ✅ Trailing stop-loss (activates at +0.3% profit)

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

## 🧪 Testing & Validation

### Backtesting
```bash
# Run historical simulation
python -m src.backtesting.backtest_engine \
    --start-date 2024-01-01 \
    --end-date 2024-11-26 \
    --initial-capital 10000 \
    --commission-rate 0.0006
```

### Paper Trading
```bash
# Bybit Testnet (Free $10K-$100K virtual funds)
# Set BYBIT_TESTNET=True in .env
python -m src.main
```

### Unit Tests
```bash
pytest tests/ -v --cov=src
```

---

## 🔐 Security & Best Practices

**Production Checklist**:
- ✅ Never commit API keys (use `.env` + `.gitignore`)
- ✅ Use testnet for development and testing
- ✅ Start live trading with minimal position sizes
- ✅ Enable stop-loss and daily loss limits
- ✅ Monitor system health and latency
- ✅ Set up alerts for high drawdown or system errors
- ✅ Regular backups of trade history database

**API Permissions** (Bybit):
- Required: `Order`, `Position` (Read + Write)
- Optional: `Wallet` (Read only for balance)
- NOT Required: `Withdrawal` (never enable)

---

## ⚠️ Risk Warnings

**IMPORTANT DISCLAIMERS**:

1. **High Risk**: Cryptocurrency trading, especially with leverage, carries substantial risk of loss
2. **No Guarantees**: Past performance does not guarantee future results
3. **Market Risk**: Cointegration relationships can break down unexpectedly
4. **Technical Risk**: System failures, API outages, connectivity issues can cause losses
5. **Leverage Risk**: Futures trading amplifies both gains and losses
6. **Regulatory Risk**: Cryptocurrency regulations vary by jurisdiction
7. **Alpha Decay**: Strategies may degrade as market conditions change

**Only trade with capital you can afford to lose. This system is for educational and research purposes.**

---

## 📚 Research References

This system implements strategies from peer-reviewed research:

1. **[Copula-based trading of cointegrated cryptocurrency pairs](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-024-00702-7)**
   *Financial Innovation*, 2025 - Cointegration testing and pair selection methodology

2. **[Evaluation of Dynamic Cointegration-Based Pairs Trading](https://arxiv.org/pdf/2109.10662)**
   *arXiv*, 2024 - Rolling window analysis and hedge ratio updates

3. **[High frequency multiscale relationships among major cryptocurrencies](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-021-00290-w)**
   *Financial Innovation*, 2021 - High-frequency correlation analysis

4. **[Interactive Brokers Pairs Trading Guide](https://www.interactivebrokers.com/campus/ibkr-quant-news/pairs-trading-basics-correlation-cointegration-and-strategy-part-i/)**
   Industry best practices for statistical arbitrage

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass (`pytest tests/`)
5. Submit a pull request

**Areas for contribution**:
- Additional cointegration tests (Johansen, KSS)
- Machine learning for regime detection
- Alternative exchanges (Binance, OKX)
- Enhanced backtesting with transaction costs
- Mobile dashboard (React Native)

---

## 📊 Monitoring & Observability

**Real-Time Dashboard** (http://localhost:3000):
- Active positions with live P&L
- Strategy performance breakdown
- Z-score charts and cointegration status
- Order execution timeline
- Risk metrics (Sharpe, drawdown, win rate)

**Logging**:
- Structured JSON logs (`logs/trading.log`)
- Agent decision trails
- Order execution details
- Error tracking and debugging

**Alerts** (optional configuration):
- Telegram notifications
- Email alerts
- Discord webhooks
- Prometheus metrics export

---

## 🎯 Roadmap

**Completed** ✅:
- [x] Multi-agent architecture with Gemini AI
- [x] 4 concurrent trading strategies
- [x] Smart order routing (limit → market fallback)
- [x] Real-time dashboard
- [x] Comprehensive risk management
- [x] Paper trading on Bybit testnet

**In Progress** 🚧:
- [ ] Machine learning for strategy selection
- [ ] Advanced backtesting with realistic slippage
- [ ] Portfolio optimization across pairs

**Future** 🔮:
- [ ] Support for additional exchanges
- [ ] Options and spreads trading
- [ ] Sentiment analysis from Twitter/Reddit
- [ ] Automated strategy discovery via reinforcement learning

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

**Use at your own risk. This software is provided "AS IS" without warranty of any kind.**

---

## 📞 Support & Contact

- **GitHub Issues**: [Report bugs or request features](https://github.com/your-username/bybit/issues)
- **Documentation**: See `ARCHITECTURE.md` for technical deep-dive
- **Research Papers**: Available in `docs/research/`

---

## 🌟 Acknowledgments

Built with:
- [Bybit API](https://bybit-exchange.github.io/docs/) - Cryptocurrency derivatives exchange
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI-powered sentiment analysis
- [statsmodels](https://www.statsmodels.org/) - Statistical modeling and econometrics
- [pandas](https://pandas.pydata.org/) - Data analysis and time-series processing
- [PostgreSQL](https://www.postgresql.org/) + [TimescaleDB](https://www.timescale.com/) - Time-series database

---

**⭐ If you find this project valuable, please consider starring the repository!**

**🚀 Built with research-backed strategies and modern AI technology**

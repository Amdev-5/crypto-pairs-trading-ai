# Crypto Pairs Trading System - Architecture & Research

## Research Summary

### Key Academic Findings (2024-2025)

1. **Copula-based Trading of Cointegrated Cryptocurrency Pairs** (Financial Innovation, 2025)
   - Framework for twenty Binance USDT-margined futures coins
   - Sets BTCUSDT as reference asset
   - Uses EG two-step method and KSS cointegration test
   - Outperforms traditional cointegration-only or copula-only strategies

2. **Dynamic Cointegration-Based Pairs Trading** (arXiv 2024)
   - Emphasizes dynamic hedge ratios
   - Uses rolling window approach for cointegration testing
   - Z-score thresholds: Entry at ±2.0, Exit at ±0.5 (typical)
   - Risk management: Stop-loss at ±3.0

3. **High-Frequency Trading Insights**
   - BTC-ETH portfolio offers highest hedging effectiveness
   - 15-minute intervals optimal for intraday pairs trading
   - Triangular arbitrage opportunities exist but require <100ms latency

### Optimal Trading Pairs (Research-Backed)
1. **BTC/ETH** - Highest hedging effectiveness, strong cointegration
2. **BTC/LTC** - Mean-reverting relationship confirmed
3. **BTC/XRP** - Moderate cointegration, higher volatility
4. **BTC/BCH** - Bitcoin fork, natural correlation
5. **LTC/DOGE** - Top-performing pair in simulation studies

---

## System Architecture

### 1. **Data Layer** (Low Latency)
```
┌─────────────────────────────────────┐
│   Bybit WebSocket Streams           │
│   - wss://stream.bybit.com/v5       │
│   - Linear perpetual futures        │
│   - <50ms latency (AWS Singapore)   │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│   Real-Time Data Buffer             │
│   - Redis/TimescaleDB               │
│   - 1-minute OHLCV aggregation      │
│   - Tick-level data storage         │
└─────────────────────────────────────┘
```

### 2. **Statistical Analysis Engine**
```python
Components:
- Cointegration Testing (Engle-Granger, Johansen, KSS)
- Rolling Window Analysis (60-120 minute windows)
- Hedge Ratio Calculation (OLS regression)
- Z-Score Generation (standardized spread)
- Mean Reversion Detection
- Stationarity Tests (ADF, KPSS)
```

### 3. **Multi-Agent System Architecture**

```
┌──────────────────────────────────────────────┐
│         ORCHESTRATOR AGENT                   │
│  - Coordinates all agents                    │
│  - Final decision making                     │
│  - Position management                       │
└──────────────────────────────────────────────┘
                    ↓
    ┌───────────────┴───────────────┬─────────────────┐
    ↓                               ↓                 ↓
┌─────────────┐          ┌──────────────────┐  ┌──────────────┐
│ QUANT AGENT │          │  SENTIMENT AGENT │  │  RISK AGENT  │
│             │          │                  │  │              │
│ - Z-score   │          │ - Gemini 2.5     │  │ - Position   │
│ - Spread    │          │ - Google Search  │  │   sizing     │
│ - Signals   │          │ - News analysis  │  │ - Stop-loss  │
│             │          │ - Event impact   │  │ - Drawdown   │
└─────────────┘          └──────────────────┘  └──────────────┘
```

### 4. **Signal Generation Logic**

**Entry Conditions:**
- Z-score > +2.0: Short spread (Short Asset A, Long Asset B)
- Z-score < -2.0: Long spread (Long Asset A, Short Asset B)
- Cointegration p-value < 0.05 (must be cointegrated)
- Sentiment score > threshold (from Gemini agent)
- No adverse news events detected

**Exit Conditions:**
- Z-score crosses 0 (mean reversion complete)
- Z-score > ±3.0 (stop-loss)
- Cointegration breaks (p-value > 0.05)
- Holding period > 24 hours (max hold time)
- Adverse event detected by Gemini agent

**Position Sizing:**
```python
hedge_ratio = β from regression: Asset_B = α + β * Asset_A + ε
position_A = capital_per_trade
position_B = position_A * hedge_ratio
```

### 5. **Technology Stack**

**Backend:**
- Python 3.11+
- FastAPI (REST API for dashboard)
- asyncio (concurrent operations)
- pybit (Bybit API client)
- google-generativeai (Gemini API)
- pandas, numpy (data processing)
- statsmodels (cointegration tests)
- scipy (statistical analysis)

**Database:**
- PostgreSQL + TimescaleDB (time-series data)
- Redis (real-time cache, message queue)

**Frontend Dashboard:**
- Next.js 14 (React framework)
- TypeScript
- TailwindCSS
- shadcn/ui components
- Recharts (charts/graphs)
- WebSocket (real-time updates)

**Infrastructure:**
- Docker & Docker Compose
- Prometheus + Grafana (monitoring)
- PM2 or systemd (process management)

---

## Required Components

### 1. **Configuration Files**
- `.env` - API keys (Bybit, Gemini, database credentials)
- `config.yaml` - Trading parameters (z-score thresholds, position sizes, pairs)

### 2. **Core Modules**

```
src/
├── agents/
│   ├── orchestrator.py      # Main coordinator
│   ├── quant_agent.py        # Statistical analysis
│   ├── sentiment_agent.py    # Gemini + Google Search
│   └── risk_agent.py         # Risk management
├── data/
│   ├── bybit_client.py       # API + WebSocket client
│   ├── data_collector.py     # Historical & real-time data
│   └── database.py           # DB operations
├── strategy/
│   ├── cointegration.py      # Cointegration testing
│   ├── zscore.py             # Z-score calculation
│   ├── signals.py            # Entry/exit signals
│   └── hedge_ratio.py        # Dynamic hedge calculation
├── execution/
│   ├── order_manager.py      # Order placement
│   ├── position_manager.py   # Position tracking
│   └── risk_manager.py       # Risk controls
├── backtesting/
│   ├── backtest_engine.py    # Historical simulation
│   └── performance.py        # Metrics calculation
└── api/
    ├── main.py               # FastAPI server
    └── websocket.py          # Real-time updates

dashboard/
├── app/
│   ├── page.tsx              # Main dashboard
│   ├── trades/               # Trade history
│   ├── positions/            # Active positions
│   └── analytics/            # Charts & analysis
└── components/
    ├── PairChart.tsx         # Price + Z-score chart
    ├── TradeTable.tsx        # Trade history table
    └── ProfitMetrics.tsx     # P&L metrics
```

### 3. **Additional Requirements**

**API Keys & Credentials:**
- ✅ Bybit API key + secret (testnet & mainnet)
- ✅ Gemini API key
- PostgreSQL database (local or cloud)
- Redis instance (optional but recommended)

**Data Requirements:**
- Historical price data (minimum 90 days for cointegration)
- Real-time WebSocket feeds
- News/event data sources

**Risk Management:**
- Maximum position size per trade
- Daily loss limit
- Maximum number of concurrent pairs
- Minimum account balance

**Monitoring:**
- Latency monitoring (<100ms target)
- API rate limits tracking
- Error/exception logging
- Performance metrics (Sharpe ratio, win rate, max drawdown)

---

## Implementation Phases

### Phase 1: Data Infrastructure (2-3 days)
- Set up database (TimescaleDB)
- Implement Bybit WebSocket client
- Create data collection pipeline
- Historical data fetching & storage

### Phase 2: Statistical Engine (3-4 days)
- Cointegration testing module
- Z-score calculation
- Hedge ratio computation
- Rolling window analysis
- Signal generation logic

### Phase 3: Multi-Agent System (4-5 days)
- Implement Gemini 2.5 Flash integration
- Google Search grounding setup
- Sentiment analysis agent
- Risk management agent
- Orchestrator coordination logic

### Phase 4: Execution Engine (3-4 days)
- Order placement system
- Position management
- Risk controls
- Error handling & retry logic

### Phase 5: Dashboard UI (3-4 days)
- Next.js setup
- Real-time charts (price, z-score, spread)
- Trade history table
- P&L metrics
- Position monitoring

### Phase 6: Backtesting & Optimization (3-5 days)
- Backtest engine
- Parameter optimization
- Performance analysis
- Strategy refinement

### Phase 7: Testing & Deployment (2-3 days)
- Unit tests
- Integration tests
- Testnet trading
- Mainnet deployment

**Total Estimated Time: 20-28 days**

---

## Critical Success Factors

1. **Low Latency (<100ms)**
   - Use WebSocket for data feeds
   - Optimize code (async/await, vectorized operations)
   - Host close to Bybit servers (AWS Singapore)

2. **Robust Cointegration**
   - Rolling window tests (every 1-4 hours)
   - Multiple test methods (EG + Johansen)
   - Auto-pause trading when cointegration breaks

3. **Dynamic Hedge Ratios**
   - Recalculate every 4-8 hours
   - Use weighted regression (recent data weighted more)

4. **Sentiment Integration**
   - Gemini agent queries news every 15 minutes
   - Override statistical signals on major events
   - Track market regime changes

5. **Risk Management**
   - Max 2-3% risk per trade
   - Stop-loss at z-score ±3.0
   - Max 5 concurrent pairs
   - Daily loss limit: 10% of capital

6. **Performance Monitoring**
   - Target Sharpe ratio: >1.5
   - Win rate: >55%
   - Max drawdown: <20%
   - Average trade duration: 2-8 hours

---

## Additional Tools Needed

1. **Backtesting Data**
   - Historical OHLCV data for all pairs (1+ year)
   - Can fetch from Bybit API or use services like CryptoDataDownload

2. **Monitoring & Alerts**
   - Telegram bot for trade notifications
   - Email alerts for critical errors
   - Discord webhook (optional)

3. **Documentation**
   - API documentation
   - Strategy documentation
   - Deployment guide
   - Troubleshooting guide

4. **Security**
   - API key encryption
   - IP whitelisting on Bybit
   - Secure .env file management
   - 2FA on all accounts

---

## Key Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cointegration breakdown | Real-time monitoring, auto-pause |
| High slippage | Limit order types, size limits |
| API rate limits | Request throttling, WebSocket priority |
| Black swan events | Position size limits, stop-losses |
| Latency spikes | Redundant connections, error handling |
| Model overfitting | Walk-forward optimization, out-of-sample testing |

---

## Sources
- [Copula-based trading of cointegrated cryptocurrency Pairs](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-024-00702-7)
- [Evaluation of Dynamic Cointegration-Based Pairs Trading](https://arxiv.org/pdf/2109.10662)
- [High frequency multiscale relationships among major cryptocurrencies](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-021-00290-w)
- [Gemini API Grounding with Google Search](https://ai.google.dev/gemini-api/docs/google-search)
- [Bybit API Documentation](https://bybit-exchange.github.io/docs/v5/intro)
- [pybit - Official Python API](https://github.com/bybit-exchange/pybit)

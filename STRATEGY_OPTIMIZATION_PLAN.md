# Strategy Optimization & Testing Plan

## Phase 1: Audit & Modularization (Current)

### Existing Strategies
1. **Engle-Granger Cointegration** - `engle_granger_strategy.py`
2. **Orderbook Imbalance (OBI)** - `orderbook_imbalance_strategy.py`
3. **Correlation-RSI** - `correlation_rsi_strategy.py`
4. **Mean Reversion** - `mean_reversion_strategy.py`
5. **Strategy Manager** - `strategy_manager.py` (aggregator)

### Issues to Fix
- [ ] Phantom loss from previous trades blocking new trades
- [ ] WebSocket data not always available (34% REST fallback)
- [ ] Position sizing too small for BTC pairs
- [ ] No actual trades being executed

---

## Phase 2: Unit Testing Framework

### Test Structure
```
tests/
├── test_strategies/
│   ├── test_engle_granger.py
│   ├── test_orderbook_imbalance.py
│   ├── test_correlation_rsi.py
│   ├── test_mean_reversion.py
│   └── test_strategy_manager.py
├── test_execution/
│   ├── test_position_manager.py
│   ├── test_order_manager.py
│   └── test_risk_agent.py
└── fixtures/
    └── sample_data.py
```

### Test Coverage Goals
- ✅ Each strategy generates valid signals
- ✅ Edge cases (NaN, inf, empty data)
- ✅ Performance benchmarks
- ✅ Signal accuracy on historical data

---

## Phase 3: Strategy Optimization

### Optimization Priorities
1. **Fix Phantom Loss** - Clear trade history properly
2. **Improve WebSocket Reliability** - Reduce REST API fallbacks
3. **Tune Strategy Parameters** - Backtest optimal thresholds
4. **Add More Strategies**:
   - Volume Profile
   - VWAP Deviation
   - Funding Rate Arbitrage
   - Volatility Breakout

### Performance Metrics
- Sharpe Ratio > 1.5
- Win Rate > 55%
- Max Drawdown < 20%
- Average trade duration: 5-30 minutes (HFT)

---

## Phase 4: Backtesting & Validation

### Backtest Requirements
- Historical data: 90 days
- Walk-forward optimization
- Out-of-sample testing
- Monte Carlo simulation

---

## Next Steps
1. Fix phantom loss issue (URGENT)
2. Create unit test framework
3. Test each strategy individually
4. Optimize parameters
5. Re-enable trading with clean slate

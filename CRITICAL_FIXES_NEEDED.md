# URGENT: Trading System Issues & Fixes

## Current Status
- ✅ System IS trading (19 real trades executed)
- ❌ **Losing money**: -$217.20 real loss
- ❌ Average loss per trade: -$11.43
- ❌ Positions close in SECONDS (no time for profit)

## Root Causes

### 1. Strategies Trigger on Noise
- Orderbook imbalance changes every second
- RSI/correlation fluctuate rapidly
- Mean reversion signals too sensitive

### 2. Execution Problems
- **100x leverage on ETH** - Extremely risky!
- Market orders cause slippage
- No minimum holding period
- No profit target before exit

### 3. Risk Management Failures
- Positions close immediately after opening
- No time-based filters
- Commission costs (0.12%) eat all profits

## IMMEDIATE ACTIONS

### Step 1: DISABLE TRADING (Done)
```yaml
trading_enabled: false  # Already set in config
```

### Step 2: Fix Strategy Parameters

#### Engle-Granger
- Increase p-value threshold: 0.05 → 0.01 (stricter)
- Require longer cointegration window

#### Mean Reversion
- Increase z-score entry: 2.0 → 2.5
- Add confirmation period (3+ candles)

#### OBI (Orderbook Imbalance)
- Increase threshold: Current → 0.8+ (80% imbalance)
- Add smoothing (EMA over 5 periods)

### Step 3: Add Holding Period Logic
```python
MIN_HOLDING_TIME = 300  # 5 minutes minimum
MAX_HOLDING_TIME = 1800  # 30 minutes maximum
```

### Step 4: Switch to Limit Orders
- Use limit orders at mid-price
- Reduce slippage from ~0.5% to ~0.05%

### Step 5: Reduce Leverage
- ETH: 100x → 10x
- XRP: 10x → 5x
- BTC: Set to 5x

### Step 6: Add Profit Targets
- Minimum profit target: 0.3% (covers commission)
- Take profit at 0.5-1.0%
- Stop loss at -0.5%

## Testing Plan

1. **Backtest** on last 30 days with new parameters
2. **Paper trade** for 24 hours
3. **Live trade** with $100 max position size
4. **Scale up** only after 70%+ win rate

## Expected Improvements
- Win rate: 0% → 60%+
- Average P&L: -$11.43 → +$5-10
- Sharpe ratio: Negative → 1.5+

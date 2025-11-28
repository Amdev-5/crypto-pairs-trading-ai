# Quick Start Guide

Get your cryptocurrency pairs trading system up and running in minutes.

## Prerequisites

- Python 3.11+
- Node.js 18+ (for dashboard)
- Bybit account with API keys ([Get testnet keys](https://testnet.bybit.com/))
- Google Gemini API key ([Get free key](https://ai.google.dev/))

## Installation

### 1. Run Setup Script

```bash
python setup.py
```

This will:
- Create virtual environment
- Install all dependencies
- Create .env file
- Setup dashboard
- Create necessary directories

### 2. Configure API Keys

Edit `.env` file:

```bash
# Bybit API (get from https://testnet.bybit.com/app/user/api-management)
BYBIT_API_KEY=your_key_here
BYBIT_API_SECRET=your_secret_here
BYBIT_TESTNET=True  # Start with testnet!

# Gemini API (get from https://ai.google.dev/)
GEMINI_API_KEY=your_gemini_key_here
```

### 3. Test the System

Run in paper trading mode:

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the trading engine
python -m src.main
```

You should see:
```
Connecting to Bybit WebSocket...
Loading historical data...
Starting main trading loop...
```

### 4. Start the Dashboard

In another terminal:

```bash
cd dashboard
npm run dev
```

Open http://localhost:3000

## Configuration

### Trading Parameters (config.yaml)

```yaml
trading:
  pairs:
    - symbol_a: "BTCUSDT"
      symbol_b: "ETHUSDT"
      enabled: true

strategy:
  zscore:
    entry_threshold: 2.0
    exit_threshold: 0.5
    stop_loss_threshold: 3.0
```

### Risk Management

Key settings in `.env`:

```bash
MAX_POSITION_SIZE=1000      # USD per position
MAX_CONCURRENT_PAIRS=5      # Max open positions
DAILY_LOSS_LIMIT=500        # Stop trading if hit
RISK_PER_TRADE=0.02         # 2% risk per trade
```

## Testing Strategy

Before going live:

### 1. Backtest

```bash
python -m src.backtesting.backtest_engine \
  --start-date 2024-01-01 \
  --end-date 2024-11-26 \
  --initial-capital 10000
```

### 2. Paper Trading

Run with `TRADING_ENABLED=False` for 1-2 weeks:
- Monitor signals
- Check cointegration detection
- Verify risk management
- Analyze performance

### 3. Testnet Trading

Enable trading on Bybit testnet:

```bash
BYBIT_TESTNET=True
TRADING_ENABLED=True
```

### 4. Live Trading (Use with Caution!)

Only after successful testnet results:

```bash
BYBIT_TESTNET=False
TRADING_ENABLED=True
MAX_POSITION_SIZE=100  # Start small!
```

## Monitoring

### View Logs

```bash
tail -f logs/trading.log
```

### Key Metrics to Watch

1. **Cointegration Status**
   - P-value should be < 0.05
   - Check in logs: "Cointegration test: p-value=0.02"

2. **Z-Score**
   - Entry signals at ±2.0
   - Exit signals at 0
   - Stop-loss at ±3.0

3. **Performance**
   - Win rate > 55%
   - Sharpe ratio > 1.5
   - Max drawdown < 20%

4. **Latency**
   - Loop time should be < 60 seconds
   - WebSocket latency < 100ms

## Troubleshooting

### WebSocket Connection Issues

```
Error: WebSocket connection failed
```

**Solution**: Check internet connection and API keys

### Insufficient Data

```
Warning: Insufficient data for cointegration test
```

**Solution**: Wait for more historical data to load (needs ~90 days)

### API Rate Limits

```
Error: Rate limit exceeded
```

**Solution**: Reduce update frequency in config

### Gemini API Errors

```
Error: Invalid API key
```

**Solution**: Verify GEMINI_API_KEY in .env

## Understanding the Output

### Trading Signals

```
Decision for BTCUSDT_ETHUSDT: LONG_SPREAD (confidence: 0.75)
```

- `LONG_SPREAD`: Long BTC, Short ETH
- `SHORT_SPREAD`: Short BTC, Long ETH
- `CLOSE`: Close position
- `HOLD`: No action

### Position Updates

```
Position opened: BTCUSDT_ETHUSDT | Long 0.1 BTCUSDT, Short 2.5 ETHUSDT
Position closed: BTCUSDT_ETHUSDT | P&L: $12.50 (1.25%) | Duration: 120.5m
```

### Risk Alerts

```
Risk violation: Daily loss limit exceeded: $-520.00
```

System will pause trading when limits are hit.

## Next Steps

1. **Optimize Parameters**
   - Adjust z-score thresholds
   - Fine-tune position sizing
   - Experiment with different pairs

2. **Add More Pairs**
   - Test new cointegrated pairs
   - Monitor correlation breakdown
   - Diversify risk

3. **Enhance Strategy**
   - Add volatility filters
   - Implement time-based rules
   - Integrate more news sources

4. **Monitor Performance**
   - Review daily P&L
   - Analyze trade metrics
   - Adjust risk limits

## Support & Resources

- **Documentation**: See README.md and ARCHITECTURE.md
- **Configuration**: Check config.yaml for all parameters
- **Research**: Read papers linked in ARCHITECTURE.md

## Important Reminders

⚠️ **Risk Warnings**:
- Cryptocurrency trading is highly risky
- Past performance doesn't guarantee future results
- Never invest more than you can afford to lose
- Start small and scale gradually
- Monitor the system constantly

🛡️ **Security**:
- Never share your API keys
- Use IP whitelisting on Bybit
- Enable 2FA on all accounts
- Keep your .env file private

📊 **Best Practices**:
- Run backtests before live trading
- Use testnet for initial testing
- Start with small position sizes
- Keep detailed logs
- Review performance regularly

---

**Ready to Trade?**

Start with paper trading, monitor for at least 1 week, then gradually move to testnet and eventually live trading with small sizes.

Good luck and trade responsibly! 🚀

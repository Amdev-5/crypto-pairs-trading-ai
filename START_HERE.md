# 🚀 START HERE - Quick Launch Guide

Your trading system is configured and ready to go!

## ✅ Your API Keys Are Set

- ✅ Bybit Testnet API configured
- ✅ Gemini API configured
- ✅ Conservative risk settings applied

## 🎯 Next Steps (5 Minutes)

### Step 1: Install Dependencies

```bash
cd /Users/siketyson/Desktop/Claude/bybit

# Run setup script
python3 setup.py
```

This will:
- Create virtual environment
- Install all Python packages
- Setup the dashboard
- Create necessary directories

### Step 2: Start Trading Engine

```bash
# Activate virtual environment
source venv/bin/activate

# Start the trading engine
python -m src.main
```

You should see:
```
============================================================
CRYPTO PAIRS TRADING SYSTEM
============================================================
Trading pairs: 5
Trading enabled: False
Testnet mode: True
============================================================
Connecting to Bybit WebSocket...
Loading historical data...
Starting main trading loop...
```

### Step 3: Start Dashboard (Optional)

Open a new terminal:

```bash
cd /Users/siketyson/Desktop/Claude/bybit/dashboard

# Install dependencies (first time only)
npm install

# Start dashboard
npm run dev
```

Open: http://localhost:3000

## 📊 What You'll See

### Trading Engine Output:

```
--- Iteration 1 ---
Loaded 1440 candles for BTCUSDT
Loaded 1440 candles for ETHUSDT
Analyzing BTCUSDT_ETHUSDT...
Sentiment for BTC: 0.45 (confidence: 0.78)
Decision for BTCUSDT_ETHUSDT: LONG_SPREAD (confidence: 0.82)
Stats: 0 trades, Win rate: 0.0%, Total P&L: $0.00
```

### What's Happening:

1. **Loading Data**: Fetches 90 days of historical prices
2. **Cointegration Testing**: Checks if pairs are cointegrated
3. **Z-Score Calculation**: Monitors mean reversion signals
4. **Sentiment Analysis**: Gemini analyzes BTC/ETH/LTC news
5. **Decision Making**: Agents vote on trades
6. **Risk Checks**: Verifies all safety limits

## 🔍 Monitor in Real-Time

### View Logs:

```bash
# In another terminal
tail -f logs/trading.log
```

### Check What's Being Analyzed:

The system analyzes these pairs every minute:
- BTC/ETH (highest hedging effectiveness)
- BTC/LTC (strong mean-reversion)
- BTC/XRP
- BTC/BCH
- LTC/DOGE

## 🎮 Current Settings (Conservative)

```
TRADING_ENABLED=False        ← Paper trading mode
BYBIT_TESTNET=True          ← Using testnet
MAX_POSITION_SIZE=100       ← Small positions
MAX_CONCURRENT_PAIRS=3      ← Max 3 trades
DAILY_LOSS_LIMIT=50         ← Stop at -$50/day
```

## 📈 Understanding Signals

### Entry Signal Example:
```
Z-score: 2.15 → SHORT_SPREAD
```
- Spread is 2.15 standard deviations above mean
- Strategy: Short BTC, Long ETH
- Expected: Mean reversion back to 0

### Exit Signal Example:
```
Z-score: 0.45 → CLOSE
```
- Mean reversion occurred
- Close position for profit

## ⚙️ When to Enable Trading

Enable real trading when:
- ✅ System runs for 3-7 days without errors
- ✅ You see valid cointegration results (p-value < 0.05)
- ✅ Signals make sense (entry at ±2.0, exit at ~0)
- ✅ You understand the strategy
- ✅ You've reviewed the logs

To enable:
```bash
# Edit .env
TRADING_ENABLED=True  # Enable trading
BYBIT_TESTNET=True    # Keep testnet for now
```

## 🛡️ Safety Features Active

- ✅ Stop-loss at z-score ±3.0
- ✅ Daily loss limit: $50
- ✅ Max position size: $100
- ✅ Max concurrent pairs: 3
- ✅ Cointegration monitoring
- ✅ Automatic position closure on breakdown

## 📱 What to Watch For

### Good Signs ✅
- Cointegration p-value < 0.05
- Z-scores between -3 and +3
- System running smoothly
- No frequent disconnections

### Warning Signs ⚠️
- "Cointegration breakdown" messages
- Z-scores > ±3.0 (extreme)
- Frequent WebSocket disconnections
- API errors

## 🔧 Common Issues

### "Module not found" error:
```bash
# Make sure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

### "WebSocket connection failed":
```bash
# Check your internet connection
# Verify Bybit API keys are correct
# Try restarting the system
```

### "Insufficient data":
```bash
# Wait 5-10 minutes for data to load
# System needs ~90 days of history
```

### Gemini API errors:
```bash
# Verify your Gemini API key
# Check quota at: https://ai.google.dev/
```

## 📚 Learn More

- **QUICKSTART.md** - Detailed setup guide
- **README.md** - Full documentation
- **ARCHITECTURE.md** - How it works
- **config.yaml** - All parameters

## 🎯 Your First Week

### Days 1-3: Monitor Paper Trading
- Watch signals being generated
- Check cointegration results
- Verify risk management
- Review sentiment analysis

### Days 4-7: Analyze Performance
- Look at signal accuracy
- Check if pairs are cointegrated
- Monitor system stability
- Read the strategy documentation

### Week 2+: Consider Testnet
- If everything looks good
- Enable trading with testnet
- Start with smallest positions
- Scale gradually

## ⚠️ CRITICAL REMINDERS

1. **Regenerate Your API Keys**: You shared them publicly - regenerate after setup!
   - Bybit: https://testnet.bybit.com/app/user/api-management
   - Regenerate both API Key and Secret

2. **Start Small**:
   - Current settings are conservative
   - Don't increase until proven

3. **Paper Trade First**:
   - Run for at least 1 week
   - Understand the system
   - Build confidence

4. **Monitor Constantly**:
   - Check logs daily
   - Watch for errors
   - Review performance

5. **It's Your Risk**:
   - No guarantees of profit
   - Can lose money
   - Trade responsibly

## 🚀 Ready to Launch!

**Run this now:**

```bash
cd /Users/siketyson/Desktop/Claude/bybit
python3 setup.py
```

Then:

```bash
source venv/bin/activate
python -m src.main
```

**Watch the magic happen!** ✨

---

## 📞 Need Help?

- Check logs: `tail -f logs/trading.log`
- Review docs: `README.md`, `QUICKSTART.md`
- Verify settings: `.env`, `config.yaml`

---

## 🎉 You're Ready!

The system will:
1. ✅ Connect to Bybit WebSocket
2. ✅ Load historical data
3. ✅ Test cointegration
4. ✅ Calculate z-scores
5. ✅ Analyze sentiment with Gemini
6. ✅ Generate signals
7. ✅ Monitor risk

All running automatically every 60 seconds!

**Happy Trading!** 🚀

*Remember: This is paper trading mode. No real money at risk yet.*

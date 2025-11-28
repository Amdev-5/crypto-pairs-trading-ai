# 📊 How to See Your Trades in Bybit

## ✅ Trading is NOW ENABLED!

Your system will now place **REAL ORDERS** on Bybit Testnet (virtual money).

---

## 🌐 View Positions in Bybit Testnet

### 1. Login to Bybit Testnet

Go to: **https://testnet.bybit.com/**

Login with your testnet account credentials.

### 2. Navigate to Positions

**Option A - Futures Positions:**
```
Top Menu → Derivatives → USDT Perpetual
```

Then look at the **"Positions"** tab at the bottom.

**Option B - Direct Link:**
```
https://testnet.bybit.com/trade/usdt/BTCUSDT
```

### 3. What You'll See

When the agent opens a position, you'll see:

```
Symbol      | Side | Size    | Entry Price | Mark Price | Unrealized PNL
BTCUSDT     | Long | 0.015   | 50,250     | 50,280     | +$0.45
ETHUSDT     | Short| 0.35    | 2,850      | 2,845      | +$1.75
```

### 4. View Order History

**Trades → Order History**
```
https://testnet.bybit.com/user/orders
```

You'll see:
- Time of order
- Symbol
- Side (Buy/Sell)
- Type (Market/Limit)
- Filled Price
- Quantity

---

## 🤖 What the Agent Will Do

### When Z-Score Triggers Entry (±1.5):

**Example: BTC/ETH Pair**

If z-score > +1.5 (spread too high):
1. **SHORT BTC**: Sells BTCUSDT perpetual
2. **LONG ETH**: Buys ETHUSDT perpetual
3. Expects spread to decrease (mean reversion)

You'll see **2 orders** in Bybit:
- BTCUSDT: Short position
- ETHUSDT: Long position

### When Z-Score Returns to 0:

The agent closes both positions:
1. Closes BTCUSDT short
2. Closes ETHUSDT long
3. Books profit/loss

---

## 📱 Real-Time Monitoring

### In Your Terminal:

```bash
cd /Users/siketyson/Desktop/Claude/bybit
./run.sh
```

Look for these messages:

**When Opening Position:**
```
✓ Executing LONG_SPREAD for BTCUSDT_ETHUSDT...
✓ Orders executed successfully
✓ Position opened: BTCUSDT_ETHUSDT | Long 0.015 BTCUSDT, Short 0.35 ETHUSDT
```

**When Closing Position:**
```
✓ Closing position for BTCUSDT_ETHUSDT...
✓ Position closed: BTCUSDT_ETHUSDT | P&L: $12.50 (1.25%) | Duration: 120.5m
```

### In Bybit Dashboard:

Refresh your positions page to see:
- New positions appearing
- Position P&L updating in real-time
- Positions closing when z-score reverts

---

## 🔍 Step-by-Step: Your First Trade

### Step 1: Start the System

```bash
cd /Users/siketyson/Desktop/Claude/bybit
python3 setup.py  # If not done yet
./run.sh
```

### Step 2: Wait for Signal

The system checks every 60 seconds. You'll see:

```
--- Iteration 1 ---
Analyzing BTCUSDT_ETHUSDT...
Cointegration test: p-value=0.023 ✓ (cointegrated)
Z-score: 1.85 → Signal: LONG_SPREAD
Sentiment for BTC: 0.35 (confidence: 0.72)
Decision: LONG_SPREAD (confidence: 0.82)
```

### Step 3: Order Execution

```
Executing LONG_SPREAD for BTCUSDT_ETHUSDT...
Placing BUY order for BTCUSDT: 0.015 @ Market
Placing SELL order for ETHUSDT: 0.35 @ Market
✓ Orders executed successfully
Position opened!
```

### Step 4: Check Bybit

1. Go to: https://testnet.bybit.com/trade/usdt/BTCUSDT
2. Click **"Positions"** tab
3. You'll see your new positions!

### Step 5: Watch It Close

When z-score → 0:
```
Z-score: 0.35 → Signal: CLOSE
Closing position for BTCUSDT_ETHUSDT...
✓ Position closed | P&L: $8.50 (0.85%)
```

Check Bybit - positions are closed!

---

## 📊 Position Size Calculator

With current settings:
- **MAX_POSITION_SIZE**: $1000 per leg
- **Entry**: When |z-score| > 1.5

Example for BTC/ETH:
- BTC @ $50,000: Buy 0.02 BTC ($1000)
- ETH @ $2,800: Sell 0.357 ETH ($1000)
- Total exposure: $2000

---

## 🎯 What to Look For

### Good Signs ✅

1. **In Terminal:**
   - "Cointegration test: p-value=0.02" (< 0.05)
   - "Orders executed successfully"
   - "Position opened"

2. **In Bybit:**
   - Two opposite positions (one long, one short)
   - Positions showing in "Positions" tab
   - P&L updating in real-time

3. **Eventually:**
   - Positions close automatically
   - Profit/loss recorded
   - New positions opened for other pairs

### Warning Signs ⚠️

1. **In Terminal:**
   - "Error executing orders"
   - "API rate limit exceeded"
   - "Cointegration breakdown"

2. **In Bybit:**
   - Only one leg opened (should be two)
   - Very large position sizes
   - Positions not closing

---

## 🔧 Troubleshooting

### "Orders executed successfully" but nothing in Bybit?

1. Make sure you're on **testnet.bybit.com** (not regular bybit.com)
2. Check you're logged into the correct account
3. Verify API keys are for testnet
4. Look in "Order History" for filled orders

### Position sizes too small to see?

The system calculates position sizes based on:
- Your testnet account balance
- MAX_POSITION_SIZE setting
- Risk per trade (2%)

If balance is low, positions will be small.

### No trades happening?

This is normal! Trades only happen when:
- ✅ Pair is cointegrated (p-value < 0.05)
- ✅ Z-score crosses threshold (±1.5)
- ✅ Risk limits allow
- ✅ Sentiment doesn't contradict

Could take hours or days for perfect conditions.

---

## 📈 Speed Up Testing (Optional)

To see trades faster, you can:

### Make Z-Score Threshold Lower:

Edit `.env`:
```bash
ZSCORE_ENTRY_THRESHOLD=1.0  # Was 1.5, more signals
```

### Or Force Test Trade:

I can create a test script that forces a trade regardless of conditions (for testing only).

---

## 🎮 Current Configuration

```
✅ TRADING_ENABLED=True
✅ BYBIT_TESTNET=True (safe!)
✅ MAX_POSITION_SIZE=$1000
✅ MAX_CONCURRENT_PAIRS=5
✅ ZSCORE_ENTRY=1.5 (more sensitive)
✅ Multi-agent decision making
```

---

## 📱 Live Monitoring Setup

### Terminal 1: Trading Engine
```bash
cd /Users/siketyson/Desktop/Claude/bybit
./run.sh
```

### Terminal 2: Live Logs
```bash
tail -f logs/trading.log
```

### Terminal 3: Specific Events
```bash
# Watch for trades
watch -n 5 'grep "Position opened\|Position closed" logs/trading.log | tail -20'
```

### Browser: Bybit Dashboard
```
https://testnet.bybit.com/trade/usdt/BTCUSDT
```

Keep "Positions" tab open and refresh occasionally.

---

## 🚀 Ready to See Trades!

### Start Now:

```bash
cd /Users/siketyson/Desktop/Claude/bybit
./run.sh
```

### Watch For:

1. System connects to Bybit ✓
2. Loads historical data ✓
3. Analyzes cointegration ✓
4. Gemini analyzes sentiment ✓
5. **Generates trading signal**
6. **Executes orders**
7. **You see position in Bybit!**

---

## 💡 Pro Tip

Open these side-by-side:

**Left**: Terminal running `./run.sh`
**Right**: Browser with https://testnet.bybit.com/trade/usdt/BTCUSDT

When you see "Position opened" in terminal → Refresh Bybit → See the position!

---

## ⏱️ Timeline

- **0-5 min**: System starts, loads data
- **5-60 min**: First cointegration tests complete
- **Minutes to hours**: First signal generates
- **Instant**: Orders execute, appear in Bybit
- **Minutes to hours**: Position closes when z-score reverts

---

## 🎉 You're Set!

Everything is configured for **LIVE TRADING on TESTNET**!

Run:
```bash
cd /Users/siketyson/Desktop/Claude/bybit
./run.sh
```

Then watch the magic happen in:
- Your terminal (logs)
- Bybit testnet dashboard (positions)

**Happy Trading!** 🚀

*Remember: This is TESTNET - virtual money, real learning!*

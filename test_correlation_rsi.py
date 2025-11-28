"""Test the new Correlation + RSI strategy"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from src.data.bybit_client import get_bybit_client
from src.strategy.correlation_rsi_strategy import CorrelationRSIStrategy

async def test_strategy():
    print("=" * 80)
    print("🧪 TESTING CORRELATION + RSI STRATEGY")
    print("=" * 80)
    print()

    # Initialize
    client = get_bybit_client()
    strategy = CorrelationRSIStrategy(
        correlation_threshold=0.5,  # More relaxed for testing
        rsi_period=14,
        rsi_oversold=30,
        rsi_overbought=70,
        zscore_entry=0.3,  # More aggressive
        zscore_exit=0.1,
        lookback_periods=60
    )

    # Get historical data
    print("📊 Fetching historical data (last 2 hours)...")
    start_time = datetime.now() - timedelta(hours=2)

    # Fetch data for ETH and XRP
    eth_data = await client.get_historical_klines("ETHUSDT", interval="1", limit=120, start_time=start_time)
    xrp_data = await client.get_historical_klines("XRPUSDT", interval="1", limit=120, start_time=start_time)

    # Convert to pandas Series
    eth_prices = pd.Series(
        [k.close for k in eth_data],
        index=[k.timestamp for k in eth_data]
    )
    xrp_prices = pd.Series(
        [k.close for k in xrp_data],
        index=[k.timestamp for k in xrp_data]
    )

    print(f"✅ Fetched {len(eth_prices)} candles for ETHUSDT")
    print(f"✅ Fetched {len(xrp_prices)} candles for XRPUSDT")
    print()

    # Generate signal
    print("🎯 Generating trading signal...")
    signal = strategy.generate_signal(eth_prices, xrp_prices)

    print()
    print("=" * 80)
    print("📈 STRATEGY OUTPUT")
    print("=" * 80)
    print(f"Action: {signal.action}")
    print(f"Confidence: {signal.confidence * 100:.1f}%")
    print(f"Correlation: {signal.correlation:.3f}")
    print(f"RSI ETH: {signal.rsi_a:.1f}")
    print(f"RSI XRP: {signal.rsi_b:.1f}")
    print(f"Z-Score: {signal.zscore:.3f}")
    print(f"Reason: {signal.entry_reason}")
    print("=" * 80)
    print()

    # Show interpretation
    if signal.action in ['LONG_SPREAD', 'SHORT_SPREAD']:
        print(f"✅ TRADE SIGNAL: {signal.action}")
        if signal.action == 'LONG_SPREAD':
            print("   → BUY ETHUSDT, SELL XRPUSDT")
        else:
            print("   → SELL ETHUSDT, BUY XRPUSDT")
    elif signal.action == 'AVOID':
        print(f"⚠️  AVOID: {signal.entry_reason}")
    else:
        print(f"🔵 {signal.action}: {signal.entry_reason}")

    print()

if __name__ == "__main__":
    asyncio.run(test_strategy())

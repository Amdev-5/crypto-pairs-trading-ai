"""Comprehensive sanity test for Bybit pairs trading system"""

import requests
import json
from src.config import config
from src.data.bybit_client import get_bybit_client
import asyncio

print("=" * 80)
print("🧪 BYBIT PAIRS TRADING - COMPREHENSIVE SANITY TEST")
print("=" * 80)
print()

# Test 1: Configuration
print("📋 TEST 1: Configuration Check")
print("-" * 80)
print(f"✅ Testnet Mode: {config.bybit.testnet}")
print(f"✅ Trading Enabled: {config.trading.enabled}")
print(f"✅ Z-Score Entry Threshold: {config.trading.zscore_entry_threshold}")
print(f"✅ Z-Score Exit Threshold: {config.trading.zscore_exit_threshold}")
print(f"✅ Cointegration P-Value Threshold: {config.trading.cointegration_pvalue_threshold}")
print(f"✅ Cointegration Window: {config.trading.cointegration_window} minutes")
print(f"✅ Max Position Size: ${config.trading.max_position_size}")
print(f"✅ Trading Pairs: {len(config.get_trading_pairs())}")
for pair in config.get_trading_pairs():
    print(f"   - {pair['symbol_a']} / {pair['symbol_b']}")
print()

# Test 2: Bybit API Connection
print("📡 TEST 2: Bybit API Connection")
print("-" * 80)
try:
    client = get_bybit_client()
    balance = client.get_account_balance()
    print(f"✅ Connected to Bybit {'Testnet' if config.bybit.testnet else 'Mainnet'}")
    print(f"✅ Account Balance: ${balance:.2f}")
    print()
except Exception as e:
    print(f"❌ Bybit API Connection Failed: {e}")
    print()

# Test 3: Dashboard Server
print("🌐 TEST 3: Dashboard Server")
print("-" * 80)
try:
    response = requests.get("http://localhost:5000/", timeout=5)
    if response.status_code == 200:
        print(f"✅ Dashboard server is running on http://localhost:5000")
        print(f"✅ HTTP Status: {response.status_code}")
    else:
        print(f"⚠️  Dashboard returned status: {response.status_code}")
    print()
except Exception as e:
    print(f"❌ Dashboard server not accessible: {e}")
    print()

# Test 4: Dashboard Data File
print("📁 TEST 4: Dashboard Data File")
print("-" * 80)
try:
    with open("/tmp/bybit_dashboard_data.json", "r") as f:
        dashboard_data = json.load(f)

    print(f"✅ Dashboard data file exists")
    print(f"✅ Account Balance: ${dashboard_data.get('account_balance', 0):.2f}")
    print(f"✅ Available Balance: ${dashboard_data.get('available_balance', 0):.2f}")
    print(f"✅ Total P&L: ${dashboard_data.get('total_pnl', 0):.2f}")
    print(f"✅ Daily P&L: ${dashboard_data.get('daily_pnl', 0):.2f}")
    print(f"✅ Total Trades: {dashboard_data.get('total_trades', 0)}")
    print(f"✅ Trading Pairs in Data: {len(dashboard_data.get('pairs', {}))}")

    for pair_id, pair_data in dashboard_data.get('pairs', {}).items():
        print(f"   - {pair_id}:")
        print(f"     Z-Score: {pair_data.get('zscore', 0):.3f}")
        print(f"     Signal: {pair_data.get('signal', 'N/A')}")
        print(f"     Confidence: {pair_data.get('confidence', 0)*100:.1f}%")
        print(f"     Cointegrated: {pair_data.get('cointegration', {}).get('pvalue', 1.0) < 0.2}")
    print()
except Exception as e:
    print(f"⚠️  Dashboard data file not found or error: {e}")
    print()

# Test 5: Trading Engine Log
print("📊 TEST 5: Trading Engine Status")
print("-" * 80)
try:
    with open("logs/trading.log", "r") as f:
        lines = f.readlines()
        recent_logs = lines[-20:]  # Last 20 lines

    print(f"✅ Trading log file exists")
    print(f"✅ Recent log entries (last 20 lines):")
    for line in recent_logs:
        line = line.strip()
        if "Account balance" in line:
            print(f"   💰 {line}")
        elif "Decision for" in line:
            print(f"   🎯 {line}")
        elif "Loop time" in line:
            print(f"   ⏱️  {line}")
        elif "ERROR" in line:
            print(f"   ❌ {line}")
        elif "WARNING" in line:
            print(f"   ⚠️  {line}")
    print()
except Exception as e:
    print(f"⚠️  Trading log not found or error: {e}")
    print()

# Test 6: WebSocket Connection
print("🔌 TEST 6: WebSocket Data Stream")
print("-" * 80)
try:
    client = get_bybit_client()

    # Check tick buffer
    symbols_with_data = 0
    for symbol in ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'BCHUSDT', 'LTCUSDT', 'DOGEUSDT']:
        price = client.get_latest_price(symbol)
        if price:
            print(f"✅ {symbol}: ${price:.2f}")
            symbols_with_data += 1
        else:
            print(f"⚠️  {symbol}: No data yet")

    if symbols_with_data >= 4:
        print(f"\n✅ WebSocket is receiving live data for {symbols_with_data}/6 symbols")
    else:
        print(f"\n⚠️  Only {symbols_with_data}/6 symbols have data - may need more time")
    print()
except Exception as e:
    print(f"❌ WebSocket test failed: {e}")
    print()

print("=" * 80)
print("🎉 SANITY TEST COMPLETE")
print("=" * 80)
print()
print("Summary:")
print("- If all tests passed ✅, the system is running correctly")
print("- Dashboard: http://localhost:5000")
print("- Trading loop runs every 10 seconds (ULTRA AGGRESSIVE mode)")
print("- Z-Score threshold: 0.1 (very low = more trades)")
print("- You should see trades executing soon!")
print()

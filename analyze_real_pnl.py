#!/usr/bin/env python3
"""Analyze actual Bybit trades to calculate real P&L"""

from pybit.unified_trading import HTTP
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()

client = HTTP(
    testnet=True,
    api_key=os.getenv('BYBIT_API_KEY'),
    api_secret=os.getenv('BYBIT_API_SECRET')
)

print("=" * 80)
print("ACTUAL TRADE P&L ANALYSIS")
print("=" * 80)

# Get recent trades for each symbol
symbols = ['ETHUSDT', 'XRPUSDT', 'BTCUSDT']

total_pnl = 0
total_trades = 0

for symbol in symbols:
    try:
        # Get closed P&L
        result = client.get_closed_pnl(
            category="linear",
            symbol=symbol,
            limit=50
        )
        
        if result['retCode'] == 0 and result['result']['list']:
            print(f"\n📊 {symbol} Closed Positions:")
            print("-" * 80)
            
            for pnl in result['result']['list']:
                closed_pnl = float(pnl.get('closedPnl', 0))
                total_pnl += closed_pnl
                total_trades += 1
                
                print(f"  Closed: {pnl.get('updatedTime', 'N/A')}")
                print(f"  Side: {pnl.get('side', 'N/A')}")
                print(f"  Qty: {pnl.get('qty', 'N/A')}")
                print(f"  Entry Price: ${float(pnl.get('avgEntryPrice', 0)):.4f}")
                print(f"  Exit Price: ${float(pnl.get('avgExitPrice', 0)):.4f}")
                print(f"  P&L: ${closed_pnl:.4f}")
                print(f"  Leverage: {pnl.get('leverage', 'N/A')}")
                print()
                
    except Exception as e:
        print(f"Error getting P&L for {symbol}: {e}")

print("=" * 80)
print(f"SUMMARY:")
print(f"  Total Trades: {total_trades}")
print(f"  Total P&L: ${total_pnl:.2f}")
if total_trades > 0:
    print(f"  Average P&L per trade: ${total_pnl/total_trades:.2f}")
print("=" * 80)

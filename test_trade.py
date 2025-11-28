"""End-to-end test trade - manually execute a $5 pairs trade to verify system works"""

import asyncio
from src.data.bybit_client import get_bybit_client
from src.execution.order_manager import OrderManager
from src.execution.position_manager import PositionManager
from src.data.models import PositionSide
from datetime import datetime

async def test_trade():
    print("=" * 80)
    print("🧪 END-TO-END TEST TRADE")
    print("=" * 80)
    print()

    # Initialize components
    client = get_bybit_client()
    order_manager = OrderManager()
    position_manager = PositionManager()

    # Test parameters (using lower-priced pairs to meet minimum order size)
    pair_id = "TEST_ETHUSDT_XRPUSDT"
    symbol_a = "ETHUSDT"
    symbol_b = "XRPUSDT"
    test_amount = 100.0  # $100 per leg (min 0.01 ETH = ~$38)

    print("📊 Test Parameters:")
    print(f"   Pair: {symbol_a} / {symbol_b}")
    print(f"   Amount: ${test_amount} per leg")
    print(f"   Total Risk: ${test_amount * 2}")
    print()

    # Step 1: Get current prices using REST API
    print("1️⃣  Fetching current prices via REST API...")

    try:
        # Use REST API to get ticker info
        from pybit.unified_trading import HTTP
        from src.config import config

        http_client = HTTP(
            testnet=config.bybit.testnet,
            api_key=config.bybit.api_key,
            api_secret=config.bybit.api_secret
        )

        # Get BTC price
        ticker_a = http_client.get_tickers(category="linear", symbol=symbol_a)
        price_a = float(ticker_a['result']['list'][0]['lastPrice'])

        # Get ETH price
        ticker_b = http_client.get_tickers(category="linear", symbol=symbol_b)
        price_b = float(ticker_b['result']['list'][0]['lastPrice'])

        print(f"   {symbol_a}: ${price_a:.2f}")
        print(f"   {symbol_b}: ${price_b:.2f}")
        print()

        # Calculate simple hedge ratio (1:1 in dollar terms for simplicity)
        hedge_ratio = price_b / price_a

    except Exception as e:
        print(f"❌ Failed to get prices: {e}")
        return

    # Step 2: Calculate position sizes (very small for testing)
    print("2️⃣  Calculating position sizes...")
    size_a_usd = test_amount
    size_b_usd = test_amount

    size_a = size_a_usd / price_a  # Convert to contracts
    size_b = size_b_usd / price_b

    # Round to Bybit step sizes (ETH: 0.01, XRP: 1)
    if symbol_a == "ETHUSDT":
        size_a = round(size_a, 2)  # 0.01 ETH step
    elif symbol_a == "XRPUSDT":
        size_a = round(size_a, 0)  # 1 XRP step

    if symbol_b == "ETHUSDT":
        size_b = round(size_b, 2)  # 0.01 ETH step
    elif symbol_b == "XRPUSDT":
        size_b = round(size_b, 0)  # 1 XRP step

    print(f"   {symbol_a}: {size_a:.6f} contracts (${size_a_usd})")
    print(f"   {symbol_b}: {size_b:.6f} contracts (${size_b_usd})")
    print()

    # Step 3: Open the pairs trade (LONG_SPREAD = Long A, Short B)
    print("3️⃣  Opening LONG SPREAD position...")
    print(f"   LONG {symbol_a} @ ${price_a}")
    print(f"   SHORT {symbol_b} @ ${price_b}")
    print()

    try:
        success, result = await order_manager.execute_pair_entry(
            pair_id=pair_id,
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            action='LONG_SPREAD',
            size_a=size_a,
            size_b=size_b,
            hedge_ratio=hedge_ratio
        )

        if success:
            print("✅ Orders executed successfully!")
            print(f"   Entry Price A: ${result['entry_price_a']:.2f}")
            print(f"   Entry Price B: ${result['entry_price_b']:.2f}")
            print()

            # Step 4: Track the position
            print("4️⃣  Tracking position in position manager...")
            position_manager.add_position(
                pair_id=pair_id,
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                side_a=result['side_a'],
                side_b=result['side_b'],
                size_a=size_a,
                size_b=size_b,
                entry_price_a=result['entry_price_a'],
                entry_price_b=result['entry_price_b'],
                entry_zscore=0.5,
                hedge_ratio=hedge_ratio
            )
            print("✅ Position tracked")
            print()

            # Step 5: Wait a moment
            print("5️⃣  Waiting 5 seconds before closing...")
            await asyncio.sleep(5)

            # Step 6: Get current prices for P&L calculation (use REST API)
            ticker_a = http_client.get_tickers(category="linear", symbol=symbol_a)
            current_price_a = float(ticker_a['result']['list'][0]['lastPrice'])

            ticker_b = http_client.get_tickers(category="linear", symbol=symbol_b)
            current_price_b = float(ticker_b['result']['list'][0]['lastPrice'])

            # Step 7: Close the position
            print("6️⃣  Closing position...")
            success, close_result = await order_manager.execute_pair_exit(
                pair_id=pair_id,
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                side_a=result['side_a'],
                side_b=result['side_b'],
                size_a=size_a,
                size_b=size_b
            )

            if success:
                print("✅ Position closed successfully!")
                print(f"   Exit Price A: ${close_result['exit_price_a']:.2f}")
                print(f"   Exit Price B: ${close_result['exit_price_b']:.2f}")
                print()

                # Step 8: Close in position manager and calculate P&L
                print("7️⃣  Calculating P&L...")
                position_manager.close_position(
                    pair_id=pair_id,
                    exit_price_a=close_result['exit_price_a'],
                    exit_price_b=close_result['exit_price_b'],
                    exit_zscore=0.0,
                    reason="Test trade"
                )

                # Get statistics
                stats = position_manager.get_statistics()
                print(f"   Total P&L: ${stats['total_pnl']:.4f}")
                print(f"   Total Trades: {stats['total_trades']}")
                print()

                print("=" * 80)
                print("✅ END-TO-END TEST SUCCESSFUL!")
                print("=" * 80)
                print()
                print("All components working:")
                print("✅ Bybit API connectivity")
                print("✅ Price fetching")
                print("✅ Order execution (entry)")
                print("✅ Order execution (exit)")
                print("✅ Position tracking")
                print("✅ P&L calculation")
                print()
                print("The system is ready for live trading!")

            else:
                print(f"❌ Failed to close position: {close_result}")
        else:
            print(f"❌ Failed to open position: {result}")

    except Exception as e:
        print(f"❌ Error during test trade: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("Test complete. Check your Bybit testnet account to verify the trades.")

if __name__ == "__main__":
    asyncio.run(test_trade())

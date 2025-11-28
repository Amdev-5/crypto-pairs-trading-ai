"""Check recent orders on Bybit testnet"""

from pybit.unified_trading import HTTP
from src.config import config
from datetime import datetime, timedelta

print("=" * 80)
print("BYBIT TESTNET - RECENT ORDERS")
print("=" * 80)
print()

client = HTTP(
    testnet=config.bybit.testnet,
    api_key=config.bybit.api_key,
    api_secret=config.bybit.api_secret
)

# Check orders for ETH and XRP
symbols = ["ETHUSDT", "XRPUSDT"]

for symbol in symbols:
    print(f"📊 Recent orders for {symbol}:")
    print("-" * 80)

    try:
        # Get order history (last 24 hours)
        response = client.get_order_history(
            category="linear",
            symbol=symbol,
            limit=10
        )

        if response['retCode'] == 0:
            orders = response['result']['list']

            if not orders:
                print(f"   No orders found for {symbol}")
            else:
                for order in orders:
                    order_id = order['orderId']
                    side = order['side']
                    qty = order['qty']
                    price = order['avgPrice'] if order['avgPrice'] != '' else order['price']
                    status = order['orderStatus']
                    created = datetime.fromtimestamp(int(order['createdTime']) / 1000)
                    updated = datetime.fromtimestamp(int(order['updatedTime']) / 1000)

                    print(f"   Order ID: {order_id}")
                    print(f"   Side: {side} | Qty: {qty} | Price: ${price}")
                    print(f"   Status: {status}")
                    print(f"   Created: {created}")
                    print(f"   Updated: {updated}")
                    print()
        else:
            print(f"   ❌ Error: {response['retMsg']}")

    except Exception as e:
        print(f"   ❌ Error checking orders: {e}")

    print()

# Check trade history
print("📈 Recent trades:")
print("-" * 80)

for symbol in symbols:
    try:
        response = client.get_executions(
            category="linear",
            symbol=symbol,
            limit=10
        )

        if response['retCode'] == 0:
            trades = response['result']['list']

            if not trades:
                print(f"   No trades for {symbol}")
            else:
                print(f"   {symbol}:")
                for trade in trades:
                    exec_id = trade['execId']
                    side = trade['side']
                    qty = trade['execQty']
                    price = trade['execPrice']
                    exec_time = datetime.fromtimestamp(int(trade['execTime']) / 1000)

                    print(f"     {exec_time}: {side} {qty} @ ${price}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print()
print("=" * 80)
print("✅ Order check complete")
print("=" * 80)

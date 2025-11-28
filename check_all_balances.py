"""Check balances across all Bybit account types"""

from pybit.unified_trading import HTTP
from src.config import config
import json

# Initialize client
client = HTTP(
    testnet=config.bybit.testnet,
    api_key=config.bybit.api_key,
    api_secret=config.bybit.api_secret
)

print("=" * 80)
print("BYBIT ACCOUNT BALANCES (TESTNET)" if config.bybit.testnet else "BYBIT ACCOUNT BALANCES (MAINNET)")
print("=" * 80)
print()

account_types = ["UNIFIED", "CONTRACT", "SPOT", "FUNDING"]

total_usdt = 0.0

for account_type in account_types:
    try:
        print(f"📊 {account_type} Account:")
        print("-" * 80)

        response = client.get_wallet_balance(accountType=account_type)

        if response['retCode'] != 0:
            print(f"   ❌ Error: {response['retMsg']}")
            print()
            continue

        # Pretty print the response for debugging
        # print(json.dumps(response['result'], indent=2))

        if not response['result']['list']:
            print(f"   ℹ️  No data available")
            print()
            continue

        account_data = response['result']['list'][0]

        # Print account summary
        if 'totalEquity' in account_data:
            print(f"   Total Equity: ${float(account_data.get('totalEquity', 0)):.2f}")
        if 'totalWalletBalance' in account_data:
            print(f"   Total Wallet Balance: ${float(account_data.get('totalWalletBalance', 0)):.2f}")
        if 'totalAvailableBalance' in account_data:
            print(f"   Total Available: ${float(account_data.get('totalAvailableBalance', 0)):.2f}")
        if 'totalMarginBalance' in account_data:
            print(f"   Total Margin Balance: ${float(account_data.get('totalMarginBalance', 0)):.2f}")

        print()

        # Print coin balances
        if 'coin' in account_data:
            print(f"   Coin Balances:")
            for coin in account_data['coin']:
                coin_name = coin.get('coin', 'UNKNOWN')
                wallet_balance = float(coin.get('walletBalance', 0))
                available_balance = float(coin.get('availableToWithdraw', 0))
                equity = float(coin.get('equity', 0))
                locked = float(coin.get('locked', 0))

                if wallet_balance > 0 or equity > 0 or locked > 0:
                    print(f"   • {coin_name}:")
                    print(f"     - Wallet Balance: {wallet_balance:.6f}")
                    print(f"     - Available to Withdraw: {available_balance:.6f}")
                    print(f"     - Equity: {equity:.6f}")
                    print(f"     - Locked: {locked:.6f}")

                    if coin_name == 'USDT':
                        total_usdt += wallet_balance

        print()

    except Exception as e:
        print(f"   ❌ Error fetching {account_type}: {e}")
        print()

print("=" * 80)
print(f"💰 TOTAL USDT ACROSS ALL ACCOUNTS: ${total_usdt:.2f}")
print("=" * 80)
print()

# Show what the trading bot is seeing
print("🤖 Trading Bot is using:")
print(f"   Account Type: UNIFIED")
print(f"   Balance: ${total_usdt:.2f} (if UNIFIED has funds)")
print()

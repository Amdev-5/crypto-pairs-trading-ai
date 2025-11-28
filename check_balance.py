"""Check Bybit testnet balances across all account types"""

import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

load_dotenv()

# Initialize client
client = HTTP(
    testnet=True,
    api_key=os.getenv('BYBIT_API_KEY'),
    api_secret=os.getenv('BYBIT_API_SECRET')
)

print("=" * 60)
print("BYBIT TESTNET ACCOUNT BALANCES")
print("=" * 60)
print()

# 1. Check Unified Account (Used for perpetual futures)
print("1. UNIFIED ACCOUNT (Perpetual Futures):")
print("-" * 60)
try:
    response = client.get_wallet_balance(accountType="UNIFIED")
    print(f"Response Code: {response['retCode']}")
    print(f"Response Message: {response['retMsg']}")

    if response['retCode'] == 0 and response['result']['list']:
        account = response['result']['list'][0]
        print(f"\nTotal Equity: ${account.get('totalEquity', 'N/A')}")
        print(f"Total Wallet Balance: ${account.get('totalWalletBalance', 'N/A')}")
        print(f"Total Available Balance: ${account.get('totalAvailableBalance', 'N/A')}")
        print(f"Total Margin Balance: ${account.get('totalMarginBalance', 'N/A')}")

        print("\nCoins:")
        for coin in account.get('coin', []):
            if float(coin.get('walletBalance', 0)) > 0:
                print(f"  {coin['coin']}:")
                print(f"    Wallet Balance: {coin.get('walletBalance', '0')}")
                print(f"    Available: {coin.get('availableToWithdraw', '0')}")
                print(f"    Equity: {coin.get('equity', '0')}")
    else:
        print("No unified account data or error")
        print(response)
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)

# 2. Check Contract Account (Old perpetual account type)
print("2. CONTRACT ACCOUNT:")
print("-" * 60)
try:
    response = client.get_wallet_balance(accountType="CONTRACT")
    print(f"Response Code: {response['retCode']}")
    print(f"Response Message: {response['retMsg']}")

    if response['retCode'] == 0 and response['result']['list']:
        account = response['result']['list'][0]
        print(f"\nTotal Equity: ${account.get('totalEquity', 'N/A')}")
        print(f"Total Wallet Balance: ${account.get('totalWalletBalance', 'N/A')}")

        print("\nCoins:")
        for coin in account.get('coin', []):
            if float(coin.get('walletBalance', 0)) > 0:
                print(f"  {coin['coin']}: {coin.get('walletBalance', '0')}")
    else:
        print("No contract account data")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)

# 3. Check Spot Account
print("3. SPOT ACCOUNT:")
print("-" * 60)
try:
    response = client.get_wallet_balance(accountType="SPOT")
    print(f"Response Code: {response['retCode']}")
    print(f"Response Message: {response['retMsg']}")

    if response['retCode'] == 0 and response['result']['list']:
        account = response['result']['list'][0]

        print("\nCoins:")
        for coin in account.get('coin', []):
            if float(coin.get('walletBalance', 0)) > 0:
                print(f"  {coin['coin']}:")
                print(f"    Wallet Balance: {coin.get('walletBalance', '0')}")
                print(f"    Available: {coin.get('availableToWithdraw', '0')}")
    else:
        print("No spot account data")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)

# 4. Get Coin Balance (simpler API)
print("4. COIN BALANCES (All Accounts):")
print("-" * 60)
try:
    # Try to get all coin info
    response = client.get_coins_balance(accountType="UNIFIED")
    print(f"Response Code: {response['retCode']}")

    if response['retCode'] == 0:
        balances = response['result']['balance']
        for coin_data in balances:
            if float(coin_data.get('walletBalance', 0)) > 0:
                print(f"{coin_data['coin']}: {coin_data.get('walletBalance', '0')}")
except Exception as e:
    print(f"Not available or error: {e}")

print("\n" + "=" * 60)

# 5. Check Account Info
print("5. ACCOUNT INFO:")
print("-" * 60)
try:
    response = client.get_account_info()
    print(f"Response Code: {response['retCode']}")
    if response['retCode'] == 0:
        info = response['result']
        print(f"Unified Account Status: {info.get('unifiedMarginStatus', 'N/A')}")
        print(f"Margin Mode: {info.get('marginMode', 'N/A')}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("\nIf you see balances above, the API is working!")
print("The trading system needs to be updated to read the correct account type.")
print("=" * 60)

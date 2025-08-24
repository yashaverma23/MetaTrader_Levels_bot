import MetaTrader5 as mt5

# ==== CONFIG ====
ACCOUNT   = "Account login"         # your Exness account login
PASSWORD  = "Password"              # your Exness account password
SERVER    = "Server"                # Exness server name


def main():
    # Initialize MT5
    if not mt5.initialize(login=ACCOUNT, password=PASSWORD, server=SERVER):
        print("❌ MT5 initialization failed:", mt5.last_error())
        return

    # Account info
    account = mt5.account_info()
    if account:
        print(f"✅ Connected to MT5 | Login: {account.login} | Balance: {account.balance}")
    else:
        print("⚠️ Could not retrieve account info")

    # Show available symbols
    all_symbols = mt5.symbols_get()
    print(f"Total symbols: {len(all_symbols)}")
    print("First 20 symbols in Market Watch:")
    for s in all_symbols[:20]:
        print(" -", s.name)

    # Shutdown
    mt5.shutdown()


if __name__ == "__main__":
    main()

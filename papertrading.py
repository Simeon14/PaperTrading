import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import datetime
from tabulate import tabulate

Cash = 1000000
Tickers = [] 
Quantity = []
PurchasePrice = []
PL = []
PLPercent = []

def save():
    global Tickers, Quantity, PurchasePrice, Cash
    df = pd.DataFrame({
        'Ticker': Tickers,
        'Quantity': Quantity,
        'PurchasePrice': PurchasePrice
    })
    df.to_csv('positions.csv', index=False)
    pd.DataFrame({'Cash': [Cash]}).to_csv('cash.csv', index=False)
    print("Data saved successfully.")

def load():
    global Tickers, Quantity, PurchasePrice, Cash
    try:
        df = pd.read_csv('positions.csv')
        Tickers = df['Ticker'].tolist()
        Quantity = df['Quantity'].tolist()
        if 'PurchasePrice' in df.columns:
            PurchasePrice = df['PurchasePrice'].tolist()
        else:
            PurchasePrice = [0.0] * len(Tickers)
        df = pd.read_csv('cash.csv')
        Cash = float(df.loc[0, 'Cash'])
        print("Loaded data from file.")
    except FileNotFoundError:
        Tickers = []
        Quantity = []
        PurchasePrice = []
        Cash = 100000
        print("No data found. Starting with default values.")

def price(ticker):
    try:
        tk   = yf.Ticker(ticker)
        hist = tk.history(period='1d', interval='1m')
        if hist.empty:
            raise ValueError(f"No price data found for {ticker}")
        return hist['Close'].iloc[-1]
    except Exception as e:
        print(f"Error getting price for {ticker}: {e}")
        return None

def buy(ticker, amount):
    global Cash, Tickers, Quantity, PurchasePrice
    p = price(ticker)
    if p is None:
        return
    if Cash >= amount:
        Tickers.append(ticker)
        Quantity.append(amount / p)
        PurchasePrice.append(p)
        Cash -= amount
        print(f"Bought ${amount} of {ticker} @ ${p}")
    else:
        print("Not enough cash")

def sell(ticker, amount):
    global Cash, Tickers, Quantity, PurchasePrice
    idx = Tickers.index(ticker) if ticker in Tickers else -1
    if price(ticker) is None or idx == -1:
        return
    if amount > price(ticker)*Quantity[idx]:
        print("Not enough shares")
    elif amount == price(ticker)*Quantity[idx]:
        Cash += amount
        Quantity.pop(idx)
        Tickers.pop(idx)
        PurchasePrice.pop(idx)
        print(f"Sold ${amount} of {ticker} @ ${price(ticker)}")
    else:
        Cash += amount
        Quantity[idx] -= amount/price(ticker)
        print(f"Sold ${amount} of {ticker} @ ${price(ticker)}")

def sellall(ticker):
    global Cash, Tickers, Quantity, PurchasePrice
    idx = Tickers.index(ticker) if ticker in Tickers else -1
    if price(ticker) is None or idx == -1:
        return
    Cash += price(ticker)*Quantity[idx]
    Quantity.pop(idx)
    Tickers.pop(idx)
    PurchasePrice.pop(idx)
    print(f"Sold all of {ticker} @ ${price(ticker)}")

def short(ticker, amount):
    global Cash, Tickers, Quantity, PurchasePrice
    p = price(ticker)
    if p is None:
        return
    # Short selling: open or increase a short position
    if ticker in Tickers:
        idx = Tickers.index(ticker)
        # If already short, increase short position
        if Quantity[idx] < 0:
            # Weighted average price for short
            total_shares = abs(Quantity[idx]) + (amount / p)
            avg_price = (abs(Quantity[idx]) * PurchasePrice[idx] + (amount / p) * p) / total_shares
            Quantity[idx] -= amount / p
            PurchasePrice[idx] = avg_price
        # If currently long, treat as a new short (not allowed in real world, but for simplicity, force close long then open short)
        elif Quantity[idx] > 0:
            print("You must close your long position before shorting.")
            return
    else:
        Tickers.append(ticker)
        Quantity.append(-amount / p)
        PurchasePrice.append(p)
    Cash += amount
    print(f"Shorted ${amount} of {ticker} @ ${p}")

def cover(ticker, amount):
    global Cash, Tickers, Quantity, PurchasePrice
    p = price(ticker)
    if p is None:
        return
    if ticker in Tickers:
        idx = Tickers.index(ticker)
        if Quantity[idx] < 0:
            shares_to_cover = amount / p
            if abs(Quantity[idx]) < shares_to_cover:
                print("Not enough shorted shares to cover that amount.")
                return
            # If covering all
            if abs(Quantity[idx]) == shares_to_cover:
                Cash -= amount
                Quantity.pop(idx)
                Tickers.pop(idx)
                PurchasePrice.pop(idx)
                print(f"Covered ${amount} of {ticker} @ ${p}")
            else:
                Cash -= amount
                Quantity[idx] += shares_to_cover
                print(f"Covered ${amount} of {ticker} @ ${p}")
        else:
            print("You do not have a short position in this ticker.")
    else:
        print("You do not have a short position in this ticker.")

def list():
    global Tickers, Quantity, PurchasePrice
    green = "\033[92m"
    red = "\033[91m"
    reset = "\033[0m"
    print(f"Cash: ${Cash:,.2f}")
    if not Tickers:
        print("↳ (no positions)")
    else:
        prices = []
        values = []
        pl_dollars = []
        pl_percent = []
        pos_type = []
        qtys = []
        for ticker, qty, buy_price in zip(Tickers, Quantity, PurchasePrice):
            p = price(ticker)
            qtys.append(qty)
            if p is None:
                prices.append("N/A")
                values.append("N/A")
                pl_dollars.append("N/A")
                pl_percent.append("N/A")
                pos_type.append("")
            else:
                prices.append(f"${p:,.2f}")
                value = p * abs(qty)
                if qty > 0:
                    values.append(f"${value:,.2f}")
                    pl = value - (buy_price * qty)
                    pl_pct = (pl / (buy_price * qty)) * 100
                    pos_type.append(f"{green}LONG{reset}")
                elif qty < 0:
                    values.append(f"-${value:,.2f}")
                    pl = (buy_price - p) * abs(qty)
                    pl_pct = (pl / (buy_price * abs(qty))) * 100 if buy_price != 0 else 0
                    pos_type.append(f"{red}SHORT{reset}")
                else:
                    values.append(f"${value:,.2f}")
                    pl = 0
                    pl_pct = 0
                    pos_type.append("")
                pl_dollars.append(f"${pl:,.2f}")
                pl_percent.append(f"{pl_pct:.2f}%")
        df = pd.DataFrame({
            "Ticker": Tickers,
            "Type": pos_type,
            "Quantity": qtys,
            "Price": prices,
            "Value": values,
            "P/L($)": pl_dollars,
            "P/L(%)": pl_percent
        })
        print(tabulate(df, headers='keys', tablefmt='fancy_grid', showindex=False))

def quote(ticker):
    p = price(ticker)
    if p is None:
        print(f"Quote for {ticker}: N/A")
        return
    print(f"Price: ${p:,.2f}")
    # Daily Change
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="2d")
        if len(hist) < 2:
            print("(No previous close data)")
        else:
            prev_close = hist['Close'].iloc[-2]
            change = p - prev_close
            percent_change = (change / prev_close) * 100
            print(f"Daily Change: ${change:+.2f} ({percent_change:+.2f}%)")
    except Exception as e:
        print(f"(Error getting daily change: {e})")
    # YTD Change
    try:
        tk = yf.Ticker(ticker)
        ytd_hist = tk.history(period="ytd")
        if not ytd_hist.empty:
            ytd_start_price = ytd_hist['Close'].iloc[0]
            ytd_change = p - ytd_start_price
            ytd_percent = (ytd_change / ytd_start_price) * 100
            print(f"YTD Change: ${ytd_change:+.2f} ({ytd_percent:+.2f}%)")
        else:
            print("YTD Change: N/A")
    except Exception as e:
        print(f"(Error getting YTD change: {e})")
    # Volume
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="2d")
        if hist.empty:
            print(f"No data found for {ticker}")
        else:
            last_volume = hist['Volume'].iloc[-1]
            print(f"Volume: {last_volume:,}")
    except Exception as e:
        print(f"Error getting volume for {ticker}: {e}")

def plot_yearly(ticker):
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="1y")
        if hist.empty:
            print(f"No data found for {ticker}")
            return
        plt.figure(figsize=(10, 5))
        plt.plot(hist.index, hist['Close'], label=f"{ticker} Close Price")
        plt.title(f"{ticker} Price Over Last Year")
        plt.xlabel("Date")
        plt.ylabel("Price ($)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"Error plotting {ticker}: {e}")

def description(ticker):
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        desc = info.get("longBusinessSummary") or info.get("shortBusinessSummary")
        if desc:
            print(desc)
        else:
            print("No description available.")
    except Exception as e:
        print(f"Error getting description for {ticker}: {e}")

def help():
    print("Welcome to SW paper trading system, here are the commands:")
    print("buy (ticker) (amount) - Buy a specific amount of a ticker")
    print("sell (ticker) (amount) - Sell a specific amount of a ticker")
    print("sellall (ticker) - Sell all of a ticker")
    print("quote (ticker) - Get current price for a ticker")
    print("list - List all positions")
    print("save - Save the current positions and cash to a file")
    print("load - Load the positions and cash from a file")
    print("exit - Exit the program")

def main():
    load()
    print("Welcome to SW paper trading system!")
    while True:
        parts = input("> ").strip().split()
        if not parts:
            continue

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "buy" and len(args) == 2:
            ticker = args[0].upper()
            try:
                amount = float(args[1])
            except ValueError:
                print("↳ Amount must be a number")
                continue
            buy(ticker, amount)

        elif cmd == "sell" and len(args) == 2:
            ticker = args[0].upper()
            try:
                amount = float(args[1])
            except ValueError:
                print("↳ Amount must be a number")
                continue
            sell(ticker, amount)

        elif cmd == "sellall" and len(args) == 1:
            sellall(args[0].upper())

        elif cmd == "short" and len(args) == 2:
            ticker = args[0].upper()
            try:
                amount = float(args[1])
            except ValueError:
                print("↳ Amount must be a number")
                continue
            short(ticker, amount)

        elif cmd == "cover" and len(args) == 2:
            ticker = args[0].upper()
            try:
                amount = float(args[1])
            except ValueError:
                print("↳ Amount must be a number")
                continue
            cover(ticker, amount)

        elif cmd == "list":
            list()

        elif cmd == "save":
            save()

        elif cmd == "load":
            load()

        elif cmd == "q" and len(args) == 1:
            quote(args[0].upper())

        elif cmd == "g" and len(args) == 1:
            plot_yearly(args[0].upper())

        elif cmd == "des" and len(args) == 1:
            description(args[0].upper())

        elif cmd in ("exit", "quit"):
            print("Goodbye!")
            break

        elif cmd == "help":
            help()

        else:
            print("Unknown command or wrong args. Type one of:")
            print("  buy TICKER AMOUNT")
            print("  sell TICKER AMOUNT")
            print("  sellall TICKER")
            print("  short TICKER AMOUNT")
            print("  cover TICKER AMOUNT")
            print("  list")
            print("  save")
            print("  load")
            print("  exit")

if __name__ == "__main__":
    main()
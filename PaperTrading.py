import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import datetime

Cash = 100000
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
            PurchasePrice = [0.0] * len(Tickers)  # default fallback
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
    global Cash, Tickers, Quantity
    if price(ticker) is None:
        return
    if ticker in Tickers:
        if amount > price(ticker)*Quantity[Tickers.index(ticker)]:
            print("Not enough shares")
        elif amount == price(ticker)*Quantity[Tickers.index(ticker)]:
            Cash += amount
            Quantity.pop(Tickers.index(ticker))
            Tickers.pop(Tickers.index(ticker))
            print(f"Sold ${amount} of {ticker} @ ${price(ticker)}")
        else:
            Cash += amount
            Quantity[Tickers.index(ticker)] -= amount/price(ticker)
            print(f"Sold ${amount} of {ticker} @ ${price(ticker)}")

def sellall(ticker):
    global Cash, Tickers, Quantity
    if price(ticker) is None:
        return
    if ticker in Tickers:
        Cash += price(ticker)*Quantity[Tickers.index(ticker)]
        Quantity.pop(Tickers.index(ticker))
        Tickers.pop(Tickers.index(ticker))
        print(f"Sold all of {ticker} @ ${price(ticker)}")
    else:
        print("You don't have any shares of that ticker")

def list():
    global Tickers, Quantity, PurchasePrice
    print(f"Cash: ${Cash:,.2f}")
    if not Tickers:
        print("↳ (no positions)")
    else:
        prices = []
        values = []
        pl_dollars = []
        pl_percent = []
        for ticker, qty, buy_price in zip(Tickers, Quantity, PurchasePrice):
            p = price(ticker)
            if p is None:
                prices.append("N/A")
                values.append("N/A")
                pl_dollars.append("N/A")
                pl_percent.append("N/A")
            else:
                prices.append(f"${p:,.2f}")
                value = p * qty
                values.append(f"${value:,.2f}")
                pl = value - (buy_price * qty)
                pl_pct = (pl / (buy_price * qty)) * 100
                pl_dollars.append(f"${pl:,.2f}")
                pl_percent.append(f"{pl_pct:.2f}%")
        df = pd.DataFrame({
            "Ticker": Tickers,
            "Price": prices,
            "Value": values,
            "P/L($)": pl_dollars,
            "P/L(%)": pl_percent
        })
        print(df.to_string(index=False))

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

        elif cmd == "list":
            list()

        elif cmd == "save":
            save()

        elif cmd == "load":
            load()

        elif cmd in ("exit", "quit"):
            print("Goodbye!")
            break

        elif cmd == "help":
            print("Commands: buy TICKER AMOUNT | sell TICKER AMOUNT | sellall TICKER | list | save | load | exit")

        else:
            print("Unknown command or wrong args. Type one of:")
            print("  buy TICKER AMOUNT")
            print("  sell TICKER AMOUNT")
            print("  sellall TICKER")
            print("  list")
            print("  save")
            print("  load")
            print("  exit")

if __name__ == "__main__":
    main()
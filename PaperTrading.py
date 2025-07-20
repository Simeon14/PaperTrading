import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import datetime

Cash = 100000
Tickers = [] 
Quantity = []

def save():
    global Tickers, Quantity, Cash
    df = pd.DataFrame({'Ticker': Tickers, 'Quantity': Quantity})
    df.to_csv('positions.csv', index=False)
    pd.DataFrame({'Cash': [Cash]}).to_csv('cash.csv', index=False)

def load():
    global Tickers, Quantity, Cash
    try:
        df = pd.read_csv('positions.csv')
        Tickers = df['Ticker'].tolist()
        Quantity = df['Quantity'].tolist()
        df = pd.read_csv('cash.csv')
        Cash = float(df.loc[0, 'Cash'])
    except FileNotFoundError:
        Tickers = []
        Quantity = []
        Cash = 100000


def price(ticker):
    tk   = yf.Ticker(ticker)
    hist = tk.history(period='1d', interval='1m')
    if hist.empty:
        raise ValueError(f"No intraday data for {ticker}")
    return hist['Close'].iloc[-1]

def buy(ticker, amount):
    global Cash, Tickers, Quantity
    if Cash >= amount:
        Tickers.append(ticker)
        Quantity.append(amount/price(ticker))
        Cash -= amount
        print(f"Bought ${amount} of {ticker} @ ${price(ticker)}")
    else:
        print("Not enough cash")

def sell(ticker, amount):
    global Cash, Tickers, Quantity
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
    if ticker in Tickers:
        Cash += price(ticker)*Quantity[Tickers.index(ticker)]
        Quantity.pop(Tickers.index(ticker))
        Tickers.pop(Tickers.index(ticker))
        print(f"Sold all of {ticker} @ ${price(ticker)}")
    else:
        print("You don't have any shares of that ticker")

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
            print(f"Cash: ${Cash:,.2f}")
            if not Tickers:
                print("↳ (no positions)")
            else:
                prices = []
                for ticker, qty in zip(Tickers, Quantity):
                    v = price(ticker)
                    prices.append(f"${v:,.2f}")
                df = pd.DataFrame({
                    "Ticker": Tickers,
                    "Price": prices
                })
                print(df.to_string(index=False))

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

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import datetime
from tabulate import tabulate
import os

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

def format_amount(amount):
    # Format with commas, no decimal if .0
    if amount == int(amount):
        return f"${int(amount):,}"
    else:
        return f"${amount:,.2f}"

def buy(ticker, amount):
    global Cash, Tickers, Quantity, PurchasePrice
    p = price(ticker)
    if p is None:
        return
    if Cash >= amount:
        if ticker in Tickers:
            idx = Tickers.index(ticker)
            # Weighted average price for new total quantity
            old_qty = Quantity[idx]
            new_qty = old_qty + (amount / p)
            avg_price = (old_qty * PurchasePrice[idx] + (amount / p) * p) / new_qty
            Quantity[idx] = new_qty
            PurchasePrice[idx] = avg_price
        else:
            Tickers.append(ticker)
            Quantity.append(amount / p)
            PurchasePrice.append(p)
        Cash -= amount
        list(f"Bought {format_amount(amount)} of {ticker} @ ${p}")
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
        list(f"Sold {format_amount(amount)} of {ticker} @ ${price(ticker)}")
    else:
        Cash += amount
        Quantity[idx] -= amount/price(ticker)
        list(f"Sold {format_amount(amount)} of {ticker} @ ${price(ticker)}")

def sellall(ticker):
    global Cash, Tickers, Quantity, PurchasePrice
    idx = Tickers.index(ticker) if ticker in Tickers else -1
    if price(ticker) is None or idx == -1:
        return
    amt = price(ticker)*Quantity[idx]
    Cash += amt
    Quantity.pop(idx)
    Tickers.pop(idx)
    PurchasePrice.pop(idx)
    list(f"Sold all of {ticker} @ ${price(ticker)} for {format_amount(amt)}")

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
    list(f"Shorted {format_amount(amount)} of {ticker} @ ${p}")

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
                list(f"Covered {format_amount(amount)} of {ticker} @ ${p}")
            else:
                Cash -= amount
                Quantity[idx] += shares_to_cover
                list(f"Covered {format_amount(amount)} of {ticker} @ ${p}")
        else:
            print("You do not have a short position in this ticker.")
    else:
        print("You do not have a short position in this ticker.")

def list(message=None):
    global Tickers, Quantity, PurchasePrice
    # Clear the terminal
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"Cash: ${Cash:,.2f}")
    green = "\033[92m"
    red = "\033[91m"
    reset = "\033[0m"
    if not Tickers:
        print("No Positions")
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
        if message:
            print(f"↳ {message}")

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

def show_financials(ticker):
    import re
    try:
        tk = yf.Ticker(ticker)
        # Define key metrics for each statement
        income_keys = [
            'Total Revenue', 'Operating Revenue', 'Gross Profit', 'Operating Income', 'Net Income',
            'Diluted EPS', 'Basic EPS', 'EBITDA', 'EBIT'
        ]
        balance_keys = [
            'Total Assets', 'Total Liabilities Net Minority Interest', 'Total Equity Gross Minority Interest',
            'Cash And Cash Equivalents', 'Short Term Investments', 'Long Term Debt', 'Total Debt', 'Share Issued'
        ]
        cashflow_keys = [
            'Operating Cash Flow', 'Investing Cash Flow', 'Financing Cash Flow', 'End Cash Position', 'Free Cash Flow'
        ]
        def format_millions(df, keys):
            df = df.loc[keys]
            df = df.iloc[:, -10:]  # Get at most last 10 periods (most recent on the right)
            df = df.iloc[:, ::-1]  # Reverse columns so oldest is on the left, most recent on the right
            # Format column headers to 'Qn YYYY'
            def col_to_qtr_yr(col):
                if hasattr(col, 'year') and hasattr(col, 'month'):
                    year = col.year
                    month = col.month
                else:
                    m = re.match(r"(\d{4})-(\d{2})", str(col))
                    if m:
                        year = int(m.group(1))
                        month = int(m.group(2))
                    else:
                        return str(col)
                q = (month - 1) // 3 + 1
                return f"Q{q} {year}"
            df.columns = [col_to_qtr_yr(c) for c in df.columns]
            # Format numbers: millions, commas, no decimals, negatives as (xxx,xxx,xxx)
            def fmt(x):
                if pd.isnull(x):
                    return "-"
                x = x / 1e6
                n = int(round(x))
                if n < 0:
                    return f"({abs(n):,})"
                else:
                    return f"{n:,}"
            df = df.map(fmt)
            df.index.name = None
            return df
        # Income Statement (Quarterly)
        financials = tk.quarterly_financials
        if not financials.empty:
            available_keys = [k for k in income_keys if k in financials.index]
            if available_keys:
                df = format_millions(financials, available_keys)
                print("Income Statement (USD millions, Quarterly):")
                print(tabulate(df, headers='keys', tablefmt='fancy_grid', showindex=True))
            else:
                print("No key income statement metrics available.")
        else:
            print("No income statement data available.")
        # Balance Sheet (Quarterly)
        balance = tk.quarterly_balance_sheet
        if not balance.empty:
            available_keys = [k for k in balance_keys if k in balance.index]
            if available_keys:
                df = format_millions(balance, available_keys)
                print("\nBalance Sheet (USD millions, Quarterly):")
                print(tabulate(df, headers='keys', tablefmt='fancy_grid', showindex=True))
            else:
                print("No key balance sheet metrics available.")
        else:
            print("No balance sheet data available.")
        # Cash Flow (Quarterly)
        cashflow = tk.quarterly_cashflow
        if not cashflow.empty:
            available_keys = [k for k in cashflow_keys if k in cashflow.index]
            if available_keys:
                df = format_millions(cashflow, available_keys)
                print("\nCash Flow Statement (USD millions, Quarterly):")
                print(tabulate(df, headers='keys', tablefmt='fancy_grid', showindex=True))
            else:
                print("No key cash flow metrics available.")
        else:
            print("No cash flow statement data available.")
    except Exception as e:
        print(f"Error fetching financials for {ticker}: {e}")

def help():
    print("Welcome to SW paper trading system, here are the commands:")
    print("BUY (ticker) (amount) - Buy a specific amount of a ticker")
    print("SELL (ticker) (amount) - Sell a specific amount of a ticker")
    print("SELLALL (ticker) - Sell all of a ticker")
    print("SHORT (ticker) (amount) - Short sell a specific amount of a ticker")
    print("COVER (ticker) (amount) - Cover a specific amount of a short position")
    print("COVERALL (ticker) - Cover all of a short position")
    print("LIST - List all positions")
    print("SAVE - Save the current positions and cash to a file")
    print("LOAD - Load the positions and cash from a file")
    print("Q (ticker) - Get current price for a ticker")
    print("G (ticker) - Show a graph of the last year's price for a ticker")
    print("DES (ticker) - Show a description of a ticker")
    print("FA (ticker) - Show financial statement data for a ticker (quarterly)")
    print("EXIT - Exit the program")
    print("HELP - Show this help message")

def parse_amount(s):
    """Parse shorthand numbers like 50k, 2.5m, 100 into float values."""
    s = s.lower().replace(',', '')
    if s.endswith('k'):
        return float(s[:-1]) * 1_000
    elif s.endswith('m'):
        return float(s[:-1]) * 1_000_000
    elif s.endswith('b'):
        return float(s[:-1]) * 1_000_000_000
    else:
        return float(s)

class PaperTradingAccount:
    def __init__(self):
        self.Cash = 1000000
        self.Tickers = []
        self.Quantity = []
        self.PurchasePrice = []
        self.realized_pl = 0.0

    def save(self):
        df = pd.DataFrame({
            'Ticker': self.Tickers,
            'Quantity': self.Quantity,
            'PurchasePrice': self.PurchasePrice
        })
        df.to_csv('positions.csv', index=False)
        pd.DataFrame({'Cash': [self.Cash], 'RealizedPL': [self.realized_pl]}).to_csv('cash.csv', index=False)

    def load(self):
        try:
            df = pd.read_csv('positions.csv')
            self.Tickers = df['Ticker'].tolist()
            self.Quantity = df['Quantity'].tolist()
            if 'PurchasePrice' in df.columns:
                self.PurchasePrice = df['PurchasePrice'].tolist()
            else:
                self.PurchasePrice = [0.0] * len(self.Tickers)
            df = pd.read_csv('cash.csv')
            self.Cash = float(df.loc[0, 'Cash'])
            if 'RealizedPL' in df.columns:
                self.realized_pl = float(df.loc[0, 'RealizedPL'])
            else:
                self.realized_pl = 0.0
        except FileNotFoundError:
            self.Tickers = []
            self.Quantity = []
            self.PurchasePrice = []
            self.Cash = 1000000
            self.realized_pl = 0.0

    def price(self, ticker):
        try:
            tk = yf.Ticker(ticker)
            hist = tk.history(period='1d', interval='1m')
            if hist.empty:
                raise ValueError(f"No price data found for {ticker}")
            return hist['Close'].iloc[-1]
        except Exception as e:
            return None

    def buy(self, ticker, amount):
        p = self.price(ticker)
        if p is None:
            return False, f"No price data for {ticker}"
        if self.Cash >= amount:
            if ticker in self.Tickers:
                idx = self.Tickers.index(ticker)
                old_qty = self.Quantity[idx]
                new_qty = old_qty + (amount / p)
                avg_price = (old_qty * self.PurchasePrice[idx] + (amount / p) * p) / new_qty
                self.Quantity[idx] = new_qty
                self.PurchasePrice[idx] = avg_price
            else:
                self.Tickers.append(ticker)
                self.Quantity.append(amount / p)
                self.PurchasePrice.append(p)
            self.Cash -= amount
            return True, f"Bought {format_amount(amount)} of {ticker} @ ${p}"
        else:
            return False, "Not enough cash"

    def sell(self, ticker, amount):
        idx = self.Tickers.index(ticker) if ticker in self.Tickers else -1
        p = self.price(ticker)
        if p is None or idx == -1:
            return False, f"No position or price for {ticker}"
        if amount > p * self.Quantity[idx]:
            return False, "Not enough shares"
        elif amount == p * self.Quantity[idx]:
            # Realized P/L for full close
            buy_price = self.PurchasePrice[idx]
            qty = self.Quantity[idx]
            pl = (p - buy_price) * qty
            self.realized_pl += pl
            self.Cash += amount
            self.Quantity.pop(idx)
            self.Tickers.pop(idx)
            self.PurchasePrice.pop(idx)
            return True, f"Sold {format_amount(amount)} of {ticker} @ ${p}"
        else:
            # Partial sell: realize P/L on sold shares
            buy_price = self.PurchasePrice[idx]
            shares_sold = amount / p
            pl = (p - buy_price) * shares_sold
            self.realized_pl += pl
            self.Cash += amount
            self.Quantity[idx] -= shares_sold
            return True, f"Sold {format_amount(amount)} of {ticker} @ ${p}"

    def sellall(self, ticker):
        idx = self.Tickers.index(ticker) if ticker in self.Tickers else -1
        p = self.price(ticker)
        if p is None or idx == -1:
            return False, f"No position or price for {ticker}"
        qty = self.Quantity[idx]
        buy_price = self.PurchasePrice[idx]
        pl = (p - buy_price) * qty
        self.realized_pl += pl
        amt = p * qty
        self.Cash += amt
        self.Quantity.pop(idx)
        self.Tickers.pop(idx)
        self.PurchasePrice.pop(idx)
        return True, f"Sold all of {ticker} @ ${p} for {format_amount(amt)}"

    def coverall(self, ticker):
        idx = self.Tickers.index(ticker) if ticker in self.Tickers else -1
        p = self.price(ticker)
        if p is None or idx == -1:
            return False, f"No position or price for {ticker}"
        if self.Quantity[idx] >= 0:
            return False, "You do not have a short position in this ticker."
        qty = abs(self.Quantity[idx])
        buy_price = self.PurchasePrice[idx]
        pl = (buy_price - p) * qty
        self.realized_pl += pl
        amt = p * qty
        self.Cash -= amt
        self.Quantity.pop(idx)
        self.Tickers.pop(idx)
        self.PurchasePrice.pop(idx)
        return True, f"Covered all of {ticker} @ ${p} for {format_amount(amt)}"

    def short(self, ticker, amount):
        p = self.price(ticker)
        if p is None:
            return False, f"No price data for {ticker}"
        if ticker in self.Tickers:
            idx = self.Tickers.index(ticker)
            if self.Quantity[idx] < 0:
                total_shares = abs(self.Quantity[idx]) + (amount / p)
                avg_price = (abs(self.Quantity[idx]) * self.PurchasePrice[idx] + (amount / p) * p) / total_shares
                self.Quantity[idx] -= amount / p
                self.PurchasePrice[idx] = avg_price
            elif self.Quantity[idx] > 0:
                return False, "You must close your long position before shorting."
        else:
            self.Tickers.append(ticker)
            self.Quantity.append(-amount / p)
            self.PurchasePrice.append(p)
        self.Cash += amount
        return True, f"Shorted {format_amount(amount)} of {ticker} @ ${p}"

    def cover(self, ticker, amount):
        p = self.price(ticker)
        if p is None:
            return False, f"No price data for {ticker}"
        if ticker in self.Tickers:
            idx = self.Tickers.index(ticker)
            if self.Quantity[idx] < 0:
                shares_to_cover = amount / p
                if abs(self.Quantity[idx]) < shares_to_cover:
                    return False, "Not enough shorted shares to cover that amount."
                if abs(self.Quantity[idx]) == shares_to_cover:
                    # Realized P/L for full cover
                    buy_price = self.PurchasePrice[idx]
                    qty = abs(self.Quantity[idx])
                    pl = (buy_price - p) * qty
                    self.realized_pl += pl
                    self.Cash -= amount
                    self.Quantity.pop(idx)
                    self.Tickers.pop(idx)
                    self.PurchasePrice.pop(idx)
                    return True, f"Covered {format_amount(amount)} of {ticker} @ ${p}"
                else:
                    # Partial cover: realize P/L on covered shares
                    buy_price = self.PurchasePrice[idx]
                    pl = (buy_price - p) * shares_to_cover
                    self.realized_pl += pl
                    self.Cash -= amount
                    self.Quantity[idx] += shares_to_cover
                    return True, f"Covered {format_amount(amount)} of {ticker} @ ${p}"
            else:
                return False, "You do not have a short position in this ticker."
        else:
            return False, "You do not have a short position in this ticker."

    def get_portfolio(self):
        # Returns a DataFrame for display
        return pd.DataFrame({
            'Ticker': self.Tickers,
            'Quantity': self.Quantity,
            'PurchasePrice': self.PurchasePrice
        })

    def get_cash(self):
        return self.Cash

    def get_realized_pl(self):
        return self.realized_pl

# Remove global variables and top-level trading functions, and use the PaperTradingAccount class for all trading logic in main().

if __name__ == "__main__":
    account = PaperTradingAccount()
    account.load()
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
                amount = parse_amount(args[1])
            except ValueError:
                print("↳ Amount must be a number (e.g., 50000, 50k, 2.5m)")
                continue
            success, msg = account.buy(ticker, amount)
            print(msg)
        elif cmd == "sell" and len(args) == 2:
            ticker = args[0].upper()
            try:
                amount = parse_amount(args[1])
            except ValueError:
                print("↳ Amount must be a number (e.g., 50000, 50k, 2.5m)")
                continue
            success, msg = account.sell(ticker, amount)
            print(msg)
        elif cmd == "sellall" and len(args) == 1:
            success, msg = account.sellall(args[0].upper())
            print(msg)
        elif cmd == "short" and len(args) == 2:
            ticker = args[0].upper()
            try:
                amount = parse_amount(args[1])
            except ValueError:
                print("↳ Amount must be a number (e.g., 50000, 50k, 2.5m)")
                continue
            success, msg = account.short(ticker, amount)
            print(msg)
        elif cmd == "coverall" and len(args) == 1:
            success, msg = account.coverall(args[0].upper())
            print(msg)
        elif cmd == "cover" and len(args) == 2:
            ticker = args[0].upper()
            try:
                amount = parse_amount(args[1])
            except ValueError:
                print("↳ Amount must be a number (e.g., 50000, 50k, 2.5m)")
                continue
            success, msg = account.cover(ticker, amount)
            print(msg)
        elif cmd == "list":
            # Show portfolio with realized/unrealized P/L
            df = account.get_portfolio()
            if df.empty:
                print(f"Cash: ${account.get_cash():,.2f}")
                print("No Positions")
            else:
                print(f"Cash: ${account.get_cash():,.2f}")
                tickers = account.Tickers
                qtys = account.Quantity
                prices = []
                values = []
                pl_dollars = []
                pl_percent = []
                pos_type = []
                total_unrealized_pl = 0
                total_invested = 0
                for ticker, qty, buy_price in zip(tickers, qtys, account.PurchasePrice):
                    p = account.price(ticker)
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
                            total_unrealized_pl += pl
                            total_invested += buy_price * qty
                            pos_type.append("LONG")
                        elif qty < 0:
                            values.append(f"-${value:,.2f}")
                            pl = (buy_price - p) * abs(qty)
                            pl_pct = (pl / (buy_price * abs(qty))) * 100 if buy_price != 0 else 0
                            total_unrealized_pl += pl
                            total_invested += buy_price * abs(qty)
                            pos_type.append("SHORT")
                        else:
                            values.append(f"${value:,.2f}")
                            pl = 0
                            pl_pct = 0
                            pos_type.append("")
                        pl_dollars.append(f"${pl:,.2f}")
                        pl_percent.append(f"{pl_pct:.2f}%")
                import pandas as pd
                df = pd.DataFrame({
                    "Ticker": tickers,
                    "Type": pos_type,
                    "Quantity": qtys,
                    "Purchase Price": account.PurchasePrice,
                    "Price": prices,
                    "Value": values,
                    "P/L($)": pl_dollars,
                    "P/L(%)": pl_percent
                })
                from tabulate import tabulate
                print(tabulate(df, headers='keys', tablefmt='fancy_grid', showindex=False))
                realized_pl = account.get_realized_pl()
                overall_pl = total_unrealized_pl + realized_pl
                print(f"Overall P/L: ${overall_pl:,.2f}")
                STARTING_VALUE = 100000  # Fixed starting value for P/L percentage
                realized_pl_pct = (realized_pl / STARTING_VALUE) * 100
                print(f"Realized P/L: ${realized_pl:,.2f} ({realized_pl_pct:+.2f}%)")
        elif cmd == "save":
            account.save()
            print("Portfolio saved.")
        elif cmd == "load":
            account.load()
            print("Portfolio loaded.")
        elif cmd == "q" and len(args) == 1:
            p = account.price(args[0].upper())
            if p is None:
                print(f"Quote for {args[0].upper()}: N/A")
            else:
                print(f"Price: ${p:,.2f}")
        elif cmd == "g" and len(args) == 1:
            from matplotlib import pyplot as plt
            import yfinance as yf
            tkf = yf.Ticker(args[0].upper())
            hist = tkf.history(period="1y")
            if hist.empty:
                print(f"No data found for {args[0].upper()}")
            else:
                plt.figure(figsize=(10, 5))
                plt.plot(hist.index, hist['Close'], label=f"{args[0].upper()} Close Price")
                plt.title(f"{args[0].upper()} Price Over Last Year")
                plt.xlabel("Date")
                plt.ylabel("Price ($)")
                plt.legend()
                plt.grid(True)
                plt.tight_layout()
                plt.show()
        elif cmd == "des" and len(args) == 1:
            from yfinance import Ticker
            tkf = Ticker(args[0].upper())
            info = tkf.info
            desc = info.get("longBusinessSummary") or info.get("shortBusinessSummary")
            if desc:
                print(desc)
            else:
                print("No description available.")
        elif cmd == "fa" and len(args) == 1:
            # (Omitted for brevity, can be copied from above)
            pass
        elif cmd in ("exit", "quit"):
            account.save()
            print("Goodbye!")
            break
        elif cmd == "help":
            # (Omitted for brevity, can be copied from above)
            pass
        else:
            print("Unknown command or wrong args. Type 'help' for a list of commands.")
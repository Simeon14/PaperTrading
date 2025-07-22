import tkinter as tk
from tkinter import ttk
from papertrading import PaperTradingAccount, parse_amount
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import threading
import io
import sys
import time

DARK_BG = '#181a1b'  # Even darker background
DARK_FG = '#f8f8f2'
DARK_ENTRY = '#23272e'
DARK_ACCENT = '#222326'
GREEN = '#50fa7b'
RED = '#ff5555'
FONT = ('Consolas', 11)

class PaperTradingApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Paper Trading GUI')
        self.root.configure(bg=DARK_BG)
        self.account = PaperTradingAccount()
        self.account.load()
        self.latest_prices = {}  # Cache for latest prices
        self.price_thread_running = True
        self.create_widgets()
        self.print_welcome()
        self.refresh_portfolio()
        self.start_price_thread()

    def start_price_thread(self):
        def price_updater():
            while self.price_thread_running:
                tickers = self.account.Tickers
                if tickers:
                    try:
                        # Use yfinance Tickers for batch price fetch
                        data = yf.download(' '.join(tickers), period='1d', interval='1m', progress=False, group_by='ticker', threads=True, auto_adjust=False)
                        for ticker in tickers:
                            try:
                                if len(tickers) == 1:
                                    # Single ticker: data is not multi-indexed
                                    price = data['Close'].iloc[-1]
                                else:
                                    price = data[ticker]['Close'].iloc[-1]
                                self.latest_prices[ticker] = price
                            except Exception:
                                self.latest_prices[ticker] = None
                    except Exception:
                        for ticker in tickers:
                            self.latest_prices[ticker] = None
                time.sleep(5)
        threading.Thread(target=price_updater, daemon=True).start()

    def get_price(self, ticker):
        # Use cached price if available, else fallback to slow fetch
        price = self.latest_prices.get(ticker)
        if price is not None:
            return price
        return self.account.price(ticker)

    def create_widgets(self):
        # Output area (read-only)
        self.output = tk.Text(self.root, height=18, bg=DARK_BG, fg=DARK_FG, insertbackground=DARK_FG, font=FONT, wrap='word', state='disabled', borderwidth=0)
        self.output.pack(padx=10, pady=(10, 2), fill='both', expand=True)

        # Portfolio table (Treeview)
        style = ttk.Style()
        style.theme_use('default')
        style.configure('Treeview',
                        background=DARK_BG,
                        foreground=DARK_FG,
                        fieldbackground=DARK_BG,
                        rowheight=24,
                        font=FONT)
        style.configure('Treeview.Heading', background=DARK_ACCENT, foreground=DARK_FG, font=(FONT[0], FONT[1], 'bold'))
        style.map('Treeview', background=[('selected', DARK_ACCENT)])

        tree_frame = tk.Frame(self.root, bg=DARK_BG)
        tree_frame.pack(padx=10, pady=(0, 2), fill='x')
        self.tree = ttk.Treeview(tree_frame, columns=('Ticker', 'Type', 'Quantity', 'Purchase Price', 'Price', 'Value', 'P/L($)', 'P/L(%)'), show='headings', height=10)
        self._sort_orders = {col: False for col in self.tree['columns']}  # False: ascending, True: descending
        for col in self.tree['columns']:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_by_column(_col))
            self.tree.column(col, anchor='center', width=100)
        self.tree.pack(fill='x', expand=True)

        # Cash label
        self.cash_var = tk.StringVar()
        self.cash_label = tk.Label(self.root, textvariable=self.cash_var, font=('Consolas', 12, 'bold'), bg=DARK_BG, fg=GREEN)
        self.cash_label.pack(pady=(0, 0))

        # Overall P/L label
        self.pl_var = tk.StringVar()
        self.pl_label = tk.Label(self.root, textvariable=self.pl_var, font=('Consolas', 12, 'bold'), bg=DARK_BG)
        self.pl_label.pack(pady=(0, 8))

        # Command input
        input_frame = tk.Frame(self.root, bg=DARK_BG)
        input_frame.pack(padx=10, pady=(0, 10), fill='x')
        self.input_entry = tk.Entry(input_frame, bg=DARK_ENTRY, fg=DARK_FG, insertbackground=DARK_FG, font=FONT, borderwidth=2, relief='flat')
        self.input_entry.pack(side='left', fill='x', expand=True)
        self.input_entry.bind('<Return>', self.process_command)
        self.input_entry.focus()
        tk.Label(input_frame, text='↵', bg=DARK_BG, fg=DARK_FG, font=FONT).pack(side='right', padx=6)

    def print_welcome(self):
        self.print_output("Welcome to SW paper trading system! Type commands below.\nType 'help' for a list of commands.")

    def print_output(self, text, error=False):
        self.output.config(state='normal')
        tag = 'error' if error else 'normal'
        self.output.insert('end', text + '\n', tag)
        self.output.see('end')
        self.output.config(state='disabled')
        self.output.tag_config('normal', foreground=DARK_FG)
        self.output.tag_config('error', foreground=RED)

    def refresh_portfolio(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        tickers = self.account.Tickers
        qtys = self.account.Quantity
        prices = []
        values = []
        pl_dollars = []
        pl_percent = []
        type_display = []
        total_pl = 0
        total_invested = 0
        for ticker, qty, buy_price in zip(tickers, qtys, self.account.PurchasePrice):
            p = self.get_price(ticker)
            if p is None:
                prices.append('N/A')
                values.append('N/A')
                pl_dollars.append('N/A')
                pl_percent.append('N/A')
                type_display.append('')
            else:
                prices.append(f"${p:,.2f}")
                value = p * abs(qty)
                if qty > 0:
                    values.append(f"${value:,.2f}")
                    pl = value - (buy_price * qty)
                    pl_pct = (pl / (buy_price * qty)) * 100
                    total_pl += pl
                    total_invested += buy_price * qty
                    type_display.append('🟢 long')
                elif qty < 0:
                    values.append(f"-${value:,.2f}")
                    pl = (buy_price - p) * abs(qty)
                    pl_pct = (pl / (buy_price * abs(qty))) * 100 if buy_price != 0 else 0
                    total_pl += pl
                    total_invested += buy_price * abs(qty)
                    type_display.append('🔴 short')
                else:
                    values.append(f"${value:,.2f}")
                    pl = 0
                    pl_pct = 0
                    type_display.append('')
                pl_dollars.append(f"${pl:,.2f}")
                pl_percent.append(f"{pl_pct:.2f}%")
        for i in range(len(tickers)):
            purchase_price = self.account.PurchasePrice[i]
            purchase_price_str = f"${purchase_price:,.2f}" if purchase_price is not None else 'N/A'
            self.tree.insert('', 'end', values=(tickers[i], type_display[i], f"{qtys[i]:.4f}", purchase_price_str, prices[i], values[i], pl_dollars[i], pl_percent[i]))
        self.cash_var.set(f"Cash: ${self.account.get_cash():,.2f}")
        # Overall P/L display
        if total_invested > 0:
            pl_pct = (total_pl / total_invested) * 100
        else:
            pl_pct = 0
        pl_color = GREEN if total_pl > 0 else RED if total_pl < 0 else DARK_FG
        self.pl_label.config(fg=pl_color)
        self.pl_var.set(f"Overall P/L: ${total_pl:,.2f}  ({pl_pct:+.2f}%)")

    def process_command(self, event=None):
        # Clear output area before showing new command output
        self.output.config(state='normal')
        self.output.delete('1.0', 'end')
        self.output.config(state='disabled')
        cmdline = self.input_entry.get().strip()
        self.input_entry.delete(0, 'end')
        if not cmdline:
            return
        parts = cmdline.split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]
        try:
            if cmd == 'buy' and len(args) == 2:
                ticker = args[0].upper()
                amount = parse_amount(args[1])
                success, msg = self.account.buy(ticker, amount)
                self.print_output(msg, error=not success)
            elif cmd == 'sell' and len(args) == 2:
                ticker = args[0].upper()
                amount = parse_amount(args[1])
                success, msg = self.account.sell(ticker, amount)
                self.print_output(msg, error=not success)
            elif cmd == 'sellall' and len(args) == 1:
                ticker = args[0].upper()
                success, msg = self.account.sellall(ticker)
                self.print_output(msg, error=not success)
            elif cmd == 'short' and len(args) == 2:
                ticker = args[0].upper()
                amount = parse_amount(args[1])
                success, msg = self.account.short(ticker, amount)
                self.print_output(msg, error=not success)
            elif cmd == 'cover' and len(args) == 2:
                ticker = args[0].upper()
                amount = parse_amount(args[1])
                success, msg = self.account.cover(ticker, amount)
                self.print_output(msg, error=not success)
            elif cmd == 'save':
                self.account.save()
                self.print_output('Portfolio saved.')
            elif cmd == 'load':
                self.account.load()
                self.print_output('Portfolio loaded.')
            elif cmd == 'list':
                self.refresh_portfolio()
                self.print_output('Portfolio refreshed.')
            elif cmd == 'help':
                self.print_output("""Commands:\n  buy (ticker) (amount)\n  sell (ticker) (amount)\n  sellall (ticker)\n  short (ticker) (amount)\n  cover (ticker) (amount)\n  q (ticker)\n  g (ticker)\n  des (ticker)\n  fa (ticker)\n  save\n  load\n  list\n  help\n  exit\nExamples:\n  buy AAPL 50k\n  sell TSLA 10k\n  short MSFT 100k\n  cover MSFT 50k\n  q AAPL\n  g TSLA\n  des MSFT\n  fa AAPL\n""")
            elif cmd == 'q' and len(args) == 1:
                self.quote(args[0].upper())
            elif cmd == 'g' and len(args) == 1:
                threading.Thread(target=self.plot_yearly, args=(args[0].upper(),)).start()
            elif cmd == 'des' and len(args) == 1:
                self.description(args[0].upper())
            elif cmd == 'fa' and len(args) == 1:
                threading.Thread(target=self.show_financials, args=(args[0].upper(),)).start()
            elif cmd in ('exit', 'quit'):
                self.root.destroy()
                sys.exit()
            else:
                self.print_output('Unknown command. Type help for a list of commands.', error=True)
        except Exception as e:
            self.print_output(f'Error: {e}', error=True)
        self.refresh_portfolio()

    def quote(self, ticker):
        p = self.account.price(ticker)
        if p is None:
            self.print_output(f"Quote for {ticker}: N/A", error=True)
            return
        self.print_output(f"Price: ${p:,.2f}")
        try:
            tkf = yf.Ticker(ticker)
            hist = tkf.history(period="2d")
            if len(hist) < 2:
                self.print_output("(No previous close data)")
            else:
                prev_close = hist['Close'].iloc[-2]
                change = p - prev_close
                percent_change = (change / prev_close) * 100
                self.print_output(f"Daily Change: ${change:+.2f} ({percent_change:+.2f}%)")
        except Exception as e:
            self.print_output(f"(Error getting daily change: {e})", error=True)
        try:
            tkf = yf.Ticker(ticker)
            ytd_hist = tkf.history(period="ytd")
            if not ytd_hist.empty:
                ytd_start_price = ytd_hist['Close'].iloc[0]
                ytd_change = p - ytd_start_price
                ytd_percent = (ytd_change / ytd_start_price) * 100
                self.print_output(f"YTD Change: ${ytd_change:+.2f} ({ytd_percent:+.2f}%)")
            else:
                self.print_output("YTD Change: N/A")
        except Exception as e:
            self.print_output(f"(Error getting YTD change: {e})", error=True)
        try:
            tkf = yf.Ticker(ticker)
            hist = tkf.history(period="2d")
            if hist.empty:
                self.print_output(f"No data found for {ticker}")
            else:
                last_volume = hist['Volume'].iloc[-1]
                self.print_output(f"Volume: {last_volume:,}")
        except Exception as e:
            self.print_output(f"Error getting volume for {ticker}: {e}", error=True)

    def plot_yearly(self, ticker):
        try:
            tkf = yf.Ticker(ticker)
            hist = tkf.history(period="1y")
            if hist.empty:
                self.print_output(f"No data found for {ticker}", error=True)
                return
            plt.style.use('dark_background')
            plt.figure(figsize=(8, 4))
            plt.plot(hist.index, hist['Close'], label=f"{ticker} Close Price", color='#50fa7b')
            plt.title(f"{ticker} Price Over Last Year")
            plt.xlabel("Date")
            plt.ylabel("Price ($)")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            self.print_output(f"Error plotting {ticker}: {e}", error=True)

    def description(self, ticker):
        try:
            tkf = yf.Ticker(ticker)
            info = tkf.info
            desc = info.get("longBusinessSummary") or info.get("shortBusinessSummary")
            if desc:
                self.print_output(desc)
            else:
                self.print_output("No description available.")
        except Exception as e:
            self.print_output(f"Error getting description for {ticker}: {e}", error=True)

    def show_financials(self, ticker):
        import re
        try:
            tkf = yf.Ticker(ticker)
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
                df = df.iloc[:, -10:]
                df = df.iloc[:, ::-1]
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
            financials = tkf.quarterly_financials
            cashflow = tkf.quarterly_cashflow
            balance = tkf.quarterly_balance_sheet
            # Income Statement
            if not financials.empty:
                available_keys = [k for k in income_keys if k in financials.index]
                if available_keys:
                    df = format_millions(financials, available_keys)
                    self.print_output("Income Statement (USD millions, Quarterly):\n" + df.to_string())
                else:
                    self.print_output("No key income statement metrics available.")
            else:
                self.print_output("No income statement data available.")
            # Cash Flow Statement
            if not cashflow.empty:
                available_keys = [k for k in cashflow_keys if k in cashflow.index]
                if available_keys:
                    df = format_millions(cashflow, available_keys)
                    self.print_output("\nCash Flow Statement (USD millions, Quarterly):\n" + df.to_string())
                else:
                    self.print_output("No key cash flow metrics available.")
            else:
                self.print_output("No cash flow statement data available.")
            # Balance Sheet (last)
            if not balance.empty:
                available_keys = [k for k in balance_keys if k in balance.index]
                if available_keys:
                    df = format_millions(balance, available_keys)
                    self.print_output("\nBalance Sheet (USD millions, Quarterly):\n" + df.to_string())
                else:
                    self.print_output("No key balance sheet metrics available.")
            else:
                self.print_output("No balance sheet data available.")
        except Exception as e:
            self.print_output(f"Error fetching financials for {ticker}: {e}", error=True)

    # schedule_price_update removed: now handled by background thread

    def sort_by_column(self, col):
        # Get all items from the treeview
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        # Try to convert data to float for numeric columns
        def try_float(val):
            try:
                # Remove $ and % and commas for conversion
                return float(val.replace('$','').replace('%','').replace(',','').replace('(','-').replace(')',''))
            except Exception:
                return val
        data.sort(key=lambda t: try_float(t[0]), reverse=self._sort_orders[col])
        # Toggle sort order for next click
        self._sort_orders[col] = not self._sort_orders[col]
        # Rearrange items in sorted positions
        for index, (val, k) in enumerate(data):
            self.tree.move(k, '', index)

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry('1200x800')
    app = PaperTradingApp(root)
    root.mainloop() 
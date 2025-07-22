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
import os

DARK_BG = '#181a1b'  # Even darker background
DARK_FG = '#f8f8f2'
DARK_ENTRY = '#23272e'
DARK_ACCENT = '#222326'
GREEN = '#50fa7b'
RED = '#ff5555'
ACCENT = '#4fa3ff'
FONT_SANS = ('Segoe UI', 12)
HEADER_FONT = ('Segoe UI', 13, 'bold')
MONO_FONT = ('Consolas', 12)

class PaperTradingApp:
    def __init__(self, root):
        self.root = root
        self.root.title('SW Paper Trading Dashboard')
        self.root.configure(bg=DARK_BG)
        self.root.geometry('1800x1200')
        self.root.minsize(1200, 800)
        # To use a custom icon, place 'icon.ico' in the project directory
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass
        self.account = PaperTradingAccount()
        self.account.load()
        self.latest_prices = {}  # Cache for latest prices
        self.price_thread_running = True
        self._last_sorted_col = None
        self._last_sort_desc = False
        self.create_widgets()
        # Bind ~ and ` keys globally to focus input after widgets are created
        self.root.bind_all('<KeyRelease-asciitilde>', lambda event: self.input_entry.focus_set())
        self.root.bind_all('<KeyRelease-grave>', lambda event: self.input_entry.focus_set())
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
        output_frame = tk.Frame(self.root, bg=DARK_BG)
        output_frame.pack(padx=20, pady=(30, 18), fill='both', expand=True)
        self.output = tk.Text(output_frame, height=24, bg='#000000', fg=DARK_FG, insertbackground=DARK_FG, font=MONO_FONT, wrap='word', state='disabled', borderwidth=2, relief='groove', highlightthickness=2, highlightbackground='#23272e')
        self.output.pack(padx=10, pady=10, fill='both', expand=True)

        # Portfolio table (Treeview)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview',
                        background=DARK_BG,
                        foreground=DARK_FG,
                        fieldbackground=DARK_BG,
                        rowheight=32,
                        font=FONT_SANS,
                        borderwidth=0)
        style.configure('Treeview.Heading', background='#23272e', foreground=ACCENT, font=HEADER_FONT, borderwidth=0)
        style.map('Treeview', background=[('selected', DARK_ACCENT)])
        style.layout('Treeview', [('Treeview.treearea', {'sticky': 'nswe'})])
        style.configure('Treeview', borderwidth=0, relief='flat')

        tree_frame = tk.Frame(self.root, bg=DARK_BG)
        tree_frame.pack(padx=20, pady=(0, 18), fill='x')
        self.tree = ttk.Treeview(tree_frame, columns=('Ticker', 'Type', 'Quantity', 'Average Cost', 'Price', 'Value', 'P/L($)', 'P/L(%)'), show='headings', height=15, selectmode='browse')
        self._sort_orders = {col: False for col in self.tree['columns']}  # False: ascending, True: descending
        for col in self.tree['columns']:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_by_column(_col))
            self.tree.column(col, anchor='center', width=140, minwidth=80, stretch=True)
        self.tree.pack(fill='x', expand=True, padx=10, pady=10)
        # Zebra striping
        self.tree.tag_configure('oddrow', background='#202225')
        self.tree.tag_configure('evenrow', background='#181a1b')
        self.tree.tag_configure('pl_positive', foreground=GREEN)
        self.tree.tag_configure('pl_negative', foreground=RED)
        self.tree.tag_configure('pl_neutral', foreground=DARK_FG)

        # Cash label
        self.cash_var = tk.StringVar()
        self.cash_label = tk.Label(self.root, textvariable=self.cash_var, font=HEADER_FONT, bg=DARK_BG, fg=GREEN, pady=8)
        self.cash_label.pack(pady=(0, 0))

        # Overall P/L label
        self.pl_var = tk.StringVar()
        self.pl_label = tk.Label(self.root, textvariable=self.pl_var, font=HEADER_FONT, bg=DARK_BG)
        self.pl_label.pack(pady=(0, 24))

        # Command input
        input_frame = tk.Frame(self.root, bg=DARK_BG)
        input_frame.pack(padx=20, pady=(0, 30), fill='x')
        self.input_entry = tk.Entry(input_frame, bg=DARK_ENTRY, fg=DARK_FG, insertbackground=DARK_FG, font=FONT_SANS, borderwidth=2, relief='groove', highlightthickness=2, highlightbackground=ACCENT)
        self.input_entry.pack(side='left', fill='x', expand=True, padx=(0, 0), ipady=6)
        self.input_entry.bind('<Return>', self.process_command)
        # Modern submit button
        submit_btn = tk.Button(input_frame, text='Submit', font=FONT_SANS, bg=ACCENT, fg='white', activebackground='#357ab7', activeforeground='white', borderwidth=0, relief='flat', padx=18, pady=6, command=lambda: self.process_command())
        submit_btn.pack(side='right')
        self.input_entry.focus()
        # Removed the ↵ label and right-side padding

    def print_welcome(self):
        self.print_output("Welcome to SW paper trading system! Type commands below.\nType 'help' for a list of commands.\n(Press ` or ~ to focus the command input box.)")

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
        # Dynamically set Treeview height based on number of rows
        num_rows = max(1, min(len(tickers), 20))
        self.tree.config(height=num_rows)
        qtys = self.account.Quantity
        prices = []
        values = []
        pl_dollars = []
        pl_percent = []
        type_display = []
        total_unrealized_pl = 0
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
                    total_unrealized_pl += pl
                    total_invested += buy_price * qty
                    type_display.append('LONG')
                elif qty < 0:
                    values.append(f"-${value:,.2f}")
                    pl = (buy_price - p) * abs(qty)
                    pl_pct = (pl / (buy_price * abs(qty))) * 100 if buy_price != 0 else 0
                    total_unrealized_pl += pl
                    total_invested += buy_price * abs(qty)
                    type_display.append('SHORT')
                else:
                    values.append(f"${value:,.2f}")
                    pl = 0
                    pl_pct = 0
                    type_display.append('')
                pl_dollars.append(f"${pl:,.2f}")
                pl_percent.append(f"{pl_pct:.2f}%")
        realized_pl = self.account.get_realized_pl()
        overall_pl = total_unrealized_pl + realized_pl
        for i in range(len(tickers)):
            avg_cost = self.account.PurchasePrice[i]
            avg_cost_str = f"${avg_cost:,.2f}" if avg_cost is not None else 'N/A'
            # Zebra striping and P/L coloring
            row_tags = []
            row_tags.append('evenrow' if i % 2 == 0 else 'oddrow')
            # Color P/L column
            pl_val = pl_dollars[i]
            if isinstance(pl_val, str) and pl_val.startswith('$'):
                try:
                    pl_num = float(pl_val.replace('$','').replace(',',''))
                    if pl_num > 0:
                        row_tags.append('pl_positive')
                    elif pl_num < 0:
                        row_tags.append('pl_negative')
                    else:
                        row_tags.append('pl_neutral')
                except Exception:
                    row_tags.append('pl_neutral')
            else:
                row_tags.append('pl_neutral')
            self.tree.insert('', 'end', values=(tickers[i], type_display[i], f"{qtys[i]:.4f}", avg_cost_str, prices[i], values[i], pl_dollars[i], pl_percent[i]), tags=tuple(row_tags))
        self.cash_var.set(f"Cash: ${self.account.get_cash():,.2f}")
        # Overall P/L display
        if total_invested > 0:
            pl_pct = (total_unrealized_pl / total_invested) * 100
        else:
            pl_pct = 0
        pl_color = GREEN if total_unrealized_pl > 0 else RED if total_unrealized_pl < 0 else DARK_FG
        self.pl_label.config(fg=pl_color)
        self.pl_var.set(f"Unrealized P/L: ${total_unrealized_pl:,.2f}  ({pl_pct:+.2f}%)\nRealized P/L: ${realized_pl:,.2f}")
        # Re-apply last sort if any, else default to Value descending
        if self._last_sorted_col is not None:
            self.sort_by_column(self._last_sorted_col, force_desc=self._last_sort_desc, remember=False)
        else:
            self.sort_by_column('Value', force_desc=True, remember=False)

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
                # Accept both 'buy TICKER AMOUNT' and 'buy AMOUNT TICKER'
                a1, a2 = args[0], args[1]
                if a1.replace('.', '', 1).isdigit() or any(c.isdigit() for c in a1):
                    amount = parse_amount(a1)
                    ticker = a2.upper()
                else:
                    ticker = a1.upper()
                    amount = parse_amount(a2)
                success, msg = self.account.buy(ticker, amount)
                self.print_output(msg, error=not success)
            elif cmd == 'sell' and len(args) == 2:
                a1, a2 = args[0], args[1]
                if a1.replace('.', '', 1).isdigit() or any(c.isdigit() for c in a1):
                    amount = parse_amount(a1)
                    ticker = a2.upper()
                else:
                    ticker = a1.upper()
                    amount = parse_amount(a2)
                success, msg = self.account.sell(ticker, amount)
                self.print_output(msg, error=not success)
            elif cmd == 'sellall' and len(args) == 1:
                ticker = args[0].upper()
                success, msg = self.account.sellall(ticker)
                self.print_output(msg, error=not success)
            elif cmd == 'short' and len(args) == 2:
                a1, a2 = args[0], args[1]
                if a1.replace('.', '', 1).isdigit() or any(c.isdigit() for c in a1):
                    amount = parse_amount(a1)
                    ticker = a2.upper()
                else:
                    ticker = a1.upper()
                    amount = parse_amount(a2)
                success, msg = self.account.short(ticker, amount)
                self.print_output(msg, error=not success)
            elif cmd == 'cover' and len(args) == 2:
                a1, a2 = args[0], args[1]
                if a1.replace('.', '', 1).isdigit() or any(c.isdigit() for c in a1):
                    amount = parse_amount(a1)
                    ticker = a2.upper()
                else:
                    ticker = a1.upper()
                    amount = parse_amount(a2)
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
                self.account.save()
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

    def sort_by_column(self, col, force_desc=None, remember=True):
        # Get all items from the treeview
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        # Try to convert data to float for numeric columns
        def try_float(val):
            try:
                # Remove $ and % and commas for conversion
                return float(val.replace('$','').replace('%','').replace(',','').replace('(','-').replace(')',''))
            except Exception:
                return val
        # Determine sort order
        if force_desc is not None:
            reverse = force_desc
        else:
            reverse = self._sort_orders[col]
        data.sort(key=lambda t: try_float(t[0]), reverse=reverse)
        # Toggle sort order for next click
        self._sort_orders[col] = not reverse
        # Rearrange items in sorted positions
        for index, (val, k) in enumerate(data):
            self.tree.move(k, '', index)
        # Remember last sort
        if remember:
            self._last_sorted_col = col
            self._last_sort_desc = reverse

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry('1200x800')
    app = PaperTradingApp(root)
    root.mainloop() 
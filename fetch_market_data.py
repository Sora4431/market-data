import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import argparse


def _normalize_timezone(idx):
    """Strip timezone info from DatetimeIndex."""
    try:
        return idx.tz_localize(None)
    except TypeError:
        return idx.tz_convert(None)


def _prepare_hist_with_changes(tkr: yf.Ticker, colname: str, start_date, end_date) -> pd.DataFrame:
    """Fetch daily closes for a ticker and compute day-over-day changes.

    Changes are computed on actual trading days only (before any calendar expansion),
    so that e.g. Monday's change reflects Friday's close, not a weekend ffill.

    Returns a DataFrame indexed by 'YYYY-MM-DD' strings with columns:
      colname, {colname}_change, {colname}_pct
    """
    h = tkr.history(start=str(start_date), end=str(end_date + timedelta(days=1)))
    if h.empty or 'Close' not in h.columns:
        return pd.DataFrame(
            index=pd.Index([], name='date'),
            columns=[colname, f'{colname}_change', f'{colname}_pct']
        )

    h = h[['Close']].copy()
    h.index = _normalize_timezone(h.index)

    # Aggregate to calendar-date granularity (take last close of each day)
    dates = pd.to_datetime(h.index).date
    h = h.groupby(dates)['Close'].last().to_frame().rename(columns={'Close': colname})

    # Convert date-object index to 'YYYY-MM-DD' strings
    h.index = [str(d) for d in h.index]
    h.index.name = 'date'

    # Compute changes on trading days only
    prev = h[colname].shift(1)
    change = h[colname] - prev
    pct = (change / prev.replace(0, pd.NA)) * 100
    h[f'{colname}_change'] = change.fillna(0).round(4)
    h[f'{colname}_pct'] = pct.fillna(0).round(4)

    return h


def fetch_market_data(days: int = 14):
    """Fetch S&P 500, WTI Crude Oil, and US 10-Year Treasury Yield.

    Covers the last `days` calendar days. Non-trading days (weekends / holidays)
    are included in the CSV with prices forward-filled and changes zeroed out.
    A `market_open` flag (1/0) marks actual trading days.
    """
    end_date = datetime.now().date()
    # Fetch extra history so the first row in our window has a valid prev-day change
    fetch_start = end_date - timedelta(days=days + 14)

    sp500_tkr = yf.Ticker("^GSPC")  # S&P 500
    wti_tkr   = yf.Ticker("CL=F")   # WTI Crude Oil (NYMEX front-month futures)
    us10y_tkr = yf.Ticker("^TNX")   # US 10-Year Treasury Yield

    sp500_h = _prepare_hist_with_changes(sp500_tkr, 'sp500', fetch_start, end_date)
    wti_h   = _prepare_hist_with_changes(wti_tkr,   'wti',   fetch_start, end_date)
    us10y_h = _prepare_hist_with_changes(us10y_tkr, 'us10y', fetch_start, end_date)

    # Outer-join on date strings; each instrument keeps its own changes
    df = sp500_h.join(wti_h, how='outer').join(us10y_h, how='outer')
    df = df.sort_index()

    # Restrict to the target window (last `days` calendar days)
    window_start = str(end_date - timedelta(days=days - 1))
    window_end   = str(end_date)
    df = df[(df.index >= window_start) & (df.index <= window_end)]

    # Record which dates had real market data before we expand the calendar
    price_cols = ['sp500', 'wti', 'us10y']
    trading_dates = set(df.index[df[price_cols].notna().any(axis=1)])

    # Expand to every calendar day in the window
    full_index = pd.date_range(start=window_start, end=window_end, freq='D')
    full_index_str = full_index.strftime('%Y-%m-%d').tolist()
    df = df.reindex(full_index_str)
    df.index.name = 'date'

    # market_open flag: 1 = actual trading day, 0 = weekend / holiday
    df['market_open'] = df.index.map(lambda d: 1 if d in trading_dates else 0)

    # Forward-fill prices for non-trading days so the chart line is continuous
    for col in price_cols:
        df[col] = df[col].ffill()

    # Zero out changes on non-trading days (they were NaN after reindex)
    change_cols = ['sp500_change', 'sp500_pct', 'wti_change', 'wti_pct', 'us10y_change', 'us10y_pct']
    for col in change_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # Drop leading rows where all prices are still NaN (no data yet)
    df = df.dropna(subset=price_cols, how='all')

    # Round prices
    df['sp500']  = df['sp500'].round(2)
    df['wti']    = df['wti'].round(2)
    df['us10y']  = df['us10y'].round(4)

    df = df.reset_index()

    cols = [
        'date', 'sp500', 'wti', 'us10y',
        'sp500_change', 'sp500_pct',
        'wti_change',   'wti_pct',
        'us10y_change', 'us10y_pct',
        'market_open',
    ]
    df = df[cols]

    df.to_csv('market_data.csv', index=False)

    last_trading = df[df['market_open'] == 1]
    if not last_trading.empty:
        last = last_trading.iloc[-1]
        print(f"Updated up to:  {last['date']}")
        print(f"S&P 500:        ${last['sp500']:,.2f}  ({last['sp500_change']:+.2f}, {last['sp500_pct']:+.2f}%)")
        print(f"WTI Crude:      ${last['wti']:,.2f}/bbl  ({last['wti_change']:+.2f}, {last['wti_pct']:+.2f}%)")
        print(f"US 10Y Yield:   {last['us10y']:.4f}%  ({last['us10y_change']:+.4f}, {last['us10y_pct']:+.2f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch market data for recent calendar days")
    parser.add_argument('--days', type=int, default=14,
                        help='Number of recent calendar days to fetch (default: 14)')
    args = parser.parse_args()
    fetch_market_data(days=args.days)

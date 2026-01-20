import yfinance as yf
import pandas as pd
from datetime import datetime
import argparse
from datetime import timedelta

def _round_series(s):
    return s.round(2)

def _last_valid_close(tkr: yf.Ticker, period: str = "7d") -> float:
    """Return the most recent non-null Close from given period."""
    hist = tkr.history(period=period)
    closes = hist['Close'].dropna() if 'Close' in hist else pd.Series(dtype=float)
    if closes.empty:
        raise ValueError(f"No close price available in last {period} for {tkr.ticker}")
    return float(closes.iloc[-1])

def _compute_changes(df, price_col, change_col, pct_col):
    prev = df[price_col].shift(1)
    change = df[price_col] - prev
    pct = (change / prev.replace(0, pd.NA)) * 100
    df[change_col] = change.fillna(0).round(2)
    df[pct_col] = pct.fillna(0).round(2)

def _refresh_sp500_only(csv_path: str = 'market_data.csv'):
    """Re-fetch S&P 500 closes for the CSV date range and recompute its changes."""
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print("CSV not found; nothing to refresh.")
        return

    if df.empty or 'date' not in df.columns:
        print("CSV is empty or missing date column; nothing to refresh.")
        return

    date_series = pd.to_datetime(df['date'])
    start_date = date_series.min().date()
    end_date = date_series.max().date() + timedelta(days=1)

    sp500 = yf.Ticker("^GSPC")
    hist = sp500.history(start=str(start_date), end=str(end_date))
    idx = hist.index
    try:
        idx = idx.tz_localize(None)
    except Exception:
        pass
    hist['date'] = pd.to_datetime(idx).date
    hist = hist.groupby('date')['Close'].last().round(2).rename('sp500').reset_index()
    hist['date'] = pd.to_datetime(hist['date']).dt.strftime('%Y-%m-%d')

    df = df.merge(hist, on='date', how='left', suffixes=(None, '_new'))
    updated_rows = df['sp500_new'].notna().sum()
    df['sp500'] = df['sp500_new'].combine_first(df['sp500'])
    df = df.drop(columns=['sp500_new'])

    _compute_changes(df, 'sp500', 'sp500_change', 'sp500_pct')
    df.to_csv(csv_path, index=False)

    print(f"Refreshed S&P 500 for {updated_rows} dates between {start_date} and {end_date - timedelta(days=1)}")

def fetch_market_data(days: int = 1, refresh: bool = False):
    """日経平均、S&P 500、金価格を取得してCSVに保存

    days=1 の場合は最新終値のみを追記。
    days>1 または refresh=True の場合は直近 days 日分の終値を取得し、CSVを更新（上書き）。
    """

    # データ取得クライアント
    nikkei = yf.Ticker("^N225")  # 日経平均
    sp500 = yf.Ticker("^GSPC")   # S&P 500
    gold_usd_tkr = yf.Ticker("GC=F")  # 金（USD, COMEX先物）
    usd_jpy_tkr = yf.Ticker("USDJPY=X")   # 為替 USD/JPY

    if days > 1 or refresh:
        # 直近 days 日の終値を取得（各市場で日付単位に集約）
        def _prepare_hist(tkr: yf.Ticker, colname: str):
            h = tkr.history(period=f"{days}d")[['Close']]
            idx = h.index
            try:
                idx = idx.tz_localize(None)
            except Exception:
                pass
            h['date'] = pd.to_datetime(idx).date
            h = h.groupby('date')['Close'].last().to_frame().rename(columns={'Close': colname})
            return h

        nikkei_hist = _prepare_hist(nikkei, 'nikkei_225')
        sp500_hist = _prepare_hist(sp500, 'sp500')
        xau_usd_hist = _prepare_hist(gold_usd_tkr, 'xau_usd')
        usd_jpy_hist = _prepare_hist(usd_jpy_tkr, 'usd_jpy')

        # 日付（date型）で外部結合し、重複のない行にする
        df = nikkei_hist.join(sp500_hist, how='outer').join(xau_usd_hist, how='outer').join(usd_jpy_hist, how='outer')
        df = df.sort_index()
        df = df.rename_axis('date').reset_index()
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        # 直近 days 日（カレンダー日）のみに制限
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)
        df['_date_obj'] = pd.to_datetime(df['date']).dt.date
        df = df[(df['_date_obj'] >= start_date) & (df['_date_obj'] <= end_date)].drop(columns=['_date_obj'])

        # 円建て金価格を算出（ffill前に作成して連続埋め可能に）
        if 'xau_usd' in df.columns and 'usd_jpy' in df.columns:
            df['gold_jpy'] = (df['xau_usd'] * df['usd_jpy']).round(2)

        # 欠損を前日値で補完（グラフの線が途切れないように）
        full_index = pd.date_range(start=start_date, end=end_date, freq='D').strftime('%Y-%m-%d')
        df = df.set_index('date').reindex(full_index)
        df.index.name = 'date'
        for col in ['nikkei_225', 'sp500', 'gold_jpy']:
            if col in df.columns:
                df[col] = df[col].ffill()
        # すべての価格が欠損の行は削除（存在する列のみで判定）
        subset_cols = [c for c in ['nikkei_225', 'sp500', 'gold_jpy'] if c in df.columns]
        if subset_cols:
            df = df.dropna(subset=subset_cols, how='all')
        df = df.reset_index().rename(columns={'index': 'date'})

        # 少数を丸める
        for col in ['nikkei_225', 'sp500', 'gold_jpy']:
            if col in df.columns:
                df[col] = _round_series(df[col])

        # 変化量・変化率を計算
        _compute_changes(df, 'nikkei_225', 'nikkei_change', 'nikkei_pct')
        _compute_changes(df, 'sp500', 'sp500_change', 'sp500_pct')
        _compute_changes(df, 'gold_jpy', 'gold_change', 'gold_pct')

        # 列順を既存形式に合わせる
        cols = ['date', 'nikkei_225', 'sp500', 'gold_jpy',
                'nikkei_change', 'nikkei_pct',
                'sp500_change', 'sp500_pct',
                'gold_change', 'gold_pct']
        # 余分な中間列を削除
        df = df[cols]

        # 上書き保存
        df.to_csv('market_data.csv', index=False)

        # 最終行でサマリ表示
        last = df.iloc[-1]
        print(f"Updated up to: {last['date']}")
        print(f"Nikkei 225: ¥{last['nikkei_225']:,.2f} ({last['nikkei_change']:+.2f}, {last['nikkei_pct']:+.2f}%)")
        print(f"S&P 500: ${last['sp500']:,.2f} ({last['sp500_change']:+.2f}, {last['sp500_pct']:+.2f}%)")
        print(f"Gold: ¥{last['gold_jpy']:,.2f}/oz ({last['gold_change']:+.2f}, {last['gold_pct']:+.2f}%)")
        return

    # 最新1日の終値を取得して追記
    today = datetime.now().strftime('%Y-%m-%d')
    nikkei_price = _last_valid_close(nikkei, period="7d")
    sp500_price = _last_valid_close(sp500, period="10d")  # US 3-day weekends need a longer lookback
    # 最新1日の金価格（円建て）を算出
    xau_usd_price = _last_valid_close(gold_usd_tkr, period="7d")
    usd_jpy_price = _last_valid_close(usd_jpy_tkr, period="7d")
    gold_price = float(xau_usd_price) * float(usd_jpy_price)

    # 既存のCSVを読み込み
    try:
        df = pd.read_csv('market_data.csv')
        # 旧CSVから円建てへ移行
        if 'gold_usd' in df.columns and 'gold_jpy' not in df.columns:
            try:
                min_date = pd.to_datetime(df['date']).min().date()
                max_date = pd.to_datetime(df['date']).max().date()
                usd_jpy = yf.Ticker("USDJPY=X").history(start=str(min_date), end=str(max_date + pd.Timedelta(days=1)))
                idx = usd_jpy.index
                try:
                    idx = idx.tz_localize(None)
                except Exception:
                    pass
                usd_jpy['date'] = pd.to_datetime(idx).date
                usd_jpy = usd_jpy.groupby('date')['Close'].last().to_frame().rename(columns={'Close': 'usd_jpy'})
                map_df = usd_jpy.reset_index()
                df['date_obj'] = pd.to_datetime(df['date']).dt.date
                df = df.merge(map_df, left_on='date_obj', right_on='date', how='left', suffixes=(None, '_fx'))
                df['gold_jpy'] = (df['gold_usd'] * df['usd_jpy']).round(2)
                df = df.drop(columns=['date_obj', 'date_fx', 'usd_jpy'])
                # 円建てで金の変化量を再計算
                _compute_changes(df, 'gold_jpy', 'gold_change', 'gold_pct')
                df = df.drop(columns=['gold_usd'])
            except Exception:
                df = df.rename(columns={'gold_usd': 'gold_jpy'})

        if 'gold_usd' in df.columns and 'gold_jpy' not in df.columns:
            try:
                min_date = pd.to_datetime(df['date']).min().date()
                max_date = pd.to_datetime(df['date']).max().date()
                usd_jpy = usd_jpy_tkr.history(start=str(min_date), end=str(max_date + pd.Timedelta(days=1)))
                idx = usd_jpy.index
                try:
                    idx = idx.tz_localize(None)
                except Exception:
                    pass
                usd_jpy['date'] = pd.to_datetime(idx).date
                usd_jpy = usd_jpy.groupby('date')['Close'].last().to_frame().rename(columns={'Close': 'usd_jpy'})
                map_df = usd_jpy.reset_index()
                df['date_obj'] = pd.to_datetime(df['date']).dt.date
                df = df.merge(map_df, left_on='date_obj', right_on='date', how='left', suffixes=(None, '_fx'))
                df['gold_jpy'] = (df['gold_usd'] * df['usd_jpy']).round(2)
                df = df.drop(columns=['date_obj', 'date_fx', 'usd_jpy'])
                _compute_changes(df, 'gold_jpy', 'gold_change', 'gold_pct')
                df = df.drop(columns=['gold_usd'])
            except Exception:
                df = df.rename(columns={'gold_usd': 'gold_jpy'})

        if len(df) > 0:
            prev = df.iloc[-1]
            nikkei_change = float(nikkei_price) - float(prev['nikkei_225'])
            sp500_change = float(sp500_price) - float(prev['sp500'])
            gold_change = float(gold_price) - float(prev['gold_jpy'])
            nikkei_pct = (nikkei_change / float(prev['nikkei_225'])) * 100 if float(prev['nikkei_225']) != 0 else 0
            sp500_pct = (sp500_change / float(prev['sp500'])) * 100 if float(prev['sp500']) != 0 else 0
            gold_pct = (gold_change / float(prev['gold_jpy'])) * 100 if float(prev['gold_jpy']) != 0 else 0
        else:
            nikkei_change = sp500_change = gold_change = 0.0
            nikkei_pct = sp500_pct = gold_pct = 0.0
    except FileNotFoundError:
        df = pd.DataFrame()
        nikkei_change = sp500_change = gold_change = 0.0
        nikkei_pct = sp500_pct = gold_pct = 0.0

    new_data = pd.DataFrame({
        'date': [today],
        'nikkei_225': [round(float(nikkei_price), 2)],
        'sp500': [round(float(sp500_price), 2)],
        'gold_jpy': [round(float(gold_price), 2)],
        'nikkei_change': [round(float(nikkei_change), 2)],
        'nikkei_pct': [round(float(nikkei_pct), 2)],
        'sp500_change': [round(float(sp500_change), 2)],
        'sp500_pct': [round(float(sp500_pct), 2)],
        'gold_change': [round(float(gold_change), 2)],
        'gold_pct': [round(float(gold_pct), 2)]
    })

    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv('market_data.csv', index=False)

    print(f"Updated: {today}")
    print(f"Nikkei 225: ¥{float(nikkei_price):,.2f} ({nikkei_change:+.2f}, {nikkei_pct:+.2f}%)")
    print(f"S&P 500: ${float(sp500_price):,.2f} ({sp500_change:+.2f}, {sp500_pct:+.2f}%)")
    print(f"Gold: ¥{float(gold_price):,.2f}/oz ({gold_change:+.2f}, {gold_pct:+.2f}%)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch market data for recent days")
    parser.add_argument('--days', type=int, default=1, help='Number of recent days to fetch (default: 1)')
    parser.add_argument('--refresh', action='store_true', help='Overwrite CSV with last N days instead of appending')
    parser.add_argument('--ffill', action='store_true', help='Forward-fill missing non-trading days to keep continuous dates')
    parser.add_argument('--fix-sp500', action='store_true', help='Re-fetch S&P 500 for existing CSV date range and overwrite that column')
    args = parser.parse_args()
    # pass ffill flag via function attribute to avoid changing signature significantly
    fetch_market_data._ffill = args.ffill
    if args.fix_sp500:
        _refresh_sp500_only()
    else:
        fetch_market_data(days=args.days, refresh=args.refresh)

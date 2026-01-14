import yfinance as yf
import pandas as pd
from datetime import datetime

def fetch_market_data():
    """日経平均、S&P 500、金価格を取得してCSVに保存"""
    
    # 現在の日付
    today = datetime.now().strftime('%Y-%m-%d')
    
    # データ取得
    nikkei = yf.Ticker("^N225")  # 日経平均
    sp500 = yf.Ticker("^GSPC")   # S&P 500
    gold = yf.Ticker("GC=F")     # 金先物
    
    # 最新の終値を取得
    nikkei_price = nikkei.history(period="1d")['Close'].iloc[-1]
    sp500_price = sp500.history(period="1d")['Close'].iloc[-1]
    gold_price = gold.history(period="1d")['Close'].iloc[-1]
    
    # 既存のCSVを読み込み
    try:
        df = pd.read_csv('market_data.csv')
        
        # 前日データを取得
        if len(df) > 0:
            prev = df.iloc[-1]
            nikkei_change = nikkei_price - prev['nikkei_225']
            sp500_change = sp500_price - prev['sp500']
            gold_change = gold_price - prev['gold_usd']
            
            nikkei_pct = (nikkei_change / prev['nikkei_225']) * 100
            sp500_pct = (sp500_change / prev['sp500']) * 100
            gold_pct = (gold_change / prev['gold_usd']) * 100
        else:
            nikkei_change = sp500_change = gold_change = 0
            nikkei_pct = sp500_pct = gold_pct = 0
    except FileNotFoundError:
        df = pd.DataFrame()
        nikkei_change = sp500_change = gold_change = 0
        nikkei_pct = sp500_pct = gold_pct = 0
    
    # 新しいデータを追加
    new_data = pd.DataFrame({
        'date': [today],
        'nikkei_225': [round(nikkei_price, 2)],
        'nikkei_change': [round(nikkei_change, 2)],
        'nikkei_pct': [round(nikkei_pct, 2)],
        'sp500': [round(sp500_price, 2)],
        'sp500_change': [round(sp500_change, 2)],
        'sp500_pct': [round(sp500_pct, 2)],
        'gold_usd': [round(gold_price, 2)],
        'gold_change': [round(gold_change, 2)],
        'gold_pct': [round(gold_pct, 2)]
    })
    
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv('market_data.csv', index=False)
    
    print(f"Updated: {today}")
    print(f"Nikkei 225: ¥{nikkei_price:,.2f} ({nikkei_change:+.2f}, {nikkei_pct:+.2f}%)")
    print(f"S&P 500: ${sp500_price:,.2f} ({sp500_change:+.2f}, {sp500_pct:+.2f}%)")
    print(f"Gold: ${gold_price:,.2f}/oz ({gold_change:+.2f}, {gold_pct:+.2f}%)")

if __name__ == "__main__":
    fetch_market_data()

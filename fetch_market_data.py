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
    
    # データフレーム作成
    new_data = pd.DataFrame({
        'date': [today],
        'nikkei_225': [round(nikkei_price, 2)],
        'sp500': [round(sp500_price, 2)],
        'gold_usd': [round(gold_price, 2)]
    })
    
    # CSVファイルに追記
    try:
        df = pd.read_csv('market_data.csv')
        df = pd.concat([df, new_data], ignore_index=True)
    except FileNotFoundError:
        df = new_data
    
    df.to_csv('market_data.csv', index=False)
    
    print(f"Updated: {today}")
    print(f"Nikkei 225: ¥{nikkei_price:,.2f}")
    print(f"S&P 500: ${sp500_price:,.2f}")
    print(f"Gold: ${gold_price:,.2f}/oz")

if __name__ == "__main__":
    fetch_market_data()
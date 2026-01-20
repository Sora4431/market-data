import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def main():
    df = pd.read_csv('market_data.csv')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Use last 14 entries just in case CSV has more
    df = df.tail(14)

    # Create 3 separate charts
    charts = [
        {
            'col': 'nikkei_225',
            'title': 'Nikkei 225 (Last 14 Days)',
            'ylabel': 'Price (JPY)',
            'color': '#1f77b4',
            'filename': 'chart_nikkei.svg'
        },
        {
            'col': 'sp500',
            'title': 'S&P 500 (Last 14 Days)',
            'ylabel': 'Index',
            'color': '#ff7f0e',
            'filename': 'chart_sp500.svg'
        },
        {
            'col': 'gold_jpy',
            'title': 'Gold Price in JPY (Last 14 Days)',
            'ylabel': 'Price (JPY per Troy Ounce)',
            'color': '#2ca02c',
            'filename': 'chart_gold.svg'
        }
    ]

    for chart in charts:
        col = chart['col']
        if col not in df.columns:
            continue

        plt.figure(figsize=(10, 5))
        plt.plot(df['date'], df[col], color=chart['color'], linewidth=2, marker='o', markersize=4)
        plt.title(chart['title'], fontsize=14, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel(chart['ylabel'], fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save to SVG for embedding in GitHub README
        plt.savefig(chart['filename'], format='svg', bbox_inches='tight')
        plt.close()

    print("3つのグラフを作成しました:")
    print("- chart_nikkei.svg (日経平均)")
    print("- chart_sp500.svg (S&P 500)")
    print("- chart_gold.svg (金価格)")

if __name__ == '__main__':
    main()
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def main():
    df = pd.read_csv('market_data.csv')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Use last 14 entries just in case CSV has more
    df = df.tail(14).reset_index(drop=True)

    # Create 3 separate charts
    charts = [
        {
            'col': 'nikkei_225',
            'change_col': 'nikkei_change',
            'title': 'Nikkei 225 (Last 14 Days)',
            'ylabel': 'Price (JPY)',
            'color': '#1f77b4',
            'filename': 'chart_nikkei.svg'
        },
        {
            'col': 'sp500',
            'change_col': 'sp500_change',
            'title': 'S&P 500 (Last 14 Days)',
            'ylabel': 'Index',
            'color': '#ff7f0e',
            'filename': 'chart_sp500.svg'
        },
        {
            'col': 'gold_jpy',
            'change_col': 'gold_change',
            'title': 'Gold Price in JPY (Last 14 Days)',
            'ylabel': 'Price (JPY per Troy Ounce)',
            'color': '#2ca02c',
            'filename': 'chart_gold.svg'
        }
    ]

    for chart in charts:
        col = chart['col']
        change_col = chart['change_col']
        if col not in df.columns or change_col not in df.columns:
            continue

        # Identify holidays: weekends only (don't use zero change as holiday indicator)
        df['is_weekend'] = df['date'].dt.weekday.isin([5, 6])

        fig, ax = plt.subplots(figsize=(10, 5))

        # Highlight weekends (Saturday/Sunday) with light gray background
        for i, row in df.iterrows():
            weekday = row['date'].weekday()
            # 5=Saturday, 6=Sunday only
            if weekday in [5, 6]:
                ax.axvspan(row['date'] - pd.Timedelta(hours=12),
                          row['date'] + pd.Timedelta(hours=12),
                          color='lightgray', alpha=0.3, zorder=0)

        # Plot only working days (exclude weekends)
        working_days = df[~df['is_weekend']]

        ax.plot(working_days['date'], working_days[col],
                color=chart['color'], linewidth=2, marker='o', markersize=4)

        ax.set_title(chart['title'], fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel(chart['ylabel'], fontsize=12)
        ax.grid(True, alpha=0.3)
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
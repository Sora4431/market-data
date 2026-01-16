import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def main():
    df = pd.read_csv('market_data.csv')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Use last 14 entries just in case CSV has more
    df = df.tail(14)

    # Build indexed series to make lines comparable
    series_map = {}
    for col in ['nikkei_225', 'sp500', 'gold_jpy']:
        if col in df.columns:
            base = df[col].iloc[0]
            if base and pd.notna(base) and float(base) != 0:
                series_map[col] = (df[col] / float(base)) * 100.0

    # Plot
    plt.figure(figsize=(9, 4.5))
    for col, label, color in [
        ('nikkei_225', 'Nikkei 225 (Indexed)', '#1f77b4'),
        ('sp500', 'S&P 500 (Indexed)', '#ff7f0e'),
        ('gold_jpy', 'Gold JPY (Indexed)', '#2ca02c'),
    ]:
        if col in series_map:
            plt.plot(df['date'], series_map[col], label=label, color=color, linewidth=2)

    plt.title('Market (Last 14 Days) — Indexed to 100')
    plt.xlabel('Date')
    plt.ylabel('Index (Base=100)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    # Save to SVG for embedding in GitHub README
    plt.savefig('chart.svg', format='svg')

if __name__ == '__main__':
    main()
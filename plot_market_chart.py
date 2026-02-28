import pandas as pd
import matplotlib.pyplot as plt


def main():
    df = pd.read_csv('market_data.csv')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df = df.tail(14).reset_index(drop=True)

    # Detect non-trading days: use market_open flag if present, else fall back to weekends
    if 'market_open' in df.columns:
        df['is_holiday'] = df['market_open'] == 0
    else:
        df['is_holiday'] = df['date'].dt.weekday >= 5

    charts = [
        {
            'col': 'sp500',
            'change_col': 'sp500_change',
            'title': 'S&P 500 (Last 14 Days)',
            'ylabel': 'Index',
            'color': '#1f77b4',
            'filename': 'chart_sp500.svg',
        },
        {
            'col': 'wti',
            'change_col': 'wti_change',
            'title': 'WTI Crude Oil (Last 14 Days)',
            'ylabel': 'Price (USD/bbl)',
            'color': '#d62728',
            'filename': 'chart_wti.svg',
        },
        {
            'col': 'us10y',
            'change_col': 'us10y_change',
            'title': 'US 10-Year Treasury Yield (Last 14 Days)',
            'ylabel': 'Yield (%)',
            'color': '#2ca02c',
            'filename': 'chart_us10y.svg',
        },
    ]

    for chart in charts:
        col = chart['col']
        change_col = chart['change_col']
        if col not in df.columns or change_col not in df.columns:
            print(f"Skipping {chart['filename']}: column '{col}' not found in CSV")
            continue

        fig, ax = plt.subplots(figsize=(10, 5))

        # Gray background for non-trading days (weekends + holidays)
        for _, row in df.iterrows():
            if row['is_holiday']:
                ax.axvspan(
                    row['date'] - pd.Timedelta(hours=12),
                    row['date'] + pd.Timedelta(hours=12),
                    color='lightgray', alpha=0.4, zorder=0,
                )

        # Plot trading days only
        trading_days = df[~df['is_holiday']]
        ax.plot(
            trading_days['date'], trading_days[col],
            color=chart['color'], linewidth=2, marker='o', markersize=4,
        )

        ax.set_title(chart['title'], fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel(chart['ylabel'], fontsize=12)
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        plt.savefig(chart['filename'], format='svg', bbox_inches='tight')
        plt.close()
        print(f"Saved {chart['filename']}")


if __name__ == '__main__':
    main()

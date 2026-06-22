import re
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ============================================
# CAPM AND BETA ESTIMATOR - MULTI-STOCK VERSION
# ============================================

market_ticker = "^GSPC"  # S&P 500 market benchmark
start_date = "2020-01-01"
end_date = "2025-01-01"

risk_free_rate = 0.045  # 4.5% annual risk-free rate assumption


def clean_filename(ticker):
    """Makes ticker safe to use as a file name."""
    return re.sub(r"[^A-Za-z0-9_]", "_", ticker)


def interpret_beta(beta):
    if beta > 1:
        return "More volatile than the market"
    elif beta < 1:
        return "Less volatile than the market"
    else:
        return "Moves almost exactly like the market"


def interpret_performance(stock_return, capm_return):
    if stock_return > capm_return:
        return "Outperformed CAPM expectation"
    else:
        return "Underperformed CAPM expectation"


# Ask user for stocks
tickers_input = input("Enter stock tickers separated by commas, e.g. AAPL, TSLA, MSFT: ")

stock_tickers = [
    ticker.strip().upper()
    for ticker in tickers_input.split(",")
    if ticker.strip()
]

if len(stock_tickers) == 0:
    print("No tickers entered. Using default stocks: AAPL, TSLA, MSFT, NVDA, AMZN")
    stock_tickers = ["AAPL", "TSLA", "MSFT", "NVDA", "AMZN"]


all_tickers = stock_tickers + [market_ticker]


print("\nDownloading market data...")

data = yf.download(
    all_tickers,
    start=start_date,
    end=end_date,
    auto_adjust=True,
    progress=False
)


# Extract closing prices
if isinstance(data.columns, pd.MultiIndex):
    prices = data["Close"]
else:
    prices = data


prices = prices.dropna(how="all")

if market_ticker not in prices.columns:
    raise ValueError("Market benchmark data was not downloaded correctly.")


# Calculate daily returns
returns = prices.pct_change().dropna()

market_returns = returns[market_ticker]


results = []


for stock_ticker in stock_tickers:
    if stock_ticker not in returns.columns:
        print(f"\nSkipping {stock_ticker}: No data found.")
        continue

    stock_returns = returns[stock_ticker]

    # Align stock and market returns
    aligned_returns = pd.concat(
        [stock_returns, market_returns],
        axis=1
    ).dropna()

    aligned_returns.columns = ["stock", "market"]

    stock_returns = aligned_returns["stock"]
    market_returns_aligned = aligned_returns["market"]

    # Beta calculation
    covariance_matrix = np.cov(stock_returns, market_returns_aligned)

    cov_stock_market = covariance_matrix[0, 1]
    var_market = covariance_matrix[1, 1]

    beta = cov_stock_market / var_market

    # Alpha calculation
    alpha_daily = stock_returns.mean() - beta * market_returns_aligned.mean()
    alpha_annual = alpha_daily * 252

    # Annualized returns
    stock_annual_return = stock_returns.mean() * 252
    market_annual_return = market_returns_aligned.mean() * 252

    # CAPM expected return
    capm_expected_return = risk_free_rate + beta * (
        market_annual_return - risk_free_rate
    )

    beta_interpretation = interpret_beta(beta)
    performance_interpretation = interpret_performance(
        stock_annual_return,
        capm_expected_return
    )

    results.append({
        "Stock": stock_ticker,
        "Beta": beta,
        "Annual Alpha": alpha_annual,
        "Stock Annual Return": stock_annual_return,
        "Market Annual Return": market_annual_return,
        "Risk-Free Rate": risk_free_rate,
        "CAPM Expected Return": capm_expected_return,
        "Beta Interpretation": beta_interpretation,
        "Performance Interpretation": performance_interpretation
    })

    # Plot stock returns vs market returns
    plt.figure(figsize=(10, 6))
    plt.scatter(market_returns_aligned, stock_returns, alpha=0.5)

    x = market_returns_aligned
    y = beta * x + alpha_daily

    plt.plot(x, y)
    plt.title(f"{stock_ticker} Returns vs Market Returns")
    plt.xlabel("Market Daily Returns")
    plt.ylabel(f"{stock_ticker} Daily Returns")
    plt.grid(True)

    plot_filename = f"{clean_filename(stock_ticker)}_capm_regression_plot.png"
    plt.savefig(plot_filename, dpi=300)
    plt.show()

    print(f"\nSaved graph: {plot_filename}")


# Convert results into a table
results_df = pd.DataFrame(results)


if results_df.empty:
    print("\nNo valid stock results were calculated.")
else:
    # Format output for terminal
    display_df = results_df.copy()

    percentage_columns = [
        "Annual Alpha",
        "Stock Annual Return",
        "Market Annual Return",
        "Risk-Free Rate",
        "CAPM Expected Return"
    ]

    display_df["Beta"] = display_df["Beta"].map(lambda x: f"{x:.4f}")

    for col in percentage_columns:
        display_df[col] = display_df[col].map(lambda x: f"{x:.2%}")

    print("\n========== CAPM RESULTS TABLE ==========")
    print(display_df.to_string(index=False))

    # Save raw numeric results to CSV
    results_df.to_csv("capm_results.csv", index=False)

    print("\nSaved results table: capm_results.csv")

    print("\n========== FINAL CONCLUSION ==========")

    highest_beta_stock = results_df.loc[results_df["Beta"].idxmax()]
    lowest_beta_stock = results_df.loc[results_df["Beta"].idxmin()]

    print(
        f"The stock with the highest beta is {highest_beta_stock['Stock']} "
        f"with a beta of {highest_beta_stock['Beta']:.2f}."
    )

    print(
        f"The stock with the lowest beta is {lowest_beta_stock['Stock']} "
        f"with a beta of {lowest_beta_stock['Beta']:.2f}."
    )

    print(
        "\nA higher beta means the stock is more sensitive to market movements. "
        "A lower beta means the stock is less sensitive to market movements."
    )
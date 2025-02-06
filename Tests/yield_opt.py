import json
import pandas as pd
from scipy.optimize import linprog
import numpy as np

# Sample balance data (replace with API call if needed)
balance_data = {
    "curve": [
        {"chain_name": "eth-mainnet", "balance": "35.20781919682791", "contract_name": "USD Coin",
         "contract_ticker_symbol": "USDC", "quote_currency": "USD", "quote": 3.52043e-05},
        {"chain_name": "eth-mainnet", "balance": "30815200764844.85", "contract_name": "Dai Stablecoin",
         "contract_ticker_symbol": "DAI", "quote_currency": "USD", "quote": 3.08152e-05},
        {"chain_name": "eth-mainnet", "balance": "34.00571640833528", "contract_name": "Tether USD",
         "contract_ticker_symbol": "USDT", "quote_currency": "USD", "quote": 3.4008095e-05}
    ],
    "aave": [],
    "lido": [
        {"chain_name": "eth-mainnet", "balance": "999999999999999", "contract_name": "Liquid staked Ether 2.0",
         "contract_ticker_symbol": "stETH", "quote_currency": "USD", "quote": 3.258454}
    ]
}

# Function to parse balance data and sum per protocol
def parse_balance_data(data):
    portfolio = {}
    for protocol, assets in data.items():
        total_balance = 0
        for asset in assets:
            total_balance += float(asset["balance"]) * asset["quote"]  # Convert to USD equivalent
        if total_balance > 0:
            portfolio[protocol.capitalize()] = total_balance
    return pd.DataFrame(list(portfolio.items()), columns=["protocol", "total_balance"])

# Convert to DataFrame (protocol-level balance)
portfolio_df = parse_balance_data(balance_data)
print("\nParsed Portfolio Data:")
print(portfolio_df)

# Simulated yield rates (APR per year) at the **protocol level**
yield_data = pd.DataFrame([
    {"protocol": "Curve", "apr": 0.05, "liquidity": 500_000},
    {"protocol": "Lido", "apr": 0.038, "liquidity": 1_000_000},
])

# Convert APR to daily return
yield_data["daily_return"] = yield_data["apr"] / 365

print("\nYield Data with Daily Returns:")
print(yield_data)

# Merge portfolio and yield data on protocol
merged_df = pd.merge(portfolio_df, yield_data, on=["protocol"], how="inner")

# ✅ Normalize balance values (to avoid large numbers)
merged_df["normalized_balance"] = merged_df["total_balance"] / 1e6  # Convert to millions for better scaling

# Optimization setup
num_protocols = len(merged_df)
c = -merged_df["daily_return"].values  # Negative because we maximize returns

# ✅ Use inequality constraint instead of equality
A_ub = [np.ones(num_protocols)]  # "≤" constraint: total allocation ≤ total portfolio balance
b_ub = [sum(merged_df["normalized_balance"])]  # Use normalized balance

# ✅ Adjust bounds: allocation must be within available liquidity and balance
bounds = [
    (0, min(row["liquidity"], row["normalized_balance"])) if row["liquidity"] > 0 else (0, 0)
    for _, row in merged_df.iterrows()
]

# Solve Linear Programming problem
result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")

# ✅ Store optimal allocations safely
if result.success and result.x is not None:
    merged_df["optimal_allocation"] = result.x * 1e6  # Convert back to original scale
    print("\nOptimized Portfolio Allocation:")
    print(merged_df[["protocol", "optimal_allocation"]])
else:
    print("\n❌ Optimization failed. Defaulting to current allocations.")
    merged_df["optimal_allocation"] = merged_df["total_balance"]  # Keep current allocation

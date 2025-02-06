import pulp
import json

# =============================================================================
# Step 1: Define Data and Assumptions
# =============================================================================
print("Step 1: Defining Data and Assumptions...\n")

# Provided data: "quote" is the total USD value of the tokens held in each protocol.
data = {
    "curve": [
        {
            "chain_name": "eth-mainnet",
            "balance": "32.47227836077262",
            "contract_name": "USD Coin",
            "contract_ticker_symbol": "USDC",
            "quote_currency": "USD",
            "quote": 3.2475527
        },
        {
            "chain_name": "eth-mainnet",
            "balance": "33239333628248.385",
            "contract_name": "Dai Stablecoin",
            "contract_ticker_symbol": "DAI",
            "quote_currency": "USD",
            "quote": 3.3239332
        },
        {
            "chain_name": "eth-mainnet",
            "balance": "34.31845842695606",
            "contract_name": "Tether USD",
            "contract_ticker_symbol": "USDT",
            "quote_currency": "USD",
            "quote": 3.4316057
        }
    ],
    "aave": [],
    "lido": [
        {
            "chain_name": "eth-mainnet",
            "balance": "999999999999999",
            "contract_name": "Liquid staked Ether 2.0",
            "contract_ticker_symbol": "stETH",
            "quote_currency": "USD",
            "quote": 3.2615054
        }
    ]
}

# Assumed APYs per protocol
assumed_apy = {
    "curve": 0.05,  # 5% APY
    "aave": 0.05,   # 5% APY (no data, so it's arbitrary)
    "lido": 0.05    # 5% APY
}

# Risk penalties per protocol (higher penalty = lower effective yield)
assumed_risk_penalty = {
    "curve": 0.0,
    "aave": 0.0,
    "lido": 0.0
}

# Liquidity penalties per protocol (higher penalty = lower effective yield)
assumed_liquidity_penalty = {
    "curve": 0.0,
    "aave": 0.0,
    "lido": 0.0
}

# Compute the effective yield for each protocol
effective_yield = {}
for protocol in assumed_apy:
    effective_yield[protocol] = assumed_apy[protocol] - \
        (assumed_risk_penalty[protocol] + assumed_liquidity_penalty[protocol])

# =============================================================================
# Step 2: Compute Total USD Value per Protocol
# =============================================================================
print("\nStep 2: Computing Total USD Value per Protocol...\n")

protocol_values = {}
for protocol, assets in data.items():
    total_value = 0.0
    for asset in assets:
        asset_value = float(asset["quote"])  # Use the USD value directly
        total_value += asset_value
    protocol_values[protocol] = total_value

# Print current balances (Before Optimization)
print("Current USD balance per protocol (Before Optimization):")
for protocol, value in protocol_values.items():
    print(f"  {protocol}: {value:.8f} USD")

# Total available capital = sum of all protocol balances
total_capital = sum(protocol_values.values())
print(f"\nTotal Capital Available: {total_capital:.8f} USD")

# =============================================================================
# Step 3: Set Up the Yield Optimization Problem
# =============================================================================
print("\nStep 3: Setting Up the Yield Optimization Problem...\n")

problem = pulp.LpProblem("Yield_Optimization", pulp.LpMaximize)

# Diversification constraint: Max allocation per protocol (50% of total capital)
max_allocation = 0.5 * total_capital

# Create decision variables for each protocol (USD allocation)
allocations = {}
for protocol in effective_yield:
    allocations[protocol] = pulp.LpVariable(
        f"allocation_{protocol}",
        lowBound=0,
        upBound=max_allocation,
        cat="Continuous"
    )

# Objective function: Maximize total annual yield (Effective Yield * Allocation)
problem += pulp.lpSum([effective_yield[p] * allocations[p] for p in allocations]), "Total_Annual_Yield"

# Constraint: Total allocation must equal the total capital available
problem += pulp.lpSum([allocations[p] for p in allocations]) == total_capital, "Total_Capital_Constraint"

# =============================================================================
# Step 4: Solve the Optimization Problem
# =============================================================================
print("\nStep 4: Solving the Optimization Problem...\n")
problem.solve()
print("Optimization Status:", pulp.LpStatus[problem.status])

# =============================================================================
# Step 5: Display Before and After Pool Balances
# =============================================================================
print("\nStep 5: Before and After Pool Balances:")

# Retrieve optimal allocations
optimized_allocations = {protocol: allocations[protocol].varValue for protocol in allocations}

# Print Before and After balances side-by-side
print("\nComparison of Pool Balances (Before vs. After):")
print(f"{'Protocol':<10}{'Before (USD)':>20}{'After (USD)':>20}{'Change (USD)':>20}")
print("="*70)

for protocol in protocol_values:
    before_balance = protocol_values[protocol]
    after_balance = optimized_allocations.get(protocol, 0.0)
    delta = after_balance - before_balance  # Change in balance
    print(f"{protocol:<10}{before_balance:>20.8f}{after_balance:>20.8f}{delta:>20.8f}")

# =============================================================================
# Step 6: Compute and Display Total Optimized Yield
# =============================================================================
total_annual_yield = sum(effective_yield[p] * optimized_allocations[p] for p in optimized_allocations)
print(f"\nTotal Optimized Annual Yield: {total_annual_yield:.8f} USD per year")

balance_comparison = {
    "before": protocol_values,  # Before optimization
    "after": optimized_allocations,  # After optimization
    "change": {protocol: optimized_allocations.get(protocol, 0.0) - protocol_values[protocol] for protocol in protocol_values},
    "total_optimized_yield": total_annual_yield
}

# Return JSON output
balance_comparison_json = json.dumps(balance_comparison, indent=4)
print(balance_comparison_json)

import pulp
import json

# =============================================================================
# Step 1: Define Data and Assumptions
# =============================================================================
def yield_opt_o3(data):

    print("Step 1: Defining Data and Assumptions...\n")

    # Provided data: "quote" is the total USD value of the tokens held in each protocol.
    data = {
        "curve": [
            {
                "chain_name": "eth-mainnet",
                "balance": "0",
                "contract_name": "USD Coin",
                "contract_ticker_symbol": "USDC",
                "quote_currency": "USD",
                "quote": 0
            },
            {
                "chain_name": "eth-mainnet",
                "balance": "0",
                "contract_name": "Dai Stablecoin",
                "contract_ticker_symbol": "DAI",
                "quote_currency": "USD",
                "quote": 0
            },
            {
                "chain_name": "eth-mainnet",
                "balance": "0",
                "contract_name": "Tether USD",
                "contract_ticker_symbol": "USDT",
                "quote_currency": "USD",
                "quote": 0
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
        "curve": 0.15,  # 5% APY
        "aave": 0.05,   # 5% APY (dummy value for protocols with no data)
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

    # Transaction costs (dummy values): separate costs for deposit and withdrawal per protocol
    deposit_cost = {
        "curve": 0.01,  # 1% cost on deposit
        "aave": 0.02,   # 2% cost on deposit
        "lido": 0.015   # 1.5% cost on deposit
    }

    withdrawal_cost = {
        "curve": 0.01,  # 1% cost on withdrawal
        "aave": 0.02,   # 2% cost on withdrawal
        "lido": 0.015   # 1.5% cost on withdrawal
    }

    # Compute the effective yield for each protocol (after risk & liquidity adjustments)
    effective_yield = {}
    for protocol in assumed_apy:
        effective_yield[protocol] = assumed_apy[protocol] - (assumed_risk_penalty[protocol] + assumed_liquidity_penalty[protocol])

    print("Assumed APYs:")
    for protocol, apy in assumed_apy.items():
        print(f"  {protocol}: {apy * 100:.2f}%")

    print("\nEffective Yields (after risk & liquidity adjustments):")
    for protocol, eff in effective_yield.items():
        print(f"  {protocol}: {eff * 100:.2f}%")

    print("\nDeposit Costs:")
    for protocol, cost in deposit_cost.items():
        print(f"  {protocol}: {cost * 100:.2f}%")

    print("\nWithdrawal Costs:")
    for protocol, cost in withdrawal_cost.items():
        print(f"  {protocol}: {cost * 100:.2f}%")

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

    # Create decision variables for deposit (d_plus) and withdrawal (d_minus) amounts.
    # They capture the extra amount to deposit (if allocation > current balance)
    # or the amount to withdraw (if allocation < current balance).
    d_plus = {}
    d_minus = {}
    for protocol in effective_yield:
        d_plus[protocol] = pulp.LpVariable(f"d_plus_{protocol}", lowBound=0, cat="Continuous")
        d_minus[protocol] = pulp.LpVariable(f"d_minus_{protocol}", lowBound=0, cat="Continuous")
        # Constrain net reallocation: new allocation - current balance = deposit amount - withdrawal amount
        problem += allocations[protocol] - protocol_values[protocol] == d_plus[protocol] - d_minus[protocol], f"realloc_balance_{protocol}"

    # New objective function: maximize total yield minus transaction costs.
    # For each protocol, if funds are deposited, we pay deposit_cost; if funds are withdrawn, we pay withdrawal_cost.
    problem += (
        pulp.lpSum([effective_yield[p] * allocations[p] for p in effective_yield])
        - pulp.lpSum([deposit_cost[p] * d_plus[p] + withdrawal_cost[p] * d_minus[p] for p in effective_yield])
    ), "Total_Annual_Yield_Net"

    # Constraint: Total allocation must equal the total capital available.
    problem += pulp.lpSum([allocations[p] for p in allocations]) == total_capital, "Total_Capital_Constraint"

    # =============================================================================
    # Step 4: Solve the Optimization Problem
    # =============================================================================
    print("\nStep 4: Solving the Optimization Problem...\n")
    problem.solve()
    print("Optimization Status:", pulp.LpStatus[problem.status])

    # =============================================================================
    # Step 5: Display Before and After Pool Balances (Return JSON)
    # =============================================================================
    print("\nStep 5: Before and After Pool Balances (JSON Output):")

    # Retrieve optimal allocations
    optimized_allocations = {protocol: allocations[protocol].varValue for protocol in allocations}

    # Prepare JSON response for before and after balances
    balance_comparison = {
        "before": protocol_values,  # Before optimization
        "after": optimized_allocations,  # After optimization
        "change": {protocol: optimized_allocations.get(protocol, 0.0) - protocol_values[protocol]
                for protocol in protocol_values},
        "total_optimized_yield": sum(effective_yield[p] * optimized_allocations[p] for p in optimized_allocations)
    }

    balance_comparison_json = json.dumps(balance_comparison, indent=4)
    print(balance_comparison)
    return(balance_comparison_json)

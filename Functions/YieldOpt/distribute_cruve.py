import pulp
import json

def yield_opt_allocation(total_capital, risk_profile):
    """
    Given a total amount of capital and a risk profile, optimally allocate
    the capital among different protocols/pools to maximize yield while
    respecting per-pool maximum allocation constraints.
    
    :param total_capital: float, the amount of capital to be distributed
    :param risk_profile: str, either "stable" or "high-yield"
    :return: JSON string with allocation details
    """
    # 1. Define risk-penalty parameters based on the risk profile
    if risk_profile == "stable":
        # Penalize higher-risk pools more
        risk_penalty = {"4pool": 0.01, "USDC/USDM": 0.05, "USDC/MONEY": 0.07}
    else:  # "high-yield" or any other string implies riskier strategy
        # Lower risk penalties to favor higher yields
        risk_penalty = {"4pool": 0.00, "USDC/USDM": 0.02, "USDC/MONEY": 0.03}

    # 2. Base APYs for each pool
    base_apy = {
        "4pool": 0.0027,      # ~0.27% 
        "USDC/USDM": 0.0317,  # ~3.17%
        "USDC/MONEY": 0.0035  # ~0.35%
    }
    
    # 3. Liquidity or volume data (if emphasizing liquidity in a "stable" profile)
    pool_volume = {
        "4pool": 1677000,  
        "USDC/USDM": 79255,
        "USDC/MONEY": 2259
    }
    
    # 4. Compute effective yield based on the risk profile logic
    #    - For "stable": use the pool volume (liquidity) as a factor, minus penalty.
    #    - For "high-yield": use the base APY as a factor, minus penalty.
    max_tvl = max(pool_volume.values())  # largest pool's TVL
    effective_yield = {}
    
    for pool in base_apy:
        if risk_profile == "stable":
            # Effective yield scales with TVL and subtracts risk penalty
            # Add a small constant to avoid zero
            effective_yield[pool] = ((pool_volume[pool] / float(max_tvl + 1))
                                     * (1 - risk_penalty[pool]) 
                                     + 0.0001)
        else:
            # Effective yield scales with base APY and subtracts risk penalty
            effective_yield[pool] = (base_apy[pool] 
                                     * (1 - risk_penalty[pool]) 
                                     + 0.0001)
    
    # 5. Create the optimization problem
    problem = pulp.LpProblem("Yield_Allocation_Optimization", pulp.LpMaximize)
    
    # 6. Define allocation variables with an upper bound (e.g. 50% per pool)
    max_allocation = 0.50 * total_capital  # max 50% of total for each pool
    allocations = {
        pool: pulp.LpVariable(f"alloc_{pool}", lowBound=0, upBound=max_allocation)
        for pool in effective_yield
    }
    
    # 7. Define the objective: maximize sum of (effective_yield * allocation)
    problem += pulp.lpSum(
        [effective_yield[p] * allocations[p] for p in allocations]
    ), "Maximize_Effective_Yield"
    
    # 8. Constrain the sum of all allocations not to exceed total capital
    problem += pulp.lpSum(allocations.values()) <= total_capital
    
    # 9. Solve the problem
    problem.solve()
    
    # 10. Extract results
    optimized_allocations = {pool: allocations[pool].varValue for pool in allocations}
    
    # 11. Calculate total optimized yield (annualized)
    total_optimized_yield = sum(
        effective_yield[p] * optimized_allocations[p] for p in optimized_allocations
    )
    
    # Prepare result for JSON
    result = {
        "total_capital": total_capital,
        "risk_profile": risk_profile,
        "allocations": optimized_allocations,
        "total_optimized_yield": total_optimized_yield
    }
    
    return json.dumps(result, indent=4)


# Example usage:
# if __name__ == "__main__":
#     sample_amount = 0.569851  # Example: user has 100k USD
#     # Try both risk profiles
#     print("=== Stable Risk Profile ===")
#     print(yield_opt_allocation(sample_amount, "stable"))
    
#     print("\n=== High-Yield Risk Profile ===")
#     print(yield_opt_allocation(sample_amount, "high-yield"))

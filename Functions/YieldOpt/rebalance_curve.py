import pulp
import json

def yield_opt_risk_profiles(data, risk_profile):
    # Define risk and liquidity penalties based on risk profile
    if risk_profile == "stable":
        risk_penalty = {"4pool": 0.01, "USDC/USDM": 0.05, "USDC/MONEY": 0.07}
    else:  # High-yield, riskier strategy
        risk_penalty = {"4pool": 0.0, "USDC/USDM": 0.02, "USDC/MONEY": 0.03}
    
    # Pool APYs
    base_apy = {"4pool": 0.0027, "USDC/USDM": 0.0317, "USDC/MONEY": 0.0035}
    
    # Pool Volumes (Total Value Locked - TVL)
    pool_volume = {"4pool": 1677000, "USDC/USDM": 79255, "USDC/MONEY": 2259}
    
    # Compute effective yield differently based on risk profile:
    # For 'stable', emphasize liquidity (volume) while applying a risk penalty.
    # For 'high-yield', emphasize the base APY (adjusted for risk).
    max_tvl = max(pool_volume.values())
    effective_yield = {}
    for pool in base_apy:
        if risk_profile == "stable":
            # Use the liquidity (TVL) factor
            effective_yield[pool] = (pool_volume[pool] / (max_tvl + 1)) * (1 - risk_penalty[pool]) + 0.0001
        else:
            # Use the yield (APY) factor
            effective_yield[pool] = base_apy[pool] * (1 - risk_penalty[pool]) + 0.0001
    
    # Compute total USD value per pool from the provided data
    protocol_values = {pool: float(data[pool]) for pool in data}
    total_capital = sum(protocol_values.values())
    max_allocation = 0.5 * total_capital  # Max allocation per protocol (50% limit)
    
    # Define LP problem
    problem = pulp.LpProblem("Yield_Optimization", pulp.LpMaximize)
    
    # Define allocation variables
    allocations = {pool: pulp.LpVariable(f"alloc_{pool}", 0, max_allocation) for pool in effective_yield}
    
    # Relaxed balance constraints (non-negative allocations)
    for pool in effective_yield:
        problem += allocations[pool] >= 0
    
    # Objective function: maximize net yield
    problem += pulp.lpSum([effective_yield[p] * allocations[p] for p in effective_yield]), "Net_Annual_Yield"
    
    # Total allocation constraint with slight flexibility
    problem += pulp.lpSum(allocations.values()) <= total_capital * 1.01
    
    # Solve the problem
    problem.solve()
    
    # Get results
    optimized_allocations = {pool: allocations[pool].varValue for pool in allocations}
    result = {
        "before": protocol_values,
        "after": optimized_allocations,
        "change": {pool: optimized_allocations[pool] - protocol_values[pool] for pool in protocol_values},
        "total_optimized_yield": sum(effective_yield[p] * optimized_allocations[p] for p in optimized_allocations)
    }
    
    return json.dumps(result, indent=4)

# def main():
#     # Sample Data
#     sample_data = {
#         "4pool": 0.021533917069534242,
#         "USDC/USDM": 0.009702021716962433,
#         "USDC/MONEY": 0.0
#     }
    
#     # Run for both risk profiles
#     stable_result = yield_opt_risk_profiles(sample_data, "stable")
#     high_yield_result = yield_opt_risk_profiles(sample_data, "high-yield")
    
#     print("Stable Profile Result:")
#     print(stable_result)
    
#     print("\nHigh-Yield Profile Result:")
#     print(high_yield_result)
    
# if __name__ == "__main__":
#     main()

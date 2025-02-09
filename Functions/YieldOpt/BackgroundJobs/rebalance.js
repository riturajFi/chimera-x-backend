const solver = require('javascript-lp-solver');
const { stringify } = require('JSON');

function yieldOptRiskProfiles(data, riskProfile) {
    // Define risk and liquidity penalties based on risk profile
    let riskPenalty;
    if (riskProfile === 'stable') {
        riskPenalty = { '4pool': 0.01, 'USDC/USDM': 0.05, 'USDC/MONEY': 0.07 };
    } else { // High-yield, riskier strategy
        riskPenalty = { '4pool': 0.0, 'USDC/USDM': 0.02, 'USDC/MONEY': 0.03 };
    }

    // Pool APYs
    const baseApy = {
        '4pool': 0.0027,
        'USDC/USDM': 0.0317,
        'USDC/MONEY': 0.0035
    };

    // Pool volumes (TVL)
    const poolVolume = {
        '4pool': 1677000,
        'USDC/USDM': 79255,
        'USDC/MONEY': 2259
    };

    // Compute effective yield
    const maxTvl = Math.max(...Object.values(poolVolume));
    let effectiveYield = {};

    for (let pool in baseApy) {
        if (riskProfile === 'stable') {
            // Emphasize liquidity (TVL), but apply a risk penalty
            effectiveYield[pool] =
                (poolVolume[pool] / (maxTvl + 1)) * (1 - riskPenalty[pool]) + 0.0001;
        } else {
            // Emphasize the base APY, adjusted for risk
            effectiveYield[pool] =
                baseApy[pool] * (1 - riskPenalty[pool]) + 0.0001;
        }
    }

    // Compute total USD values from the provided data
    const protocolValues = {};
    for (let pool in data) {
        protocolValues[pool] = parseFloat(data[pool]);
    }

    const totalCapital = Object.values(protocolValues).reduce((a, b) => a + b, 0);
    const maxAllocation = 0.5 * totalCapital; // 50% limit per protocol

    // We will build a model for javascript-lp-solver
    // The structure is:
    //
    // model = {
    //   optimize: 'Net_Annual_Yield',
    //   opType: 'max',
    //   constraints: { ... },
    //   variables: { ... }
    // };

    // 1) constraints: keep track of total allocation <= totalCapital * 1.01
    //    also each allocation must be >= 0 and <= maxAllocation
    let constraints = {
        totalAllocation: {
            max: totalCapital * 1.01
        }
    };

    // For each pool, we also define constraints for non-negativity and max allocation
    // e.g. 'alloc_4pool_nonNeg' => min: 0, 'alloc_4pool_maxAlloc' => max: maxAllocation
    // But with javascript-lp-solver, you typically embed these constraints within the
    // "variables" definitions. We'll define them in a re-usable manner.

    // We'll create a separate unique constraint for each pool, referencing them from the variable.
    for (let pool in effectiveYield) {
        constraints[`alloc_${pool}_nonNeg`] = { min: 0 };
        constraints[`alloc_${pool}_maxAlloc`] = { max: maxAllocation };
    }

    // 2) variables: each pool (e.g., "alloc_4pool") must include:
    //    - objective coefficient (Net_Annual_Yield)
    //    - +1 in the totalAllocation constraint
    //    - +1 in the non-neg constraint
    //    - +1 in the maxAlloc constraint
    let variables = {};

    for (let pool in effectiveYield) {
        variables[`alloc_${pool}`] = {
            Net_Annual_Yield: effectiveYield[pool],
            totalAllocation: 1
        };
        // Link variable to the per-pool constraints:
        variables[`alloc_${pool}`][`alloc_${pool}_nonNeg`] = 1;
        variables[`alloc_${pool}`][`alloc_${pool}_maxAlloc`] = 1;
    }

    // Build the complete model
    const model = {
        optimize: 'Net_Annual_Yield',
        opType: 'max',
        constraints: constraints,
        variables: variables
    };

    // Solve the model
    const results = solver.Solve(model);

    // Extract the optimized allocations from the solution
    // The solver returns the variable names as properties in 'results'
    // For example, results['alloc_4pool'] might be 123.45
    let optimizedAllocations = {};
    for (let pool in effectiveYield) {
        let varName = `alloc_${pool}`;
        optimizedAllocations[pool] = results[varName] || 0;
    }

    // Calculate final objective (annual yield)
    let totalOptimizedYield = 0;
    for (let pool in optimizedAllocations) {
        totalOptimizedYield += effectiveYield[pool] * optimizedAllocations[pool];
    }

    // Build the result object
    let result = {
        before: protocolValues,
        after: optimizedAllocations,
        change: {},
        total_optimized_yield: totalOptimizedYield
    };

    for (let pool in protocolValues) {
        result.change[pool] = optimizedAllocations[pool] - protocolValues[pool];
    }

    // Return JSON string with indentation
    return JSON.stringify(result, null, 4);
}

// Sample usage
function main() {
    // Sample Data
    let sampleData = {
        '4pool': 0.021533917069534242,
        'USDC/USDM': 0.009702021716962433,
        'USDC/MONEY': 0.0
    };

    // Run for both risk profiles
    let stableResult = yieldOptRiskProfiles(sampleData, 'stable');
    let highYieldResult = yieldOptRiskProfiles(sampleData, 'high-yield');

    console.log('Stable Profile Result:');
    console.log(stableResult);

    console.log('\nHigh-Yield Profile Result:');
    console.log(highYieldResult);
}

// If executed directly (e.g. `node index.js`), run main():
if (require.main === module) {
    main();
}

module.exports = { yieldOptRiskProfiles };

# import numpy as np
# import random
# from collections import defaultdict

# # ---------------------------
# #  CONFIGURATION CONSTANTS
# # ---------------------------
# NUM_EPISODES = 500       # How many episodes to train
# MAX_STEPS_PER_EPISODE = 10
# DISCOUNT_FACTOR = 0.9     # Q-learning discount
# ALPHA = 0.1               # Learning rate
# EPSILON = 0.1             # Epsilon-greedy for exploration
# TRANSACTION_COST = 0.0002    # Cost for each reallocation (dummy units)
# UNIT_SIZE = 10            # We move funds in increments of 10
# TOTAL_UNITS = 10          # We have 10 "chunks" => 100 units total
# RANDOM_SEED = 42

# np.random.seed(RANDOM_SEED)
# random.seed(RANDOM_SEED)

# # ---------------------------
# #   HELPER FUNCTIONS
# # ---------------------------
# def get_apy():
#     """
#     Returns a random APY for each of the 3 protocols (in decimal).
#     For example, an APY of 0.05 = 5%.
#     """
#     # In a real scenario, these would come from Covalent or other data sources.
#     # We'll randomly generate them in the range [0.0, 0.15] for demonstration.
#     return (
#         round(random.uniform(0.0, 0.15), 4),  # Protocol A
#         round(random.uniform(0.0, 0.15), 4),  # Protocol B
#         round(random.uniform(0.0, 0.15), 4)   # Protocol C
#     )

# def portfolio_value(state, apys):
#     """
#     Given a state (distribution of units) and the APYs of each protocol,
#     compute the new portfolio value after one period.
#     - state: (a, b, c) each in [0..TOTAL_UNITS], sum = TOTAL_UNITS
#     - apys: (apyA, apyB, apyC)
#     Each chunk represents 10 real units of currency, so:
#       actual_held_in_A = a * 10
#       yield_for_A = actual_held_in_A * apyA
#     """
#     a, b, c = state
#     apyA, apyB, apyC = apys

#     # Convert "chunks" to actual units
#     valA = (a * UNIT_SIZE)
#     valB = (b * UNIT_SIZE)
#     valC = (c * UNIT_SIZE)

#     # Gains from yield
#     gainA = valA * apyA
#     gainB = valB * apyB
#     gainC = valC * apyC

#     # New total
#     new_valA = valA + gainA
#     new_valB = valB + gainB
#     new_valC = valC + gainC

#     # Sum to get total portfolio value
#     return new_valA + new_valB + new_valC

# def get_possible_actions(state):
#     """
#     Given a state (a, b, c), return all possible actions:
#     - We can move 1 chunk (10 units) from one protocol to another,
#       as long as there's at least 1 chunk to move.
#     """
#     actions = []
#     a, b, c = state
#     # Move from A -> B
#     if a > 0:
#         actions.append(("A->B", 1))
#     # Move from A -> C
#     if a > 0:
#         actions.append(("A->C", 1))
#     # Move from B -> A
#     if b > 0:
#         actions.append(("B->A", 1))
#     # Move from B -> C
#     if b > 0:
#         actions.append(("B->C", 1))
#     # Move from C -> A
#     if c > 0:
#         actions.append(("C->A", 1))
#     # Move from C -> B
#     if c > 0:
#         actions.append(("C->B", 1))
#     # Or we can do NOTHING
#     actions.append(("NOOP", 0))
#     return actions

# def apply_action(state, action):
#     """
#     Applies the action to the current state.
#     action: (direction, amount)
#       - e.g., ("A->B", 1) means move 1 chunk from A to B.
#       - ("NOOP", 0) do nothing.
#     Returns the new state.
#     """
#     a, b, c = state
#     direction, amt = action

#     if direction == "A->B" and a >= amt:
#         return (a - amt, b + amt, c)
#     elif direction == "A->C" and a >= amt:
#         return (a - amt, b, c + amt)
#     elif direction == "B->A" and b >= amt:
#         return (a + amt, b - amt, c)
#     elif direction == "B->C" and b >= amt:
#         return (a, b - amt, c + amt)
#     elif direction == "C->A" and c >= amt:
#         return (a + amt, b, c - amt)
#     elif direction == "C->B" and c >= amt:
#         return (a, b + amt, c - amt)
#     # NOOP or insufficient units to move
#     return state

# # ---------------------------
# #   Q-LEARNING ALGORITHM
# # ---------------------------
# # We'll store Q-values in a dictionary keyed by (state, action).
# # state is (a, b, c). action is e.g. "A->B" or "NOOP".
# Q = defaultdict(float)

# def choose_action(state, epsilon):
#     """
#     Epsilon-greedy selection of action from the Q table.
#     """
#     actions = get_possible_actions(state)

#     # With probability epsilon, explore
#     if random.random() < epsilon:
#         return random.choice(actions)

#     # Otherwise, exploit (choose best Q-value)
#     best_q = None
#     best_action = None
#     for act in actions:
#         q_val = Q[(state, act)]
#         if best_q is None or q_val > best_q:
#             best_q = q_val
#             best_action = act
#     return best_action

# def q_learn():
#     """
#     Main loop to train an RL agent to optimize yield.
#     """
#     all_episode_rewards = []

#     for episode in range(NUM_EPISODES):
#         # Reset environment to an initial distribution
#         # e.g., start with everything in Protocol A:
#         state = (10, 0, 0)   # 10 chunks in A, 0 in B, 0 in C => 100% in A

#         # We can track the initial portfolio value. Let's say no yield for step 0.
#         initial_value = state[0] * UNIT_SIZE + state[1] * UNIT_SIZE + state[2] * UNIT_SIZE

#         episode_reward = 0.0

#         for step in range(MAX_STEPS_PER_EPISODE):
#             # 1) Get next APYs
#             apys = get_apy()

#             # 2) Compute the old portfolio value before taking an action
#             old_value = portfolio_value(state, apys)

#             # 3) Choose an action (epsilon-greedy)
#             action = choose_action(state, EPSILON)

#             # 4) Transition to new state
#             next_state = apply_action(state, action)

#             # 5) Compute the new portfolio value
#             new_value = portfolio_value(next_state, apys)

#             # 6) Compute the immediate reward
#             #    e.g., gain minus transaction cost if we actually moved funds
#             base_reward = new_value - old_value
#             # If action != NOOP, subtract transaction cost
#             if action[0] != "NOOP":
#                 base_reward -= TRANSACTION_COST

#             # 7) Update Q-value: Q(s,a) <- Q(s,a) + alpha [r + gamma*maxQ(s') - Q(s,a)]
#             actions_next_state = get_possible_actions(next_state)
#             max_q_next = max(Q[(next_state, act)] for act in actions_next_state)
#             old_q = Q[(state, action)]

#             Q[(state, action)] = old_q + ALPHA * (base_reward + DISCOUNT_FACTOR * max_q_next - old_q)

#             # Accumulate reward
#             episode_reward += base_reward

#             # Move on
#             state = next_state

#         all_episode_rewards.append(episode_reward)

#     return all_episode_rewards

# # ---------------------------
# #   RUN THE TRAINING
# # ---------------------------
# def main():
#     rewards = q_learn()
#     # Simple output: average reward at the end
#     print(f"Average reward over {NUM_EPISODES} episodes: {np.mean(rewards):.2f}")

#     # Check the best action from an initial state after training
#     test_state = (10, 0, 0)  # 100% in Protocol A
#     best_act = choose_action(test_state, epsilon=0.0)  # exploit
#     print(f"Best action from state {test_state} after training: {best_act}")

# if __name__ == "__main__":
#     main()

import numpy as np
import random
from collections import defaultdict

# ---------------------------
#  CONFIGURATION CONSTANTS
# ---------------------------
NUM_EPISODES = 500       # Number of training episodes
MAX_STEPS_PER_EPISODE = 50
DISCOUNT_FACTOR = 0.9     # Q-learning discount
ALPHA = 0.1               # Learning rate
EPSILON = 0.2             # Epsilon-greedy for exploration
TRANSACTION_COST = 0.01  # Cost for each reallocation
UNIT_SIZE = 10            # Each chunk represents 10 units of currency
TOTAL_UNITS = 10          # We divide portfolio into 10 chunks
RANDOM_SEED = 42

np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

# ---------------------------
#   DUMMY APY DATA (Replace with Live Data)
# ---------------------------
APY_DATA = {
    "Curve": 0.05,  # 5%
    "Aave": 0.15,   # 15%
    "Lido": 0.1     # 10%
}

# ---------------------------
#   HELPER FUNCTIONS
# ---------------------------


def get_apy():
    """
    Returns actual APYs from DeFi protocols (for now, uses dummy values).
    """
    return (APY_DATA["Curve"], APY_DATA["Aave"], APY_DATA["Lido"])


def portfolio_value(state, apys):
    """
    Computes total portfolio value based on asset distribution and APY.
    """
    a, b, c = state
    apyA, apyB, apyC = apys

    # Convert chunks to actual USD values
    valA = (a * UNIT_SIZE)
    valB = (b * UNIT_SIZE)
    valC = (c * UNIT_SIZE)

    # Compute gains from APY
    gainA = valA * apyA
    gainB = valB * apyB
    gainC = valC * apyC

    return valA + gainA + valB + gainB + valC + gainC  # New portfolio value


def get_possible_actions(state):
    """
    Returns all possible rebalancing actions.
    """
    actions = []
    a, b, c = state
    if a > 0:
        actions.append(("A->B", 1))
        actions.append(("A->C", 1))
    if b > 0:
        actions.append(("B->A", 1))
        actions.append(("B->C", 1))
    if c > 0:
        actions.append(("C->A", 1))
        actions.append(("C->B", 1))

    actions.append(("NOOP", 0))  # Option to do nothing
    return actions


def apply_action(state, action):
    """
    Moves funds between protocols based on action.
    """
    a, b, c = state
    direction, amt = action

    if direction == "A->B" and a >= amt:
        return (a - amt, b + amt, c)
    elif direction == "A->C" and a >= amt:
        return (a - amt, b, c + amt)
    elif direction == "B->A" and b >= amt:
        return (a + amt, b - amt, c)
    elif direction == "B->C" and b >= amt:
        return (a, b - amt, c + amt)
    elif direction == "C->A" and c >= amt:
        return (a + amt, b, c - amt)
    elif direction == "C->B" and c >= amt:
        return (a, b + amt, c - amt)

    return state  # No change if NOOP or invalid move

# ---------------------------
#   PARSING JSON DATA
# ---------------------------


def parse_json_to_state(data):
    """
    Converts JSON balance data into a normalized state representation.
    State is a tuple representing percentage allocation across Curve, Aave, and Lido.
    """
    protocol_values = {"Curve": 0, "Aave": 0, "Lido": 0}

    # Parse Curve Holdings
    for asset in data["curve"]:
        balance = float(asset["balance"])
        price = float(asset["quote"])
        protocol_values["Curve"] += balance * price  # Convert to USD

    # Parse Lido Holdings
    for asset in data["lido"]:
        balance = float(asset["balance"])
        price = float(asset["quote"])
        protocol_values["Lido"] += (balance / 1e9) * price  # Convert to USD

    # No Aave holdings in this dataset
    protocol_values["Aave"] = 0

    # Normalize to a 10-chunk state representation
    total_value = sum(protocol_values.values())
    if total_value == 0:
        return (0, 0, 0)  # Avoid division by zero

    state = tuple(int((v / total_value) * 10)
                  for v in protocol_values.values())

    return state


# ---------------------------
#   Q-LEARNING ALGORITHM
# ---------------------------
Q = defaultdict(float)


def choose_action(state, epsilon):
    """
    Chooses an action using epsilon-greedy exploration.
    """
    actions = get_possible_actions(state)
    if random.random() < epsilon:
        return random.choice(actions)

    return max(actions, key=lambda act: Q[(state, act)])


def q_learn(data):
    """
    Train the RL agent using actual DeFi portfolio data.
    """
    all_episode_rewards = []

    for episode in range(NUM_EPISODES):
        state = parse_json_to_state(data)
        initial_value = portfolio_value(state, get_apy())
        episode_reward = 0.0

        for step in range(MAX_STEPS_PER_EPISODE):
            apys = get_apy()
            old_value = portfolio_value(state, apys)

            action = choose_action(state, EPSILON)
            next_state = apply_action(state, action)

            new_value = portfolio_value(next_state, apys)
            base_reward = new_value - old_value

            if action[0] != "NOOP":
                base_reward -= TRANSACTION_COST  # Deduct transaction cost

            actions_next_state = get_possible_actions(next_state)
            max_q_next = max(Q[(next_state, act)]
                             for act in actions_next_state)
            old_q = Q[(state, action)]

            Q[(state, action)] = old_q + ALPHA * \
                (base_reward + DISCOUNT_FACTOR * max_q_next - old_q)

            episode_reward += base_reward
            state = next_state

        all_episode_rewards.append(episode_reward)

    return all_episode_rewards

# ---------------------------
#   RUN THE TRAINING
# ---------------------------


def main():
    json_data = {
        "curve": [
            {"chain_name": "eth-mainnet", "balance": "35.20781919682791", "contract_name": "USD Coin",
                "contract_ticker_symbol": "USDC", "quote_currency": "USD", "quote": 1.0},
            {"chain_name": "eth-mainnet", "balance": "30815200764844.85", "contract_name": "Dai Stablecoin",
                "contract_ticker_symbol": "DAI", "quote_currency": "USD", "quote": 1.0},
            {"chain_name": "eth-mainnet", "balance": "34.00571640833528", "contract_name": "Tether USD",
                "contract_ticker_symbol": "USDT", "quote_currency": "USD", "quote": 1.0}
        ],
        "aave": [],
        "lido": [
            {"chain_name": "eth-mainnet", "balance": "999999999999999", "contract_name": "Liquid staked Ether 2.0",
                "contract_ticker_symbol": "stETH", "quote_currency": "USD", "quote": 3.258454}
        ]

    }

    rewards = q_learn(json_data)
    print(f"Average reward over {
          NUM_EPISODES} episodes: {np.mean(rewards):.2f}")

    test_state = parse_json_to_state(json_data)
    best_act = choose_action(test_state, epsilon=0.0)
    print(f"Best action from state {test_state} after training: {best_act}")


if __name__ == "__main__":
    main()

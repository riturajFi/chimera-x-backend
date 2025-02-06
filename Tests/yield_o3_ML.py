import gym
import numpy as np
from gym import spaces
from stable_baselines3 import PPO
import json

# Define a custom Gym environment for yield optimization
class YieldOptimizationEnv(gym.Env):
    def __init__(self):
        super(YieldOptimizationEnv, self).__init__()
        
        # Assume we have 3 protocols: curve, aave, and lido.
        self.num_protocols = 3
        
        # Observation: current balances per protocol (USD)
        # For simplicity, we only use the balances.
        self.observation_space = spaces.Box(low=0, high=np.inf, shape=(self.num_protocols,), dtype=np.float32)
        
        # Action: adjustments (delta) to each protocol's balance.
        # The actions can be negative (withdraw) or positive (deposit).
        # We assume actions are in a range [-max_adjustment, max_adjustment].
        self.max_adjustment = 5.0  # dummy maximum adjustment value
        self.action_space = spaces.Box(low=-self.max_adjustment, high=self.max_adjustment, 
                                       shape=(self.num_protocols,), dtype=np.float32)
        
        # Set initial state (example starting balances)
        self.initial_balances = np.array([10.0, 0.0, 3.0])
        self.current_balances = self.initial_balances.copy()
        self.total_capital = np.sum(self.current_balances)
        
        # Effective yields for each protocol (as fractions, e.g., 4% = 0.04)
        # These can be derived from on-chain data or assumed.
        self.effective_yields = np.array([0.04, 0.015, 0.01])
        
        # Transaction costs: separate deposit and withdrawal percentages for each protocol.
        self.deposit_costs = np.array([0.01, 0.02, 0.015])
        self.withdrawal_costs = np.array([0.01, 0.02, 0.015])
        
        # To simulate episodes, we define a fixed episode length.
        self.current_step = 0
        self.episode_length = 10

    def step(self, action):
        # Clip the action to allowed bounds
        adjustment = np.clip(action, -self.max_adjustment, self.max_adjustment)
        
        # Calculate proposed new balances (before rebalancing the total)
        proposed_balances = self.current_balances + adjustment
        
        # To ensure the total capital remains constant, we re-scale the proposed balances.
        total_proposed = np.sum(proposed_balances)
        if total_proposed > 0:
            new_balances = proposed_balances * (self.total_capital / total_proposed)
        else:
            new_balances = self.current_balances.copy()  # safeguard
        
        # Compute deposit and withdrawal amounts per protocol.
        deposit_amount = np.maximum(new_balances - self.current_balances, 0)
        withdrawal_amount = np.maximum(self.current_balances - new_balances, 0)
        
        # Compute transaction costs:
        tx_cost = np.sum(deposit_amount * self.deposit_costs + withdrawal_amount * self.withdrawal_costs)
        
        # Compute the gross yield (annualized yield * balance); for simplicity, we treat one step as one period.
        # In a real setup, you might multiply by the period length (or discount future rewards).
        gross_yield = np.sum(new_balances * self.effective_yields)
        
        # Net reward: gross yield minus transaction costs.
        reward = gross_yield - tx_cost
        
        # Update state:
        self.current_balances = new_balances
        
        # Increase step counter.
        self.current_step += 1
        
        # Check if the episode is done.
        done = self.current_step >= self.episode_length
        
        # For debugging, include transaction details in info.
        info = {
            "deposit_amount": deposit_amount.tolist(),
            "withdrawal_amount": withdrawal_amount.tolist(),
            "tx_cost": tx_cost,
            "gross_yield": gross_yield
        }
        
        return self.current_balances.copy(), reward, done, info

    def reset(self):
        self.current_balances = self.initial_balances.copy()
        self.total_capital = np.sum(self.current_balances)
        self.current_step = 0
        return self.current_balances.copy()
    
    def render(self, mode='human'):
        print("Current balances:", self.current_balances)

# ----------------------------------------------------------------------------
# Training the RL Agent Using PPO from Stable Baselines3
# ----------------------------------------------------------------------------
def train_rl_agent():
    env = YieldOptimizationEnv()
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=5000)  # Increase timesteps for better training
    return model, env

# ----------------------------------------------------------------------------
# Testing the Trained Agent
# ----------------------------------------------------------------------------
def test_agent(model, env):
    obs = env.reset()
    done = False
    results = {
        "states": [],
        "actions": [],
        "rewards": [],
        "infos": []
    }
    while not done:
        action, _states = model.predict(obs)
        results["states"].append(obs.tolist())
        results["actions"].append(action.tolist())
        obs, reward, done, info = env.step(action)
        results["rewards"].append(reward)
        results["infos"].append(info)
    return results

if __name__ == '__main__':
    # Train the RL agent
    model, env = train_rl_agent()
    
    # Test the trained agent
    test_results = test_agent(model, env)
    
    # Output the results as JSON for inspection
    test_results_json = json.dumps(test_results, indent=4)
    print("Test Results (JSON):")
    print(test_results_json)

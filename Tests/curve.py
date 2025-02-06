from web3 import Web3
import json

# Set up environment variables
# Replace with your private key
PRIVATE_KEY = "0e130f1539d42bd663037aeee2345c88f022cd4898441879f9ec79715874d8d6"
# Replace with your RPC URL
RPC_URL = "https://base-mainnet.infura.io/v3/50b156a9977746479bc5f3f748348ac4"
# Replace with your contract address
CONTRACT_ADDRESS = "0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59"

# Connect to the Ethereum network
web3 = Web3(Web3.HTTPProvider(RPC_URL))

if not web3.is_connected():
    print("Failed to connect to the Ethereum network")
    exit()

print("Connected to the Ethereum network")

# Load the ABI
with open(r"Functions\YieldOpt\curve_abi.json", "r") as abi_file:
    contract_abi = json.load(abi_file)

# Initialize the contract
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

# Function to call
amounts = [8122411380, 0]
min_mint_amount = 382080610  # Replace with a safeguard for slippage
use_eth = True  # Set True if ETH is being used

# Prepare the transaction
try:
    # Get the transaction data
    nonce = web3.eth.get_transaction_count("0x0a64B7300acb4E0a8F420E631aC4E923F19D7584")
    gas_price = web3.eth.gas_price
    value = web3.to_wei(0.00000000812241138, 'ether')
    temp = contract.functions.add_liquidity(amounts, min_mint_amount, use_eth)
    # gas_estimate = contract.functions.add_liquidity(amounts, min_mint_amount, use_eth).estimate_gas({"from": SENDER_ADDRESS})
    transaction = contract.functions.add_liquidity(amounts, min_mint_amount, use_eth).build_transaction({
        "chainId": 8453,  # Mainnet chain ID; replace with 5 for Goerli, etc.
        "gas": 3000000,
        "gasPrice": gas_price,
        "nonce": nonce,
        "value": value
    })

    # Sign the transaction
    signed_txn = web3.eth.account.sign_transaction(transaction, PRIVATE_KEY)
    # Send the transaction
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Transaction sent: {web3.to_hex(tx_hash)}")

    # Wait for receipt
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}")

except Exception as e:
    print(f"Error: {e}")

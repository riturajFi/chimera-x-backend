from web3 import Web3
import json

# Connect to an Ethereum node (Infura, Alchemy, or local node)
INFURA_URL = "https://base-mainnet.infura.io/v3/50b156a9977746479bc5f3f748348ac4"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

# Check if connected
if not w3.is_connected():
    raise Exception("Failed to connect to Ethereum network")

# List of contracts to check balances with their names
contracts = {
    "4Pool": "0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f",
    "USDC/USDM": "0x63Eb7846642630456707C3efBb50A03c79B89D81",
    "USDC/MONEY Curve LP": "0x70d410b739Da81303a76169CDD406A746BDE8b34"
}

# ABI for balanceOf function
abi = [{
    "stateMutability": "view",
    "type": "function",
    "name": "balanceOf",
    "inputs": [{ "name": "arg0", "type": "address" }],
    "outputs": [{ "name": "", "type": "uint256" }]
}]

# Address to check balance for (Replace with actual address)
wallet_address = "0x5244b38c272b1fa6Dc22034608903eA4EeBC7C2f"
wallet_address = w3.to_checksum_address(wallet_address)

# Loop through contracts and get balances
balances = {}
for name, contract_address in contracts.items():
    contract_address = w3.to_checksum_address(contract_address)
    contract = w3.eth.contract(address=contract_address, abi=abi)
    balance = contract.functions.balanceOf(wallet_address).call()
    balances[name] = w3.from_wei(balance, 'ether')

# Print balances
for name, balance in balances.items():
    print(f"Balance in {name}: {balance} USDC")

# Return balances as JSON
balances_json = json.dumps(balances, indent=4)
print(balances_json)

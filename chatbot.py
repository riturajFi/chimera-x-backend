from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import sys
import time
import requests
import base64
from web3 import Web3
import json
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from cdp import Wallet, hash_message
from cdp_langchain.tools import CdpTool
from pydantic import BaseModel, Field
from Functions.check_pool_balance import checkPoolBalance
from Functions.YieldOpt.yieldOpt import yeild_optimize
from Functions.YieldOpt.yield_o3_txnCost import yield_opt_o3
from stake_curve_function import stake_curve
from Functions.YieldOpt.check_curve_balances import get_balances
from Functions.YieldOpt.rebalance_curve import yield_opt_risk_profiles
from Functions.YieldOpt.distribute_cruve import yield_opt_allocation

# Import CDP Agentkit Langchain Extension.
from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper

app = Flask(__name__)
CORS(app)  # Enable CORS to allow requests from the React frontend

wallet_data_file = "wallet_data.txt"
load_dotenv()
# Functions Prompts

SIGN_MESSAGE_PROMPT = """
This tool will sign arbitrary messages using EIP-191 Signed Message Standard hashing.
"""

ADD_MONITOR_PROMPT = """
This tool will add a term for monitoring by calling the cron job.
"""

STAKE_ETH_PROMPT = """
This tool can call a function with the input amount of eth to a staking protocol
"""

CLAIM_AIRDROP_PROMPT = """
This tool can call a function with the input amount of eth to a staking protocol
"""

CHECK_POOL_BALANCE_PROMPT = """
This tool can check the pool balances in lido, curve and aave for an address
"""

PROPOSE_YIELD_OPTIMIZATION = """
This tool can propose a yield optimization
"""

PROPOSE_YIELD_DISTRIBUTION = """Given a blance for an wallet, this tool proposes yield optimization techniques"""

STAKE_CURVE = """Use this function to stake in curve finance"""

TRANSAFER_USDC_FROM_USER = """ Use this to transfer usdc of user to your own wallet"""
APPROVE_4POOL_TO_SPEND_USDC_PROMPT = """This tool approves the 4Pool contract to spend the user's USDC."""
ADD_LIQUIDITY_TO_CURVE_4POOL_PROMPT = """This tool adds liquidity to Curve's 4Pool contract."""
WITHDRAW_FROM_CURVE_POOL_PROMPT = """This tool withdraws liquidity from Curve's 4Pool contract."""
SEND_USDC_TO_USER_PROMPT = """This tool sends USDC from the agent's wallet to the specified user address."""
GET_USDC_ETH_BALANCE_OF_ADDRESS = """This tool fetched usdc and eth balances of the specified user address."""


# Inputs


class SignMessageInput(BaseModel):
    message: str = Field(
        ...,
        description="The message to sign. e.g. `hello world`"
    )


class AddMonitoringInput(BaseModel):
    term: str = Field(
        ...,
        description="The term to monitor. e.g. `Flood`"
    )


class StakeEthInput(BaseModel):
    amount_in_ether: str = Field(
        ...,
        description="The amount to stake. e.g. `0.001`"
    )


class ClaimAirdropInput(BaseModel):
    address: str = Field(
        ...,
        description="The address to claim airdrop to. e.g. `0xabxdc`"
    )


class CheckPoolBalanceInput(BaseModel):
    address: str = Field(
        ...,
        description="The address to check pool balance to. e.g. `0xabxdc`"
    )


class ProposeYieldOptimizationInput(BaseModel):
    address: str = Field(
        ...,
        description="The dummy address"
    )


class StakeCurveInput(BaseModel):
    sender_address: str = Field(
        ...,
        description="The sender address"
    )


class TrsansferUsdcFromUserInput(BaseModel):
    address: str = Field(
        ...,
        description="The sender address"
    )


class ClaimAirdropInput(BaseModel):
    address: str = Field(...,
                         description="The address to claim the airdrop. e.g. `0xabxcd`")


class Approve4PoolSpendUSDCInput(BaseModel):
    address: str = Field(...,
                         description="The user's address approving USDC spend.")


class AddLiquidityToCurve4PoolInput(BaseModel):
    address: str = Field(...,
                         description="The user's address adding liquidity to Curve 4Pool.")


class WithdrawFromCurvePoolInput(BaseModel):
    address: str = Field(
        ..., description="The user's address withdrawing liquidity from Curve 4Pool.")


class SendUSDCToUserInput(BaseModel):
    address: str = Field(...,
                         description="The recipient's address to send USDC to.")


class GetBalanceUSDCEthforAddress(BaseModel):
    address: str = Field(...,
                         description="The recipient's address to send USDC to.")


class ProposeYieldDistribution(BaseModel):
    balance: int = Field(...,
                         description="The recipient's address to send USDC to.")


# Functions

def sign_message(wallet: Wallet, message: str) -> str:
    """Sign message using EIP-191 message hash from the wallet.

    Args:
        wallet (Wallet): The wallet to sign the message from.
        message (str): The message to hash and sign.

    Returns:
        str: The message and corresponding signature.

    """
    payload_signature = wallet.sign_payload(hash_message(message)).wait()

    return f"The payload signature {payload_signature}"


def get_balances_eth_usdc(address: str):
    print("called get_balances_eth_usdc")
    INFURA_URL = "https://base-mainnet.infura.io/v3/50b156a9977746479bc5f3f748348ac4"
    web3 = Web3(Web3.HTTPProvider(INFURA_URL))

    # Convert address to checksum format
    address = web3.to_checksum_address(address)

    # Fetch ETH balance
    eth_balance_wei = web3.eth.get_balance(address)
    eth_balance = web3.from_wei(eth_balance_wei, 'ether')

    # USDC Contract Details (Base Mainnet)
    # Replace with actual Base USDC contract address
    USDC_CONTRACT_ADDRESS = web3.to_checksum_address(
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
    USDC_ABI = [
        {
            "stateMutability": "view",
            "type": "function",
            "name": "balanceOf",
            "inputs": [{"name": "arg0", "type": "address"}],
            "outputs": [{"name": "", "type": "uint256"}],
        }
    ]

    usdc_contract = web3.eth.contract(
        address=USDC_CONTRACT_ADDRESS, abi=USDC_ABI)

    # Fetch USDC balance
    usdc_balance_wei = usdc_contract.functions.balanceOf(address).call()
    usdc_balance = usdc_balance_wei / (10**6)  # USDC has 6 decimal places

    return {
        "ETH Balance": f"{eth_balance} ETH",
        "USDC Balance": f"{usdc_balance} USDC"
    }


def call_add_monitor_term(term):

    api_url = f"http://localhost:8000/add_watch?term={term}"

    try:
        response = requests.post(api_url)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        return response.json()  # Assumes the API returns JSON response
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def checkPoolBalance_agent(address):
    print("Called checkPoolBalance_agent")
    filename = "pool_balances.json"
    pool_balances_raw = get_balances(wallet_address=address)
    print(pool_balances_raw)
    # Parse the raw JSON string into a dictionary
    pool_balances = json.loads(pool_balances_raw) if isinstance(
        pool_balances_raw, str) else pool_balances_raw
    with open(filename, "w") as json_file:
        json.dump(pool_balances, json_file, indent=4)
    return pool_balances

# Stake function


def stake_eth(amount_in_ether):

    INFURA_URL = "https://base-sepolia.infura.io/v3/50b156a9977746479bc5f3f748348ac4"
    web3 = Web3(Web3.HTTPProvider(INFURA_URL))

    with open("staking_abi.json", "r") as file:
        staking_abi = json.load(file)

    amount_in_wei = web3.to_wei(amount_in_ether, "ether")
    staker_address = "0x7B133e5bce9552289Adb6B8a0449318De9C6C894"  # Staker's address
    # Replace with staker's private key
    staker_private_key = os.getenv("STAKER_PK")
    staking_contract_address = "0xe725fA0577e25aCdf6F8Fbd979fdd7437714d6cb"
    nonce = web3.eth.get_transaction_count(staker_address)
    staking_contract = web3.eth.contract(
        address=staking_contract_address, abi=staking_abi)

    txn = staking_contract.functions.stake().build_transaction({
        "from": staker_address,
        "value": amount_in_wei,
        "gas": 300000,
        "gasPrice": web3.to_wei("10", "gwei"),
        "nonce": nonce
    })

    # Sign and send the transaction
    signed_txn = web3.eth.account.sign_transaction(
        txn, private_key=staker_private_key)
    txn_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Stake transaction sent. Txn Hash: {txn_hash.hex()}")

    # Wait for receipt
    receipt = web3.eth.wait_for_transaction_receipt(txn_hash)
    print("Transaction receipt:", receipt)


def proposeYieldOptimization(address):
    filename = "pool_balances.json"
    pool_balance_data = {
        "4pool": 0.070793,
        "USDC/USDM": 0.009702021716962433,
        "USDC/MONEY": 0.0
    }
    # try:
    #     with open(filename, "r") as json_file:
    #         pool_balance_data = json.load(json_file)
    # except:
    #     pool_balance_data = {
    #         "4pool": 0.021533917069534242,
    #         "USDC/USDM": 0.009702021716962433,
    #         "USDC/MONEY": 0.0
    #     }

    return yield_opt_risk_profiles(data=pool_balance_data, risk_profile="stable")


def propose_yield_distribution(balance):

    print("Called Propese yield")
    result = yield_opt_allocation(0.569851, risk_profile="stable")
    print(result)
    return result


def stake_curve_finance(sender_address):
    print("Called stake curve")
    stake_curve(sender_address=sender_address)


def transfer_usdc_from_user(address: str):
    print("call transfer_usdc_from_user")
    INFURA_URL = "https://base-mainnet.infura.io/v3/50b156a9977746479bc5f3f748348ac4"
    web3 = Web3(Web3.HTTPProvider(INFURA_URL))

    # Contract Details
    contract_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    abi = [
        {
            "stateMutability": "nonpayable",
            "type": "function",
            "name": "transferFrom",
            "inputs": [
                {"name": "_from", "type": "address"},
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "outputs": [{"name": "", "type": "bool"}]
        },
    ]

    # Load Private Key Securely
    private_key = os.getenv("AGENTKIT_PRIVATE_KEY")
    if not private_key:
        raise ValueError(
            "Private key is missing. Set AGENTKIT_PRIVATE_KEY in .env")

    # Addresses
    owner_address = "0x8e003462E1e3F711533955B9B581732e98ACc139"
    spender_address = "0x5A9f8C21aEa074EBe211F20A8E51E8d90777F404"
    recipient_address = "0x5A9f8C21aEa074EBe211F20A8E51E8d90777F404"

    # Amount to Transfer (1 Wei in USDC terms)
    amount = 284925  # 1 Wei of USDC

    # Contract Instance
    contract = web3.eth.contract(address=contract_address, abi=abi)

    # Get Nonce (for Spender)
    nonce = web3.eth.get_transaction_count(spender_address)

    # Estimate Gas
    estimated_gas_limit = contract.functions.transferFrom(owner_address, recipient_address, amount).estimate_gas({
        "from": spender_address
    })
    print(f"Estimated Gas Limit: {estimated_gas_limit}")

    # Get Optimal Gas Price
    base_fee = web3.eth.gas_price
    priority_fee = web3.to_wei("1", "gwei")  # Safe low priority fee
    max_fee = base_fee + priority_fee  # Ensure minimal overpaying

    # Build the Transaction
    txn = contract.functions.transferFrom(
        owner_address,
        recipient_address,
        amount
    ).build_transaction({
        "from": spender_address,
        "gas": estimated_gas_limit,  # Dynamically estimated
        "maxPriorityFeePerGas": priority_fee,  # EIP-1559 dynamic fee
        "maxFeePerGas": max_fee,
        "nonce": nonce,
        "chainId": web3.eth.chain_id,
    })

    # Sign Transaction
    signed_txn = web3.eth.account.sign_transaction(txn, private_key)

    # Send Transaction
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

    # Wait for Receipt
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"Trasnfered USDC from user to agent : {receipt}")


def approve_4pool_to_spend_usdc(address: str):
    print("Called apprive 4pool")
    INFURA_URL = "https://base-mainnet.infura.io/v3/50b156a9977746479bc5f3f748348ac4"
    web3 = Web3(Web3.HTTPProvider(INFURA_URL))

    # Contract Details
    # Replace with actual USDC contract address
    USDC_contract_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    abi = [
        {
            "stateMutability": "nonpayable",
            "type": "function",
            "name": "approve",
            "inputs": [
                {"name": "spender", "type": "address"},
                {"name": "value", "type": "uint256"}
            ],
            "outputs": [{"name": "", "type": "bool"}]
        },
    ]

    # Load Private Key Securely
    private_key = os.getenv("AGENTKIT_PRIVATE_KEY")
    if not private_key:
        raise ValueError(
            "Private key is missing. Set AGENTKIT_PRIVATE_KEY in .env")

    # Addresses
    # Replace with your wallet address
    owner_address = "0x5A9f8C21aEa074EBe211F20A8E51E8d90777F404"
    spender_address = "0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f"
    max_approval_amount = int(
        "115792089237316195423570985008687907853269984665640564039457584007913129639935"
    )  # Maximum uint256 value

    # Contract Instance
    contract = web3.eth.contract(address=USDC_contract_address, abi=abi)

    # Get Nonce (for Owner)
    nonce = web3.eth.get_transaction_count(owner_address)

    # Estimate Gas
    estimated_gas_limit = contract.functions.approve(spender_address, max_approval_amount).estimate_gas({
        "from": owner_address
    })
    print(f"Estimated Gas Limit: {estimated_gas_limit}")

    # Get Optimal Gas Price
    base_fee = web3.eth.gas_price
    priority_fee = web3.to_wei("1", "gwei")  # Safe low priority fee
    max_fee = base_fee + priority_fee  # Ensure minimal overpaying

    # Build the Transaction
    txn = contract.functions.approve(spender_address, max_approval_amount).build_transaction({
        "from": owner_address,
        "gas": estimated_gas_limit,  # Dynamically estimated
        "maxPriorityFeePerGas": priority_fee,  # EIP-1559 dynamic fee
        "maxFeePerGas": max_fee,
        "nonce": nonce,
        "chainId": web3.eth.chain_id,
    })

    # Sign Transaction
    signed_txn = web3.eth.account.sign_transaction(txn, private_key)

    # Send Transaction
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

    # Wait for Receipt
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"Approval successful! Tx Hash: {tx_hash.hex()}")


def add_liquidity_to_curve_4Pool(address: str):

    print("called add_liquidity_to_curve_4Pool")

    transfer_usdc_from_user("0x8e003462E1e3F711533955B9B581732e98ACc139")

    INFURA_URL = "https://base-mainnet.infura.io/v3/50b156a9977746479bc5f3f748348ac4"
    web3 = Web3(Web3.HTTPProvider(INFURA_URL))

    # Contract Details
    abi = [
        {
            "stateMutability": "nonpayable",
            "type": "function",
            "name": "add_liquidity",
            "inputs": [
                {"name": "_amounts", "type": "uint256[4]"},
                {"name": "_min_mint_amount", "type": "uint256"},
            ],
            "outputs": [{"name": "", "type": "uint256"}],
        },
    ]

    # Load Private Key Securely
    private_key = os.getenv("AGENTKIT_PRIVATE_KEY")
    if not private_key:
        raise ValueError(
            "Private key is missing. Set AGENTKIT_PRIVATE_KEY in .env")

    # Addresses
    contract_address = web3.to_checksum_address(
        "0xf6c5f01c7f3148891ad0e19df78743d31e390d1f")
    spender_address = web3.to_checksum_address(
        "0x5A9f8C21aEa074EBe211F20A8E51E8d90777F404")
    _amounts = [int(200000), int(0), int(0), int(0)]
    _amounts = [int(200000), int(0), int(0), int(0)]  # USDC deposit
    _is_deposit = True  # Boolean flag for deposit

    # ✅ ABI Definitions
    ABI = [
        {
            "stateMutability": "nonpayable",
            "type": "function",
            "name": "add_liquidity",
            "inputs": [
                {"name": "_amounts", "type": "uint256[4]"},
                {"name": "_min_mint_amount", "type": "uint256"},
            ],
            "outputs": [{"name": "", "type": "uint256"}],
        },
        {
            "stateMutability": "view",
            "type": "function",
            "name": "calc_token_amount",
            "inputs": [
                {"name": "_amounts", "type": "uint256[4]"},
                {"name": "_is_deposit", "type": "bool"},
            ],
            "outputs": [{"name": "", "type": "uint256"}],
        },
    ]

    # ✅ Contract Instance
    contract = web3.eth.contract(address=contract_address, abi=ABI)

    # ✅ Calculate `_min_mint_amount` dynamically
    _min_mint_amount = contract.functions.calc_token_amount(
        _amounts, _is_deposit).call()
    print(_min_mint_amount)
    # Contract Instance
    contract = web3.eth.contract(address=contract_address, abi=abi)

    # Get Nonce (for Spender)
    nonce = web3.eth.get_transaction_count(spender_address)

    # Estimate Gas
    estimated_gas_limit = contract.functions.add_liquidity(_amounts, int(_min_mint_amount * 0.99)).estimate_gas({
        "from": spender_address
    })
    print(f"Estimated Gas Limit: {estimated_gas_limit}")

    # Get Optimal Gas Price
    base_fee = web3.eth.gas_price
    priority_fee = web3.to_wei("1", "gwei")  # Safe low priority fee
    max_fee = base_fee + priority_fee  # Ensure minimal overpaying

    # Build the Transaction
    txn = contract.functions.add_liquidity(_amounts, _min_mint_amount).build_transaction({
        "from": spender_address,
        "gas": estimated_gas_limit,  # Dynamically estimated
        "maxPriorityFeePerGas": priority_fee,  # EIP-1559 dynamic fee
        "maxFeePerGas": max_fee,
        "nonce": nonce,
        "chainId": web3.eth.chain_id,
    })

    # Sign Transaction
    signed_txn = web3.eth.account.sign_transaction(txn, private_key)

    # Send Transaction
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

    # Wait for Receipt
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"Syccess add_liquidity_to_curve_4Pool! Hash: {tx_hash.hex()}")


def withdaw_from_curve_pool(address: str):
    print("Called withdaw_from_curve_pool")
    INFURA_URL = "https://base-mainnet.infura.io/v3/50b156a9977746479bc5f3f748348ac4"
    web3 = Web3(Web3.HTTPProvider(INFURA_URL))

    # Contract Details
    # Replace with actual 4Pool contract address
    contract_address = web3.to_checksum_address(
        "0xf6c5f01c7f3148891ad0e19df78743d31e390d1f")
    abi = [
        {
            "stateMutability": "nonpayable",
            "type": "function",
            "name": "remove_liquidity_one_coin",
            "inputs": [
                {"name": "_burn_amount", "type": "uint256"},
                {"name": "i", "type": "int128"},
                {"name": "_min_received", "type": "uint256"},
            ],
            "outputs": [{"name": "", "type": "uint256"}]
        },
    ]

    # Load Private Key Securely
    private_key = os.getenv("AGENTKIT_PRIVATE_KEY")
    if not private_key:
        raise ValueError(
            "Private key is missing. Set AGENTKIT_PRIVATE_KEY in .env")

    # Addresses
    sender_address = web3.to_checksum_address(
        "0x5A9f8C21aEa074EBe211F20A8E51E8d90777F404")  # Replace with your wallet address

    # Hardcoded Values (Equivalent to JavaScript)
    _burn_amount = int("2521159640395019")  # Amount to burn
    i = 0  # Index of the token
    _min_received = int(2557)  # Minimum tokens to receive

    # Contract Instance
    contract = web3.eth.contract(address=contract_address, abi=abi)

    # Get Nonce
    nonce = web3.eth.get_transaction_count(sender_address)

    # Estimate Gas
    estimated_gas_limit = contract.functions.remove_liquidity_one_coin(
        _burn_amount, i, _min_received
    ).estimate_gas({
        "from": sender_address
    })
    print(f"Estimated Gas Limit: {estimated_gas_limit}")

    # Get Optimal Gas Price
    base_fee = web3.eth.gas_price
    priority_fee = web3.to_wei("1", "gwei")  # Safe low priority fee
    max_fee = base_fee + priority_fee  # Ensure minimal overpaying

    # Build the Transaction
    txn = contract.functions.remove_liquidity_one_coin(
        _burn_amount, i, _min_received
    ).build_transaction({
        "from": sender_address,
        "gas": estimated_gas_limit,  # Dynamically estimated
        "maxPriorityFeePerGas": priority_fee,  # EIP-1559 dynamic fee
        "maxFeePerGas": max_fee,
        "nonce": nonce,
        "chainId": web3.eth.chain_id,
    })

    # Sign Transaction
    signed_txn = web3.eth.account.sign_transaction(txn, private_key)

    # Send Transaction
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

    # Wait for Receipt
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"Liquidity Removed Successfully! Tx Hash: {tx_hash.hex()}")


def send_usdc_to_user(wallet: Wallet):
    print("Called send_usdc_to_user")
    INFURA_URL = "https://base-mainnet.infura.io/v3/50b156a9977746479bc5f3f748348ac4"
    web3 = Web3(Web3.HTTPProvider(INFURA_URL))

    # Contract Details
    contract_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    abi = [
        {
            "stateMutability": "nonpayable",
            "type": "function",
            "name": "transferFrom",
            "inputs": [
                {"name": "_from", "type": "address"},
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "outputs": [{"name": "", "type": "bool"}]
        },
    ]

    # Load Private Key Securely
    private_key = os.getenv("AGENTKIT_PRIVATE_KEY")
    if not private_key:
        raise ValueError(
            "Private key is missing. Set AGENTKIT_PRIVATE_KEY in .env")

    # Addresses
    owner_address = web3.to_checksum_address(
        "0xE8e5651d0b020011FF5991B59e49fd64eeE02311")
    spender_address = web3.to_checksum_address(
        "0x5A9f8C21aEa074EBe211F20A8E51E8d90777F404")
    recipient_address = web3.to_checksum_address(
        "0xE8e5651d0b020011FF5991B59e49fd64eeE02311")

    # Amount to Transfer (1 Wei in USDC terms)
    amount = 1  # 1 Wei of USDC

    # Contract Instance
    contract = web3.eth.contract(address=contract_address, abi=abi)

    # Get Nonce (for Spender)
    nonce = web3.eth.get_transaction_count(spender_address)

    # Estimate Gas
    estimated_gas_limit = contract.functions.transferFrom(spender_address, recipient_address, amount).estimate_gas({
        "from": spender_address
    })
    print(f"Estimated Gas Limit: {estimated_gas_limit}")

    # Get Optimal Gas Price
    base_fee = web3.eth.gas_price
    priority_fee = web3.to_wei("1", "gwei")  # Safe low priority fee
    max_fee = base_fee + priority_fee  # Ensure minimal overpaying

    # Build the Transaction
    txn = contract.functions.transferFrom(
        owner_address,
        recipient_address,
        amount
    ).build_transaction({
        "from": spender_address,
        "gas": estimated_gas_limit,  # Dynamically estimated
        "maxPriorityFeePerGas": priority_fee,  # EIP-1559 dynamic fee
        "maxFeePerGas": max_fee,
        "nonce": nonce,
        "chainId": web3.eth.chain_id,
    })

    # Sign Transaction
    signed_txn = web3.eth.account.sign_transaction(txn, private_key)

    # Send Transaction
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

    # Wait for Receipt
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"Transaction successful! Hash: {tx_hash.hex()}")


class START_MONITOR_INP(BaseModel):
    sender_address: str = Field(
        ...,
        description="The sender address"
    )


START_MONITOR_DES = """start monitoring pool"""


def activateMonitoringPool(sender_address):
    print("Called activateMonitoringPool")
    api_url = "http://localhost:8080/api/start-monitor"

    # Set the monitoring time in seconds
    params = {"total_monitoring_time": 500000}  # Adjust time as needed

    # Make the GET request
    response = requests.get(api_url, params=params)
    print(response)

# Initialize Agent


def initialize_agent():
    """Initialize the agent with CDP Agentkit."""
    # Initialize LLM.
    llm = ChatOpenAI(model="gpt-4o-mini")

    wallet_data = None

    if os.path.exists(wallet_data_file):
        with open(wallet_data_file) as f:
            wallet_data = f.read()

    # Configure CDP Agentkit Langchain Extension.
    values = {}
    if wallet_data is not None:
        # If there is a persisted agentic wallet, load it and pass to the CDP Agentkit Wrapper.
        values = {"cdp_wallet_data": wallet_data}
        wallet_dict = json.loads(values["cdp_wallet_data"])
    agentkit = CdpAgentkitWrapper(**values)
    # persist the agent's CDP MPC Wallet Data.
    wallet_data = agentkit.export_wallet()
    with open(wallet_data_file, "w") as f:
        f.write(wallet_data)

    # Initialize CDP Agentkit Toolkit and get tools.
    cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(agentkit)
    tools = cdp_toolkit.get_tools()

    signMessageTool = CdpTool(
        name="sign_message",
        description=SIGN_MESSAGE_PROMPT,
        cdp_agentkit_wrapper=agentkit,
        args_schema=SignMessageInput,
        func=sign_message,
    )

    addMonitoringTermTool = CdpTool(
        name="add_monitoring",
        description=ADD_MONITOR_PROMPT,
        cdp_agentkit_wrapper=agentkit,
        args_schema=AddMonitoringInput,
        func=call_add_monitor_term,
    )

    stake_eth_tool = CdpTool(
        name="call_function",
        description=STAKE_ETH_PROMPT,
        cdp_agentkit_wrapper=agentkit,
        args_schema=StakeEthInput,
        func=stake_eth,
    )

    check_pool_balance_tool = CdpTool(
        name="check_pool_balance",
        description=CHECK_POOL_BALANCE_PROMPT,
        cdp_agentkit_wrapper=agentkit,
        args_schema=CheckPoolBalanceInput,
        func=checkPoolBalance_agent,
    )

    propose_yeild_opt_tool = CdpTool(
        name="propose_yeild_optimization",
        description=PROPOSE_YIELD_OPTIMIZATION,
        cdp_agentkit_wrapper=agentkit,
        args_schema=ProposeYieldOptimizationInput,
        func=proposeYieldOptimization
    )

    propose_yield_dist_tool = CdpTool(
        name="propose_yield_dist_tool",
        description=PROPOSE_YIELD_DISTRIBUTION,
        cdp_agentkit_wrapper=agentkit,
        args_schema=ProposeYieldDistribution,
        func=propose_yield_distribution
    )

    stake_curve_tool = CdpTool(
        name="stake_curve_finance",
        description=STAKE_CURVE,
        cdp_agentkit_wrapper=agentkit,
        args_schema=StakeCurveInput,
        func=stake_curve_finance
    )

    transafer_usdc_from_user_tool = CdpTool(
        name="transafer_usdc_from_user",
        description=TRANSAFER_USDC_FROM_USER,
        cdp_agentkit_wrapper=agentkit,
        args_schema=TrsansferUsdcFromUserInput,
        func=transfer_usdc_from_user
    )

    approve_4pool_to_spend_usdc_tool = CdpTool(
        name="approve_4pool_to_spend_usdc",
        description=APPROVE_4POOL_TO_SPEND_USDC_PROMPT,
        cdp_agentkit_wrapper=agentkit,
        args_schema=Approve4PoolSpendUSDCInput,
        func=approve_4pool_to_spend_usdc,
    )

    add_liquidity_to_curve_4Pool_tool = CdpTool(
        name="add_liquidity_to_curve_4pool",
        description=ADD_LIQUIDITY_TO_CURVE_4POOL_PROMPT,
        cdp_agentkit_wrapper=agentkit,
        args_schema=AddLiquidityToCurve4PoolInput,
        func=add_liquidity_to_curve_4Pool,
    )

    withdraw_from_curve_pool_tool = CdpTool(
        name="withdraw_from_curve_pool",
        description=WITHDRAW_FROM_CURVE_POOL_PROMPT,
        cdp_agentkit_wrapper=agentkit,
        args_schema=WithdrawFromCurvePoolInput,
        func=withdaw_from_curve_pool,
    )

    send_usdc_to_user_tool = CdpTool(
        name="send_usdc_to_user",
        description=SEND_USDC_TO_USER_PROMPT,
        cdp_agentkit_wrapper=agentkit,
        args_schema=SendUSDCToUserInput,
        func=send_usdc_to_user,
    )

    get_balances_eth_usdc_tool = CdpTool(
        name="get_balances_eth_usdc",
        description=GET_USDC_ETH_BALANCE_OF_ADDRESS,
        cdp_agentkit_wrapper=agentkit,
        args_schema=GetBalanceUSDCEthforAddress,
        func=get_balances_eth_usdc,
    )

    startMonintorTool = CdpTool(
        name="start_monitoring_pools",
        description=START_MONITOR_DES,
        cdp_agentkit_wrapper=agentkit,
        args_schema=START_MONITOR_INP,
        func=activateMonitoringPool,

    )

    tools.append(signMessageTool)
    tools.append(stake_eth_tool)
    tools.append(check_pool_balance_tool)
    tools.append(propose_yeild_opt_tool)
    tools.append(stake_curve_tool)
    tools.append(transafer_usdc_from_user_tool)
    tools.extend([
        approve_4pool_to_spend_usdc_tool,
        add_liquidity_to_curve_4Pool_tool,
        withdraw_from_curve_pool_tool,
        send_usdc_to_user_tool,
        get_balances_eth_usdc_tool, propose_yield_dist_tool,
        startMonintorTool
    ])
    # Store buffered conversation history in memory.
    memory = MemorySaver()
    config = {"configurable": {"thread_id": "CDP Agentkit Chatbot Example!"}}

    # Create ReAct Agent using the LLM and CDP Agentkit tools.
    return create_react_agent(
        llm,
        tools=tools,
        checkpointer=memory,
        state_modifier=(
            "Keep in mind that when you print the response from a function call, at the end add the term - Function called : the_name_of_function_called"
            "You are a helpful agent that can interact onchain using the Coinbase Developer Platform AgentKit. "
            "You are empowered to interact onchain using your tools. If you ever need funds, you can request "
            "them from the faucet if you are on network ID 'base-sepolia'. If not, you can provide your wallet "
            "details and request funds from the user. Before executing your first action, get the wallet details "
            "to see what network you're on. If there is a 5XX (internal) HTTP error code, ask the user to try "
            "again later. If someone asks you to do something you can't do with your currently available tools, "
            "you must say so, and encourage them to implement it themselves using the CDP SDK + Agentkit, "
            "recommend they go to docs.cdp.coinbase.com for more information. Be concise and helpful with your "
            "You can also call a function on a staking platform with some eth on a staking protocol using the call_function method"
            "You can also claim airdrop. For this, call the call_airdrop function"
            "You can transfer USDC from user. To do so, invoke the transer_usdc_from_user function"
            "You can als Check Pool balance across AAVE, CURVE and LIDO. Give response regarding the balances strictly as : The balance details for the address `0xcE674EED84af71CFb5540d764fF5047a183eaA9d` are as follows"
            "You can propose yield optmization. For proposing yield optmiziation, call the propose_yeild_opt_tool. You should call the check_pool_balances if it is not called before"
            "You can also stake in curve finance by calling stake_curve_finance function with requried wallet address as input to sender_address"
            "When you are asked by the user to find the balances of a given address, call the get_balances_eth_usdc_tool with input as the input address"
            """When asked for executing transaction based on yield optimization is proposed, ie after you call the Yeild optimization function, if the User says to execute the transactions, then ask them for approving the use of USDC by replying specifically : Please approve USDC Spend limit amount. The amount here is specified by the user. If not then ask them for the amount
               When User input is the word approved, call only and only add_liquidity_to_curve_4Pool
            """
            """When asked for yield distrubtion, call the propose yield distribution with USDC value of your wallet address"""
            "When asked to fund a wallet, give the following answer : Please click the following button to fund your wallet. Do not call any function or anyhting extra reply"
            "When asked about how to grow my tokens or ocrypto, reply with : One of the ways to grow your crypto is to stake them in yield generating strategies. Then tell the user a little about yield and Curve finance"
            "If prompted on how to distribute my crypto, give answer by calling the propose_yield_distribution funciton. Read the result and also memorize the correspondign values needed to stake in each protcol"
            "For monitoring, call stat monitor tool"
        ),
    ), config

# Autonomous Mode


agent_executor = None
config = None


@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    agent_response = ""
    tool_response = ""
    # Run agent with the user's input in chat mode
    for chunk in agent_executor.stream(
        {"messages": [HumanMessage(content=user_message)]}, config
    ):
        if "agent" in chunk:
            print(chunk["agent"]["messages"][0].content)
            agent_response += (chunk["agent"]["messages"][0].content)
        elif "tools" in chunk:
            print(chunk["tools"]["messages"][0].content)
            tool_response += (chunk["tools"]["messages"][0].content)
    return jsonify({"response": agent_response, "tool_response": tool_response})


if __name__ == '__main__':
    agent_executor, config = initialize_agent()
    app.run(debug=True)

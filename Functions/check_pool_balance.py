import base64
import requests
import json


def checkPoolBalance(address):
    api_key = "cqt_rQ67gJQPRxHGRVXK3K4HTJrtTcgw"

    # Construct the Basic Auth header
    auth_header = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("utf-8")

    # List of protocols to query
    protocols = ["curve", "aave", "lido"]

    # Headers
    headers = {
        "Authorization": f"Basic {auth_header}"
    }

    # Store results
    balances = {}

    # Loop through each protocol and fetch data
    for protocol in protocols:
        url = f"https://api.covalenthq.com/v1/cq/covalent/app/{protocol}/balances/?address={address}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            balances[protocol] = []

            # Parse the response data
            for item in data.get("data", {}).get("items", []):
                balance_info = {
                    "chain_name": item.get("chain_name"),
                    "balance": item.get("balance"),
                    "contract_name": item.get("contract_name"),
                    "contract_ticker_symbol": item.get("contract_ticker_symbol"),
                    "quote_currency": item.get("quote_currency"),
                    "quote": item.get("quote"),
                }
                balances[protocol].append(balance_info)
        else:
            balances[protocol] = {
                "error": {
                    "status_code": response.status_code,
                    "message": response.text
                }
            }

    # Return the balances as a JSON object
    return json.dumps(balances, indent=4)

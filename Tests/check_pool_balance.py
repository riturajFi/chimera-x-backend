import base64
import requests
import json
import sys

def check_pool_balance(address):
    api_key = "cqt_rQ67gJQPRxHGRVXK3K4HTJrtTcgw"  # Replace with your actual API key

    # Construct the Basic Auth header
    auth_header = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("utf-8")

    # Headers
    headers = {
        "Authorization": f"Basic {auth_header}"
    }

    # Store results
    balances = {}

    # Loop through each protocol and fetch data

    url = f"https://api.covalenthq.com/v1/cq/covalent/app/curve/balances/?address=0x6F862c13d02Abb6c362D62E996A84EF5907eA795"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print(response.json())
    else:
        balances[protocol] = {
            "error": {
                "status_code": response.status_code,
                "message": response.text
            }
        }

    # Return the balances as a JSON object
    return json.dumps(balances, indent=4)

if __name__ == "__main__":

    result = check_pool_balance("0x6F862c13d02Abb6c362D62E996A84EF5907eA795")

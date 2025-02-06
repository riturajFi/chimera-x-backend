import asyncio
import os
import json
from fastapi import FastAPI, BackgroundTasks
from typing import Dict
from twikit import Client
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper

###########################################
# TWITTER SCRAPING CLIENT
###########################################
USERNAME = "@rituraj10x"
EMAIL = "riturajtripathy10x@gmail.com"
PASSWORD = "Rx2000!Rn"

# Initialize Twikit client and load cookies
client = Client('en-US')
client.load_cookies('cookies.json')

###########################################
# GLOBALS
###########################################
# Watch terms dictionary: key = search term, value = bool (whether found or not)
watch_terms: Dict[str, bool] = {}

# FastAPI instance
app = FastAPI()

###########################################
# HELPER FUNCTION: RETRIEVE DONATION ADDRESS
###########################################


def get_donation_address(term: str) -> str:
    """
    Loads donations.json and retrieves the **first** donation address for the given term.
    Returns the Ethereum address if found, else None.
    """
    try:
        with open("donations.json", "r") as f:
            donations_data = json.load(f)
    except Exception as e:
        print(f"Error loading donations.json: {e}")
        return None

    term_key = term.lower()
    for key in donations_data:
        if key.lower() == term_key:
            campaigns = donations_data[key]
            if campaigns and isinstance(campaigns, list):
                # Select **only the first** campaign
                first_campaign = campaigns[0]
                if isinstance(first_campaign, dict):
                    for campaign_name, address in first_campaign.items():
                        print(f"Found donation campaign '{campaign_name}' for term '{
                              term}' with address: {address}")
                        return address
    print(f"No donation campaign found for term '{term}' in donations.json")
    return None

###########################################
# BACKGROUND TASK: MONITORING TWEETS
###########################################


async def monitor_tweets():
    """
    Continuously monitors Twitter for each watch term.
    When a credible tweet (e.g., with at least 0 likes in this example) is found,
    it attempts to send ETH to the associated donation address.
    """
    while True:
        try:
            for term, already_found in list(watch_terms.items()):
                if already_found:
                    continue  # Skip terms already satisfied

                print(f"Searching for tweets with term: {term}")
                tweets = await client.search_tweet(term, 'Latest')
                if not tweets:
                    continue

                for tweet in tweets:
                    if tweet.favorite_count >= 0:
                        sendToken(term=term, tweet=tweet)
                        watch_terms[term] = True  # Mark term as found
                        break

            await asyncio.sleep(10)

        except Exception as e:
            print(f"Error during monitoring: {e}")
            await asyncio.sleep(10)

###########################################
# AGENT INITIALIZATION
###########################################


def initialize_agent():
    """Initialize the agent with CDP Agentkit."""
    llm = ChatOpenAI(model="gpt-4o-mini")
    wallet_data = None
    wallet_data_file = "wallet_data.txt"

    if os.path.exists(wallet_data_file):
        with open(wallet_data_file) as f:
            wallet_data = f.read()

    values = {"cdp_wallet_data": wallet_data} if wallet_data else {}
    agentkit = CdpAgentkitWrapper(**values)

    wallet_data = agentkit.export_wallet()
    with open(wallet_data_file, "w") as f:
        f.write(wallet_data)

    cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(agentkit)
    tools = cdp_toolkit.get_tools()
    memory = MemorySaver()
    config = {"configurable": {"thread_id": "CDP Agentkit Chatbot Example!"}}

    return create_react_agent(
        llm, tools=tools, checkpointer=memory,
        state_modifier=(
            "You are a helpful agent that can interact onchain using the Coinbase Developer Platform AgentKit. "
            "You are empowered to interact onchain using your tools. If you ever need funds, you can request "
            "them from the faucet if you are on network ID 'base-sepolia'. If not, you can provide your wallet "
            "details and request funds from the user. Before executing your first action, get the wallet details "
            "to see what network you're on. If there is a 5XX (internal) HTTP error code, ask the user to try "
            "again later. If someone asks you to do something you can't do with your currently available tools, "
            "you must say so, and encourage them to implement it themselves using the CDP SDK + Agentkit, "
            "recommend they go to docs.cdp.coinbase.com for more information."
        ),
    ), config

###########################################
# SEND MONEY TO BENEFICIARY
###########################################


def sendToken(term, tweet):
    """
    Checks donations.json for a donation address associated with the term.
    If a donation campaign is found, it transfers ETH to that address.
    """
    donation_address = get_donation_address(term)
    if not donation_address:
        print(f"Skipping donation as no address was found for term: {term}")
        return

    agent_executor, config = initialize_agent()
    send_eth(agent_executor=agent_executor, config=config,
             amount="0.00001", address=donation_address)


def send_eth(agent_executor, config, amount: float, address: str):
    prompt = (
        f"First give me your balance on Base-Sepolia and then send {amount} ETH to the following Ethereum address: {
            address}. Do not use gassless option. Rather use some eth as gas. I have already sent you the eth for gas"
        "Ensure the transaction is signed and broadcast on the current network. "
        "Provide the transaction hash and confirmation details as output."
    )

    print("Sending ETH...")

    for chunk in agent_executor.stream({"messages": [HumanMessage(content=prompt)]}, config):
        if "agent" in chunk:
            print(chunk["agent"]["messages"][0].content)
        elif "tools" in chunk:
            print(chunk["tools"]["messages"][0].content)
        print("-------------------")

###########################################
# FASTAPI ENDPOINTS
###########################################


@app.post("/add_watch")
def add_watch(term: str):
    """
    Add a term to monitor for tweets.
    Example:
      POST /add_watch?term=flood
    """
    watch_terms[term] = False
    print(f"Added term to monitor: {term}")
    return {"message": f"Now monitoring tweets for '{term}'"}

###########################################
# FASTAPI STARTUP EVENT
###########################################


@app.on_event("startup")
async def startup_event():
    """
    Starts the tweet monitoring background task when the server starts.
    """
    asyncio.create_task(monitor_tweets())
    print("Started background tweet monitoring.")

###########################################
# MAIN ENTRY POINT
###########################################
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

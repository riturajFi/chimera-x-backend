import asyncio
import os
from fastapi import FastAPI, BackgroundTasks
from typing import Dict, List
from twikit import Client
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from cdp import Wallet, hash_message
from cdp_langchain.tools import CdpTool
from pydantic import BaseModel, Field
from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper

###########################################
# TWITTER SCRAPING CLIENT
###########################################
USERNAME = "@rituraj10x"
EMAIL = "riturajtripathy10x@gmail.com"
PASSWORD = "Rx2000!Rn"

# Initialize Twikit client
client = Client('en-US')

# Optionally load saved cookies if you have previously authenticated
client.load_cookies('cookies.json')

###########################################
# GLOBALS
###########################################
# Watch terms dictionary: key = search term, value = bool (whether found or not)
watch_terms: Dict[str, bool] = {}

# FastAPI instance
app = FastAPI()

###########################################
# BACKGROUND TASK: MONITORING TWEETS
###########################################
async def monitor_tweets():
    """
    Continuously monitors Twitter for each watch term.
    Logs success when a matching tweet is found.
    """
    while True:
        try:
            # Iterate through all watch terms
            for term, already_found in list(watch_terms.items()):
                if already_found:
                    continue  # Skip terms already satisfied

                # Search for latest tweets with the term
                print(f"Searching for tweets with term: {term}")
                tweets = await client.search_tweet(term, 'Latest')
                if not tweets:
                    continue

                # Check tweets for any additional criteria (e.g., likes, replies)
                for tweet in tweets:
                    # Example: Check if the tweet has at least 1 like
                    if tweet.favorite_count >= 0:
                        sendToken(term=term, tweet=tweet)
                        watch_terms[term] = True  # Mark term as found
                        break  # Stop checking further tweets for this term

            # Wait before the next check
            await asyncio.sleep(10)  # Adjust delay as needed

        except Exception as e:
            print(f"Error during monitoring: {e}")
            await asyncio.sleep(10)  # Retry after a delay

def initialize_agent():
    """Initialize the agent with CDP Agentkit."""
    # Initialize LLM.
    llm = ChatOpenAI(model="gpt-4o-mini")

    wallet_data = None
    wallet_data_file = "wallet_data.txt"

    if os.path.exists(wallet_data_file):
        with open(wallet_data_file) as f:
            wallet_data = f.read()

    # Configure CDP Agentkit Langchain Extension.
    values = {}
    if wallet_data is not None:
        # If there is a persisted agentic wallet, load it and pass to the CDP Agentkit Wrapper.
        values = {"cdp_wallet_data": wallet_data}

    agentkit = CdpAgentkitWrapper(**values)

    # persist the agent's CDP MPC Wallet Data.
    wallet_data = agentkit.export_wallet()
    with open(wallet_data_file, "w") as f:
        f.write(wallet_data)

    # Initialize CDP Agentkit Toolkit and get tools.
    cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(agentkit)
    tools = cdp_toolkit.get_tools()

    # Store buffered conversation history in memory.
    memory = MemorySaver()
    config = {"configurable": {"thread_id": "CDP Agentkit Chatbot Example!"}}

    # Create ReAct Agent using the LLM and CDP Agentkit tools.
    return create_react_agent(
        llm,
        tools=tools,
        checkpointer=memory,
        state_modifier=(
            "You are a helpful agent that can interact onchain using the Coinbase Developer Platform AgentKit. "
            "You are empowered to interact onchain using your tools. If you ever need funds, you can request "
            "them from the faucet if you are on network ID 'base-sepolia'. If not, you can provide your wallet "
            "details and request funds from the user. Before executing your first action, get the wallet details "
            "to see what network you're on. If there is a 5XX (internal) HTTP error code, ask the user to try "
            "again later. If someone asks you to do something you can't do with your currently available tools, "
            "you must say so, and encourage them to implement it themselves using the CDP SDK + Agentkit, "
            "recommend they go to docs.cdp.coinbase.com for more information. Be concise and helpful with your "
            "responses. Refrain from restating your tools' descriptions unless it is explicitly requested."
        ),
    ), config


#Send Money to Benificiary
def sendToken(term, tweet):
    agent_executor, config = initialize_agent()

    send_eth(agent_executor=agent_executor, config=config, amount="0.00001", address="0x7B133e5bce9552289Adb6B8a0449318De9C6C894")

def send_eth(agent_executor, config, amount: float, address: str):

    prompt = (
        f"First give me your balance on Base-Sepolia and then Send {amount} ETH to the following Ethereum address: {address}. "
        "Ensure the transaction is signed and broadcast on the current network. "
        "Provide the transaction hash and confirmation details as output."
    )

    print("Sending ETH...")

    for chunk in agent_executor.stream(
        {"messages": [HumanMessage(content=prompt)]}, config
    ):
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
    watch_terms[term] = False  # Initialize the term as "not found"
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

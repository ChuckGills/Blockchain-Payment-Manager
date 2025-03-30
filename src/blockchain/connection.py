from web3 import Web3
import os
from dotenv import load_dotenv
 ## USED TO DEBUG CONNECTIONS 
# Load environment variables from the .env file
load_dotenv()

# Retrieve the node URL from the environment
NODE_URL = os.getenv("BLOCKCHAIN_NODE_URL")

NODE_URL = "https://rpc.testnet-02.midnight.network"
# Debug: Check if NODE_URL is being loaded correctly
if NODE_URL is None:
    print("Error: BLOCKCHAIN_NODE_URL is not set. Please ensure your .env file is in the project directory and contains a valid URL.")
else:
    print("Using NODE_URL:", NODE_URL)

# Create a Web3 instance using the HTTP provider
w3 = Web3(Web3.HTTPProvider(NODE_URL))

# Check the connection status
try:
    if w3.is_connected():
        print("Connected to blockchain node!")
    else:
        print("Connection failed. Verify that your node is running and accessible.")
except Exception as e:
    print("An error occurred while checking the connection:", e)

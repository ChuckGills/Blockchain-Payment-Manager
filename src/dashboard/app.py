import streamlit as st
import streamlit.components.v1 as components
from web3 import Web3
import os
from dotenv import load_dotenv


NODE_URL = "https://sepolia.rpc.zkcandy.io"
w3 = Web3(Web3.HTTPProvider(NODE_URL))

if not w3.is_connected():
    st.error("Error: Could not connect to the blockchain node.")
else:
    st.success("Connected to blockchain node!")

# Dashboard Title
st.title("Decentralized Payment Protector Dashboard")

# --------------------------
# MetaMask Connection Section
# --------------------------
metamask_component = """
<html>
  <head>
    <script>
      async function connectMetaMask() {
        if (typeof window.ethereum !== 'undefined') {
          try {
            const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
            document.getElementById("walletAddress").value = accounts[0];
            document.getElementById("walletStatus").innerText = "Connected: " + accounts[0];
          } catch (error) {
            console.error("Error connecting to MetaMask:", error);
            document.getElementById("walletStatus").innerText = "Error connecting to MetaMask";
          }
        } else {
          alert("MetaMask is not installed. Please install MetaMask and try again.");
        }
      }
    </script>
  </head>
  <body>
    <button onclick="connectMetaMask()">Connect MetaMask</button>
    <input type="hidden" id="walletAddress" value="" />
    <div id="walletStatus">Not connected</div>
  </body>
</html>
"""

components.html(metamask_component, height=200)

# Input for wallet address (user should copy from the MetaMask connect component)
wallet_address = st.text_input("Wallet Address (copy from above)", "")

# Function to get wallet balance using Web3.py
def get_wallet_balance(address):
    try:
        balance = w3.eth.get_balance(address)
        return w3.fromWei(balance, 'ether')
    except Exception as e:
        st.error(f"Error fetching balance: {e}")
        return None

if wallet_address:
    balance = get_wallet_balance(wallet_address)
    if balance is not None:
        st.write(f"Wallet Balance: {balance} ETH")

# --------------------------
# Send Transaction Section
# --------------------------
action = st.selectbox("Choose Action", ["Select an action", "Send Transaction", "Create Escrow Transaction"])

if action == "Send Transaction":
    with st.form("send_transaction_form"):
        st.subheader("Send Transaction")
        to_address = st.text_input("Receiver Address", "0xReceiverAddress")
        amount_wei = st.number_input("Amount (in Wei)", value=1000000000)
        send_submitted = st.form_submit_button("Send Transaction")
        
        
        def fraud_check(recipient, amount):
            
            return False

        
        def send_transaction(sender, to, amount):
            # Here you would build and send a transaction using Web3.py
            # For demonstration, we return a dummy transaction hash.
            return "0xDUMMYTXHASH"

        if send_submitted:
            if wallet_address:
                if fraud_check(to_address, amount_wei):
                    st.error("Transaction flagged as fraudulent!")
                else:
                    tx_hash = send_transaction(wallet_address, to_address, amount_wei)
                    st.success(f"Transaction sent successfully! Hash: {tx_hash}")
            else:
                st.error("Please connect MetaMask to obtain a wallet address first.")

# --------------------------
# Create Escrow Transaction Form
# --------------------------

if action == "Create Escrow Transaction":
    with st.form("escrow_transaction_form"):
        st.subheader("Create Escrow Transaction")
        escrow_recipient = st.text_input("Escrow Recipient Address", "0xRecipient")
        escrow_amount = st.number_input("Escrow Amount (in Wei)", value=1000000000)
        escrow_submitted = st.form_submit_button("Create Escrow Transaction")
        
        # Dummy create escrow transaction function
        def create_escrow_transaction(sender, recipient, amount):
            # In production, interact with your escrow smart contract here.
            # For simulation, we return a dummy escrow transaction ID.
            return "escrow123"
        
        if escrow_submitted:
            if wallet_address:
                escrow_id = create_escrow_transaction(wallet_address, escrow_recipient, escrow_amount)
                st.success(f"Escrow transaction created with ID: {escrow_id}")
            else:
                st.error("Please connect MetaMask to obtain a wallet address first.")

# --------------------------
# Other Sections (Flag Wallet, Escrow Status, etc.)
# --------------------------
st.header("Flag Wallet")
flag_wallet_address = st.text_input("Wallet Address to Flag", wallet_address)
def flag_wallet(wallet):
    file=open("../../data/reported.txt","a")
    file.write(wallet+"\n")
    file.close()
    

if st.button("Flag Wallet"):
    if flag_wallet_address:
        if flag_wallet(flag_wallet_address):
            st.success(f"Wallet {flag_wallet_address} flagged successfully.")
        else:
            st.error("Failed to flag wallet.")
    else:
        st.error("Enter a wallet address to flag.")

st.header("Unfulfilled Escrow Purchases")
def get_unfulfilled_escrows():
    # Replace with a call to your escrow contract or backend
    return [
        {"escrow_id": "escrow001", "buyer": "0xabc...", "amount": "0.5 ETH"},
        {"escrow_id": "escrow002", "buyer": "0xdef...", "amount": "1.2 ETH"},
    ]

if st.button("Refresh Escrow Purchases"):
    unfulfilled_escrows = get_unfulfilled_escrows()
    st.write(unfulfilled_escrows)
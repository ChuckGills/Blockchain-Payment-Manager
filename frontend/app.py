import streamlit as st
import requests
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure page settings
st.set_page_config(
    page_title="Midnight Dashboard",
    
    layout="wide"
)

# Constants
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000")

# Session state initialization
if "wallet_id" not in st.session_state:
    st.session_state.wallet_id = None
if "wallet_address" not in st.session_state:
    st.session_state.wallet_address = None

# Page title
st.title("Midnight Secure Payment HUB")

# --------------------------
# Sidebar: Wallet Connection via Midnight Wallet
# --------------------------
with st.sidebar:
    st.header("Midnight Wallet Connection")
    
    # Display connected wallet info if available
    if st.session_state.wallet_address:
        st.success(f"Connected: {st.session_state.wallet_address}")
        
        # Get balance
        try:
            response = requests.get(
                f"{BACKEND_URL}/get-balance",
                params={"walletId": st.session_state.wallet_id}
            )
            if response.status_code == 200:
                balance = response.json()["balance"]
                st.metric("Balance", f"{balance} tDUST")
        except Exception as e:
            st.error(f"Error fetching balance: {str(e)}")
        
        # Disconnect button
        if st.button("Disconnect Wallet"):
            try:
                # Close wallet on backend
                requests.post(
                    f"{BACKEND_URL}/close-wallet",
                    json={"walletId": st.session_state.wallet_id}
                )
                # Clear session state
                st.session_state.wallet_id = None
                st.session_state.wallet_address = None
                st.rerun()
            except Exception as e:
                st.error(f"Error disconnecting: {str(e)}")
    
    # Wallet connection options if not connected
    else:
        st.info("Please connect your wallet to continue")
        connection_option = st.radio(
            "Connection Method:",
            ["Create New Wallet", "Connect with Seed", "Restore from Snapshot"]
        )
        
        if connection_option == "Create New Wallet":
            if st.button("Create Wallet"):
                with st.spinner("Creating new wallet..."):
                    try:
                        response = requests.post(f"{BACKEND_URL}/create-wallet")
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.wallet_id = data["walletId"]
                            st.session_state.wallet_address = data["address"]
                            st.rerun()
                        else:
                            st.error("Failed to create wallet")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        
        elif connection_option == "Connect wallet":
            with st.form("seed_form"):
                seed = st.text_input("Enter Wallet Addr", type="password")
                submit = st.form_submit_button("Connect")
                
                if submit and seed:
                    with st.spinner("Connecting wallet..."):
                        try:
                            response = requests.post(
                                f"{BACKEND_URL}/connect-wallet-seed",
                                json={"seed": seed}
                            )
                            if response.status_code == 200:
                                data = response.json()
                                st.session_state.wallet_id = data["walletId"]
                                st.session_state.wallet_address = data["address"]
                                st.rerun()
                            else:
                                st.error("Failed to connect wallet")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            
        elif connection_option == "Restore from Snapshot":
            with st.form("snapshot_form"):
                snapshot = st.text_area("Paste Wallet Snapshot")
                submit = st.form_submit_button("Restore")
                
                if submit and snapshot:
                    with st.spinner("Restoring wallet..."):
                        try:
                            response = requests.post(
                                f"{BACKEND_URL}/restore-wallet",
                                json={"snapshot": snapshot}
                            )
                            if response.status_code == 200:
                                data = response.json()
                                st.session_state.wallet_id = data["walletId"]
                                st.session_state.wallet_address = data["address"]
                                st.rerun()
                            else:
                                st.error("Failed to restore wallet")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")


if st.session_state.wallet_address:
    st.success("Wallet connected successfully!")
    
    tab1, tab2, tab3 = st.tabs(["Send Transaction", "Escrow", "Wallet Management"])
    
    with tab1:
        st.header("Send Transaction")

        if "warning_shown" not in st.session_state:
            st.session_state.warning_shown = False
            st.session_state.warning_message = ""
            st.session_state.transaction_data = {}

        if st.session_state.warning_shown:
            st.warning(st.session_state.warning_message)

            col1, col2 = st.columns(2)

            with col1:
                with st.form("cancel_form"):
                    cancel_submit = st.form_submit_button("Cancel Transaction")
                    if cancel_submit:
                        st.session_state.warning_shown = False
                        st.info("Transaction cancelled")
                        st.rerun()

            with col2:
                with st.form("proceed_form"):
                    proceed_submit = st.form_submit_button("Proceed Anyway")
                    if proceed_submit:
                        with st.spinner("Processing transaction with confirmation..."):
                            try:
                                transaction_data = st.session_state.transaction_data

                                confirm_response = requests.post(
                                    f"{BACKEND_URL}/send-transaction",
                                    json={
                                        "walletId": st.session_state.wallet_id,
                                        "receiverAddress": transaction_data["receiverAddress"],
                                        "amount": transaction_data["amount"],
                                        "memo": transaction_data.get("memo", ""),
                                        "bypassWarning": True
                                    }
                                )

                                if confirm_response.status_code == 200:
                                    data = confirm_response.json()
                                    st.success(f"Transaction sent! Hash: {data['transactionHash']}")
                                    st.session_state.warning_shown = False
                                else:
                                    error_data = confirm_response.json()
                                    st.error(f"Transaction failed: {error_data.get('message', 'Unknown error')}")
                            except Exception as e:
                                st.error(f"Error sending transaction: {str(e)}")

        else:
            with st.form("send_form"):
                recipient = st.text_input("Recipient Address")
                amount = st.number_input("Amount (tDUST)", min_value=0.000001, value=1.0, step=0.1, format="%.6f")
                memo = st.text_input("Memo (Optional)")

                submit_tx = st.form_submit_button("Send Transaction")

                if submit_tx:
                    if not recipient:
                        st.error("Please enter a recipient address")
                    elif amount <= 0:
                        st.error("Amount must be greater than 0")
                    else:
                        with st.spinner("Processing transaction... This may take up to a minute for ZK proof generation"):
                            try:
                                amount_in_smallest_unit = str(int(amount * 1_000_000))

                                response = requests.post(
                                    f"{BACKEND_URL}/send-transaction",
                                    json={
                                        "walletId": st.session_state.wallet_id,
                                        "receiverAddress": recipient,
                                        "amount": amount_in_smallest_unit,
                                        "memo": memo,
                                        "bypassWarning": False
                                    }
                                )

                                if response.status_code == 400 and response.json().get("status") == "warning":
                                    warning_data = response.json()
                                    st.session_state.warning_shown = True
                                    st.session_state.warning_message = warning_data["message"]
                                    st.session_state.transaction_data = {
                                        "receiverAddress": recipient,
                                        "amount": amount_in_smallest_unit,
                                        "memo": memo
                                    }
                                    st.rerun()
                                elif response.status_code == 200:
                                    data = response.json()
                                    st.success(f"Transaction sent! Hash: {data['transactionHash']}")
                                else:
                                    error_data = response.json()
                                    st.error(f"Transaction failed: {error_data.get('message', 'Unknown error')}")
                            except Exception as e:
                                st.error(f"Error sending transaction: {str(e)}")

    with tab2:
        st.header("Escrow Transactions")

        
        escrow_tabs = st.tabs(["Create Escrow", "My Escrows"])

        with escrow_tabs[0]:
            st.subheader("Create New Escrow Payment")
            st.info("Escrow holds funds until both parties approve the transaction")

            with st.form("escrow_form"):
                recipient = st.text_input("Recipient Address")
                amount = st.number_input("Amount (tDUST)", min_value=0.000001, value=1.0, step=0.1, format="%.6f")
                
                
                arbiter = st.text_input("Arbiter Address ", )
                memo = st.text_input("Memo/Notes (Optional)")

                submit_escrow = st.form_submit_button("Create Escrow")

                if submit_escrow:
                    if not recipient:
                        st.error("Please enter a recipient address")
                    elif amount <= 0:
                        st.error("Amount must be greater than 0")
                   
                    else:
                        with st.spinner("Creating escrow... This may take a minute"):
                            try:
                                # Convert to smallest unit
                                amount_in_smallest_unit = str(int(amount * 1_000_000))

                                payload = {
                                    "walletId": st.session_state.wallet_id,
                                    "receiverAddress": recipient,
                                    "amount": amount_in_smallest_unit,
                                    "memo": memo
                                }

                                
                                payload["arbiterAddress"] = arbiter

                                response = requests.post(
                                    f"{BACKEND_URL}/create-escrow",
                                    json=payload
                                )

                                if response.status_code == 200:
                                    data = response.json()
                                    st.success(f"Escrow created! ID: {data['escrowId']}")
                                    st.info("Funds have been locked in escrow")
                                else:
                                    error_data = response.json()
                                    st.error(f"Escrow creation failed: {error_data.get('message', 'Unknown error')}")
                            except Exception as e:
                                st.error(f"Error creating escrow: {str(e)}")

        with escrow_tabs[1]:
            st.subheader("My Escrow Transactions")

            if st.button("Refresh Escrow List"):
                st.rerun()

            # Create tabs for sent, received, and arbiter roles
            role_tabs = st.tabs(["As Buyer", "As Seller", "As Arbiter"])

            with role_tabs[0]:
                st.subheader("Escrows Where You Are the Buyer")

                # Fetch escrows where user is buyer
                try:
                    response = requests.get(
                        f"{BACKEND_URL}/get-escrows",
                        params={"walletId": st.session_state.wallet_id, "role": "buyer"}
                    )

                    if response.status_code == 200:
                        escrows = response.json()["escrows"]

                        if escrows:
                            for escrow in escrows:
                                with st.container():
                                    # Display basic escrow information
                                    st.markdown(f"**Escrow ID:** {escrow['id']}")
                                    st.markdown(f"**Seller:** {escrow['seller']}")
                                    st.markdown(f"**Amount:** {int(escrow['amount'])/1_000_000} tDUST")
                                    st.markdown(f"**Created:** {escrow['createdAt']}")
                                    if 'arbiter' in escrow and escrow['arbiter']:
                                        st.markdown(f"**Arbiter:** {escrow['arbiter']}")
                                    if escrow.get('memo'):
                                        st.markdown(f"**Memo:** {escrow['memo']}")

                                    # Display status
                                    status_color = "red"
                                    if escrow['fundsReleased']:
                                        status = "Funds Released"
                                        status_color = "green"
                                    elif escrow['disputeRaised']:
                                        status = "Dispute Raised"
                                        status_color = "orange"
                                    elif escrow['buyerApproved'] and escrow['sellerApproved']:
                                        status = "Both Approved (Ready to Release)"
                                        status_color = "blue"
                                    elif escrow['buyerApproved']:
                                        status = "Buyer Approved (Awaiting Seller)"
                                        status_color = "blue"
                                    elif escrow['sellerApproved']:
                                        status = "Seller Approved (Awaiting Buyer)"
                                        status_color = "blue"
                                    else:
                                        status = "Pending Approval"

                                    st.markdown(f"**Status:** :{status_color}[{status}]")

                                    # Action buttons
                                    col1, col2, col3 = st.columns(3)

                                    with col1:
                                        approve_disabled = escrow['buyerApproved'] or escrow['fundsReleased']
                                        if st.button("Approve", key=f"approve_buyer_{escrow['id']}", 
                                                    disabled=approve_disabled):
                                            with st.spinner("Approving escrow..."):
                                                try:
                                                    response = requests.post(
                                                        f"{BACKEND_URL}/approve-escrow",
                                                        json={
                                                            "walletId": st.session_state.wallet_id,
                                                            "escrowId": escrow['id'],
                                                            "role": "buyer"
                                                        }
                                                    )

                                                    if response.status_code == 200:
                                                        st.success("Escrow approved!")
                                                        st.rerun()
                                                    else:
                                                        error_data = response.json()
                                                        st.error(f"Approval failed: {error_data.get('message', 'Unknown error')}")
                                                except Exception as e:
                                                    st.error(f"Error: {str(e)}")

                                    with col2:
                                        # Release button (enabled only if both approved and no dispute)
                                        release_disabled = not (escrow['buyerApproved'] and escrow['sellerApproved']) or escrow['disputeRaised'] or escrow['fundsReleased']
                                        if st.button("Release Funds", key=f"release_{escrow['id']}", 
                                                    disabled=release_disabled):
                                            with st.spinner("Releasing funds..."):
                                                try:
                                                    response = requests.post(
                                                        f"{BACKEND_URL}/release-escrow",
                                                        json={
                                                            "walletId": st.session_state.wallet_id,
                                                            "escrowId": escrow['id']
                                                        }
                                                    )

                                                    if response.status_code == 200:
                                                        st.success("Funds released!")
                                                        st.rerun()
                                                    else:
                                                        error_data = response.json()
                                                        st.error(f"Release failed: {error_data.get('message', 'Unknown error')}")
                                                except Exception as e:
                                                    st.error(f"Error: {str(e)}")

                                    with col3:
                                        dispute_disabled = escrow['disputeRaised'] or escrow['fundsReleased']
                                        if st.button("Raise Dispute", key=f"dispute_buyer_{escrow['id']}", 
                                                   disabled=dispute_disabled):
                                            with st.spinner("Raising dispute..."):
                                                try:
                                                    response = requests.post(
                                                        f"{BACKEND_URL}/raise-dispute",
                                                        json={
                                                            "walletId": st.session_state.wallet_id,
                                                            "escrowId": escrow['id']
                                                        }
                                                    )

                                                    if response.status_code == 200:
                                                        st.success("Dispute raised! The arbiter will review.")
                                                        st.rerun()
                                                    else:
                                                        error_data = response.json()
                                                        st.error(f"Failed to raise dispute: {error_data.get('message', 'Unknown error')}")
                                                except Exception as e:
                                                    st.error(f"Error: {str(e)}")

                                    st.divider()
                        else:
                            st.info("You don't have any escrows as a buyer")

                except Exception as e:
                    st.error(f"Error loading escrows: {str(e)}")

            with role_tabs[1]:
                st.subheader("Escrows Where You Are the Seller")

                try:
                    response = requests.get(
                        f"{BACKEND_URL}/get-escrows",
                        params={"walletId": st.session_state.wallet_id, "role": "seller"}
                    )

                    if response.status_code == 200:
                        escrows = response.json()["escrows"]

                        if escrows:
                            for escrow in escrows:
                                with st.container():
                                    st.markdown(f"**Escrow ID:** {escrow['id']}")
                                    st.markdown(f"**Buyer:** {escrow['buyer']}")
                                    st.markdown(f"**Amount:** {int(escrow['amount'])/1_000_000} tDUST")
                                    st.markdown(f"**Created:** {escrow['createdAt']}")
                                    if 'arbiter' in escrow and escrow['arbiter']:
                                        st.markdown(f"**Arbiter:** {escrow['arbiter']}")
                                    if escrow.get('memo'):
                                        st.markdown(f"**Memo:** {escrow['memo']}")

                                    
                                    status_color = "red"
                                    if escrow['fundsReleased']:
                                        status = "Funds Released"
                                        status_color = "green"
                                    elif escrow['disputeRaised']:
                                        status = "Dispute Raised"
                                        status_color = "orange"
                                    elif escrow['buyerApproved'] and escrow['sellerApproved']:
                                        status = "Both Approved (Ready to Release)"
                                        status_color = "blue"
                                    elif escrow['buyerApproved']:
                                        status = "Buyer Approved (Awaiting Seller)"
                                        status_color = "blue"
                                    elif escrow['sellerApproved']:
                                        status = "Seller Approved (Awaiting Buyer)"
                                        status_color = "blue"
                                    else:
                                        status = "Pending Approval"

                                    st.markdown(f"**Status:** :{status_color}[{status}]")

                                    # Action buttons
                                    col1, col2 = st.columns(2)

                                    with col1:
                                        approve_disabled = escrow['sellerApproved'] or escrow['fundsReleased']
                                        if st.button("Approve", key=f"approve_seller_{escrow['id']}", 
                                                    disabled=approve_disabled):
                                            with st.spinner("Approving escrow..."):
                                                try:
                                                    response = requests.post(
                                                        f"{BACKEND_URL}/approve-escrow",
                                                        json={
                                                            "walletId": st.session_state.wallet_id,
                                                            "escrowId": escrow['id'],
                                                            "role": "seller"
                                                        }
                                                    )

                                                    if response.status_code == 200:
                                                        st.success("Escrow approved!")
                                                        st.rerun()
                                                    else:
                                                        error_data = response.json()
                                                        st.error(f"Approval failed: {error_data.get('message', 'Unknown error')}")
                                                except Exception as e:
                                                    st.error(f"Error: {str(e)}")

                                    with col2:
                                        dispute_disabled = escrow['disputeRaised'] or escrow['fundsReleased']
                                        if st.button("Raise Dispute", key=f"dispute_seller_{escrow['id']}", 
                                                   disabled=dispute_disabled):
                                            with st.spinner("Raising dispute..."):
                                                try:
                                                    response = requests.post(
                                                        f"{BACKEND_URL}/raise-dispute",
                                                        json={
                                                            "walletId": st.session_state.wallet_id,
                                                            "escrowId": escrow['id']
                                                        }
                                                    )

                                                    if response.status_code == 200:
                                                        st.success("Dispute raised! The arbiter will review.")
                                                        st.rerun()
                                                    else:
                                                        error_data = response.json()
                                                        st.error(f"Failed to raise dispute: {error_data.get('message', 'Unknown error')}")
                                                except Exception as e:
                                                    st.error(f"Error: {str(e)}")

                                    st.divider()
                        else:
                            st.info("You don't have any escrows as a seller")

                except Exception as e:
                    st.error(f"Error loading escrows: {str(e)}")

            with role_tabs[2]:
                st.subheader("Escrows Where You Are the Arbiter")

                # Fetch escrows where user is arbiter
                try:
                    response = requests.get(
                        f"{BACKEND_URL}/get-escrows",
                        params={"walletId": st.session_state.wallet_id, "role": "arbiter"}
                    )

                    if response.status_code == 200:
                        escrows = response.json()["escrows"]

                        if escrows:
                            for escrow in escrows:
                                with st.container():
                                    # Display basic escrow information
                                    st.markdown(f"**Escrow ID:** {escrow['id']}")
                                    st.markdown(f"**Buyer:** {escrow['buyer']}")
                                    st.markdown(f"**Seller:** {escrow['seller']}")
                                    st.markdown(f"**Amount:** {int(escrow['amount'])/1_000_000} tDUST")
                                    st.markdown(f"**Created:** {escrow['createdAt']}")
                                    if escrow.get('memo'):
                                        st.markdown(f"**Memo:** {escrow['memo']}")

                                    # Display dispute status
                                    if escrow['fundsReleased']:
                                        st.markdown("**Status:** :green[Funds Released]")
                                    elif escrow['disputeRaised']:
                                        st.markdown("**Status:** :orange[Dispute Raised - Needs Resolution]")

                                        # Show arbiter resolution controls
                                        st.subheader("Resolve Dispute")
                                        st.write("As the arbiter, you can resolve this dispute by deciding which party deserves the funds.")

                                        deserving_party = st.radio(
                                            "Select the deserving party:", 
                                            ["Buyer", "Seller"],
                                            key=f"party_{escrow['id']}"
                                        )

                                        if st.button("Resolve Dispute", key=f"resolve_{escrow['id']}"):
                                            with st.spinner("Resolving dispute..."):
                                                try:
                                                    response = requests.post(
                                                        f"{BACKEND_URL}/resolve-dispute",
                                                        json={
                                                            "walletId": st.session_state.wallet_id,
                                                            "escrowId": escrow['id'],
                                                            "deservingParty": deserving_party.lower()
                                                        }
                                                    )

                                                    if response.status_code == 200:
                                                        st.success(f"Dispute resolved in favor of the {deserving_party}!")
                                                        st.rerun()
                                                    else:
                                                        error_data = response.json()
                                                        st.error(f"Resolution failed: {error_data.get('message', 'Unknown error')}")
                                                except Exception as e:
                                                    st.error(f"Error: {str(e)}")
                                    else:
                                        st.markdown("**Status:** :blue[No Dispute Raised]")

                                    st.divider()
                        else:
                            st.info("You don't have any escrows as an arbiter")

                except Exception as e:
                    st.error(f"Error loading escrows: {str(e)}")


    with tab3:
        st.header("Wallet Management")
        
        if st.button("Create Backup Snapshot"):
            with st.spinner("Creating wallet snapshot..."):
                try:
                    response = requests.get(
                        f"{BACKEND_URL}/create-snapshot",
                        params={"walletId": st.session_state.wallet_id}
                    )
                    
                    if response.status_code == 200:
                        snapshot_data = response.json()["snapshot"]
                        st.code(snapshot_data)
                        st.info("Copy and store this snapshot securely. It contains your private keys.")
                    else:
                        st.error("Failed to create snapshot")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        with st.expander("Report Fraudulent Transaction"):
            st.info("Use this form to report an address involved in a fraudulent transaction. This will add the address to our database of reported addresses, warning other users who attempt to send funds to this address.")

            with st.form("report_fraud_form"):
                reported_address = st.text_input("Fraudulent Address", placeholder="Enter Midnight wallet address")
                reason = st.text_area("Reason for Report", placeholder="Briefly describe the fraudulent activity")

                submit_report = st.form_submit_button("Submit Report")

                if submit_report:
                    if not reported_address:
                        st.error("Please enter an address to report")
                    
                    else:
                        with st.spinner("Submitting report..."):
                            try:
                                response = requests.post(
                                    f"{BACKEND_URL}/report-address",
                                    json={
                                        "address": reported_address,
                                        "reason": reason
                                    }
                                )

                                if response.status_code == 200:
                                    st.success("Address reported successfully!")
                                    st.info("Other users will now be warned when attempting to send funds to this address.")
                                else:
                                    error_data = response.json()
                                    st.error(f"Failed to report address: {error_data.get('message', 'Unknown error')}")
                            except Exception as e:
                                st.error(f"Error submitting report: {str(e)}")
else:
   
    st.info("👈 Please connect your Midnight wallet using the sidebar")
    st.markdown("""
    ## Welcome to the Midnight Wallet Dashboard
    
    This application allows you to:
    
    - Create a new Midnight wallet or connect an existing one
    - Send private transactions using zero-knowledge proofs
    - Manage escrow transactions
    - Back up your wallet with snapshots
    
    Connect your wallet to get started!
    """)
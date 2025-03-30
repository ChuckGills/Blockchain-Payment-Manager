from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()
NODE_URL = os.getenv("BLOCKCHAIN_NODE_URL")
w3 = Web3(Web3.HTTPProvider(NODE_URL))
PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")

def send_transaction(to_address, amount):
    account = w3.eth.account.privateKeyToAccount(PRIVATE_KEY)
    transaction = {
        'to': to_address,
        'value': amount,
        'gas': 2000000,
        'gasPrice': w3.toWei('50', 'gwei'),
        'nonce': w3.eth.getTransactionCount(account.address),
    }
    signed_tx = account.sign_transaction(transaction)
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
    return tx_hash.hex()

if __name__ == "__main__":

    tx_hash = send_transaction("0xReceiverAddress", 1000000000000000000)
    print("Transaction sent with hash:", tx_hash)
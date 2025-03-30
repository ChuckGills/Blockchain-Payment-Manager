class Escrow:
    def __init__(self):
        self.escrow_data = {}

    def lock_funds(self, tx_id, amount):
        self.escrow_data[tx_id] = {"amount": amount, "status": "locked"}
        return True

    def release_funds(self, tx_id):
        if tx_id in self.escrow_data:
            self.escrow_data[tx_id]["status"] = "released"
            return True
        return False

    def get_status(self, tx_id):
        return self.escrow_data.get(tx_id, None)


if __name__ == "__main__":
    escrow = Escrow()
    escrow.lock_funds("0xabc123", 1500)
    print("Escrow Status:", escrow.get_status("0xabc123"))
    escrow.release_funds("0xabc123")
    print("Escrow Status after release:", escrow.get_status("0xabc123"))
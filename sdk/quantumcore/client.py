import json
import os
from web3 import Web3

class QuantumCoreClient:
    def __init__(self, rpc_url: str = "https://sepolia.gateway.tenderly.co", private_key: str = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.private_key = private_key or "0xedbe2e1b7d566039dddb9d3e72559ebc56fe0472cf49b09eb59a79d5c37751cf"
        self.account = self.w3.eth.account.from_key(self.private_key)

        # Load broadcast artifacts
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        broadcast_path = os.path.join(base_dir, "broadcast/Deploy.s.sol/11155111/run-latest.json")
        vault_abi_path = os.path.join(base_dir, "out/QuantumVault.sol/QuantumVault.json")

        with open(broadcast_path) as f:
            broadcast = json.load(f)

        self.vault_address = Web3.to_checksum_address(broadcast["transactions"][1]["contractAddress"])

        with open(vault_abi_path) as f:
            vault_abi = json.load(f)["abi"]

        self.vault = self.w3.eth.contract(address=self.vault_address, abi=vault_abi)

    def get_limits(self):
        max_tx = self.vault.functions.maxPerTx().call() / 1e6
        hourly_cap = self.vault.functions.hourlyCap().call() / 1e6
        spent = self.vault.functions.spentThisHour().call() / 1e6
        return {"max_per_tx": max_tx, "hourly_cap": hourly_cap, "spent_this_hour": spent}

    def pay(self, recipient: str, amount_usd: float):
        recipient_cs = Web3.to_checksum_address(recipient)
        units = int(amount_usd * 1e6)

        max_units = self.vault.functions.maxPerTx().call()
        if units > max_units:
            raise ValueError(f"Exceeds max per-tx limit of ${max_units / 1e6:.2f}")

        base_fee = self.w3.eth.get_block("latest")["baseFeePerGas"]
        priority_fee = self.w3.to_wei(2, "gwei")

        tx = self.vault.functions.pay(recipient_cs, units).build_transaction({
            "chainId": 11155111,
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 160000,
            "maxFeePerGas": int(base_fee * 2) + priority_fee,
            "maxPriorityFeePerGas": priority_fee
        })

        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        raw_tx = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return {
            "status": "confirmed",
            "tx_hash": tx_hash.hex(),
            "block_number": receipt.blockNumber,
            "explorer_url": f"https://sepolia.etherscan.io/tx/{tx_hash.hex()}"
        }

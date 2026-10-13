import json
import glob
from web3 import Web3
from dataclasses import dataclass

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

# 1. Load contract configuration
run_files = sorted(glob.glob("broadcast/Deploy.s.sol/31337/run-latest.json"))
with open(run_files[-1]) as f:
    broadcast_data = json.load(f)

TOKEN_ADDR = Web3.to_checksum_address(broadcast_data["transactions"][0]["contractAddress"])
VAULT_ADDR = Web3.to_checksum_address(broadcast_data["transactions"][1]["contractAddress"])

with open("out/QuantumVault.sol/QuantumVault.json") as f:
    VAULT_ABI = json.load(f)["abi"]

vault_contract = w3.eth.contract(address=VAULT_ADDR, abi=VAULT_ABI)

# Agent Session Key (Anvil Account 1)
AGENT_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
agent_account = w3.eth.account.from_key(AGENT_KEY)

def quantumcore_pay(recipient_address: str, amount_usd: float) -> str:
    """
    Standard Tool: Allows an AI agent to execute payments through QuantumCore.
    Enforces spending limits on-chain.
    """
    try:
        recipient = Web3.to_checksum_address(recipient_address)
        amount_units = int(amount_usd * 1e6)

        # Pre-check: Ensure within policy before signing
        max_tx = vault_contract.functions.maxPerTx().call()
        if amount_units > max_tx:
            return f"REJECTED: ${amount_usd:.2f} exceeds single transaction cap of ${max_tx / 1e6:.2f}"

        # Sign and execute payment
        tx = vault_contract.functions.pay(recipient, amount_units).build_transaction({
            'from': agent_account.address,
            'nonce': w3.eth.get_transaction_count(agent_account.address),
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })

        signed = w3.eth.account.sign_transaction(tx, AGENT_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return (
            f"SUCCESS: Paid ${amount_usd:.2f} to {recipient[:8]}... "
            f"(Tx: {tx_hash.hex()[:10]}... in block #{receipt.blockNumber})"
        )
    except Exception as e:
        return f"EXECUTION FAILED: {str(e)}"

# Direct test run
if __name__ == "__main__":
    merchant = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
    
    print("--- Test 1: Agent pays valid invoice ($1.50) ---")
    print(quantumcore_pay(merchant, 1.50))
    
    print("\n--- Test 2: Agent attempts rogue transaction exceeding limit ($15.00) ---")
    print(quantumcore_pay(merchant, 15.00))

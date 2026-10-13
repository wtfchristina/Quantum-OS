import json
from web3 import Web3

RPC_URL = "https://sepolia.gateway.tenderly.co"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# 1. Load addresses and compiled ABI
with open("broadcast/Deploy.s.sol/11155111/run-latest.json") as f:
    broadcast_data = json.load(f)

TOKEN_ADDR = Web3.to_checksum_address(broadcast_data["transactions"][0]["contractAddress"])
VAULT_ADDR = Web3.to_checksum_address(broadcast_data["transactions"][1]["contractAddress"])

with open("out/QuantumVault.sol/QuantumVault.json") as f:
    VAULT_ABI = json.load(f)["abi"]

vault = w3.eth.contract(address=VAULT_ADDR, abi=VAULT_ABI)

# Use your funded deployer account (holds 0.125 SepETH for gas)
SIGNER_KEY = "0xedbe2e1b7d566039dddb9d3e72559ebc56fe0472cf49b09eb59a79d5c37751cf"
signer_account = w3.eth.account.from_key(SIGNER_KEY)

def agent_pay(recipient_address: str, amount_usd: float) -> str:
    try:
        recipient = Web3.to_checksum_address(recipient_address)
        amount_units = int(amount_usd * 1e6)

        # Off-chain precheck against smart contract policy
        max_tx = vault.functions.maxPerTx().call()
        if amount_units > max_tx:
            return f"[DENIED] ${amount_usd:.2f} exceeds per-transaction limit of ${max_tx / 1e6:.2f}"

        # Dynamic fee calculation for Sepolia
        base_fee = w3.eth.get_block("latest")["baseFeePerGas"]
        priority_fee = w3.to_wei(2, "gwei")
        max_fee = int(base_fee * 2) + priority_fee

        nonce = w3.eth.get_transaction_count(signer_account.address)

        tx = vault.functions.pay(recipient, amount_units).build_transaction({
            "chainId": 11155111,
            "from": signer_account.address,
            "nonce": nonce,
            "gas": 160000,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee
        })

        signed = w3.eth.account.sign_transaction(tx, SIGNER_KEY)
        raw_tx = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
        tx_hash = w3.eth.send_raw_transaction(raw_tx)

        print(f"Broadcasted to Sepolia: {tx_hash.hex()}")
        print("Waiting for block inclusion...")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        spent_hour = vault.functions.spentThisHour().call()

        return (
            f"[CONFIRMED] Paid ${amount_usd:.2f} in Block #{receipt.blockNumber}\n"
            f"Explorer: https://sepolia.etherscan.io/tx/{tx_hash.hex()}\n"
            f"Hourly Spent: ${spent_hour / 1e6:.2f} / ${vault.functions.hourlyCap().call() / 1e6:.2f}"
        )
    except Exception as e:
        return f"[FAILED] {str(e)}"

if __name__ == "__main__":
    test_vendor = "0x000000000000000000000000000000000000dEaD"

    print(f"Signer Address: {signer_account.address}")
    print(f"Signer Balance: {w3.from_wei(w3.eth.get_balance(signer_account.address), 'ether')} ETH")

    print("\n--- Test 1: Limit Violation Guardrail ($10.00 > $5.00 cap) ---")
    print(agent_pay(test_vendor, 10.00))

    print("\n--- Test 2: Live Sepolia Settlement ($1.25) ---")
    print(agent_pay(test_vendor, 1.25))

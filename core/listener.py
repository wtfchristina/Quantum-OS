import json
import time
from web3 import Web3

RPC_URL = "https://sepolia.gateway.tenderly.co"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

with open("broadcast/Deploy.s.sol/11155111/run-latest.json") as f:
    broadcast_data = json.load(f)

VAULT_ADDR = Web3.to_checksum_address(broadcast_data["transactions"][1]["contractAddress"])

with open("out/QuantumVault.sol/QuantumVault.json") as f:
    VAULT_ABI = json.load(f)["abi"]

vault = w3.eth.contract(address=VAULT_ADDR, abi=VAULT_ABI)

print("==================================================")
print("     QUANTUMCORE LIVE ON-CHAIN EVENT MONITOR      ")
print("==================================================")
print(f"Tracking Vault Contract: {VAULT_ADDR}")
print(f"Network               : Ethereum Sepolia (11155111)")
print("Listening for incoming blocks and payment logs...\n")

last_block = w3.eth.block_number - 5

try:
    while True:
        current_block = w3.eth.block_number
        if current_block > last_block:
            # Query PaymentExecuted events over the recent window
            events = vault.events.PaymentExecuted.get_logs(
                from_block=last_block + 1,
                to_block=current_block
            )
            for ev in events:
                tx_hash = ev.transactionHash.hex()
                recipient = ev.args.recipient
                amount_usd = ev.args.amount / 1e6
                spent_hour = ev.args.spentThisHour / 1e6
                print(">>> [SETTLEMENT DETECTED]")
                print(f"    Block      : #{ev.blockNumber}")
                print(f"    Recipient  : {recipient}")
                print(f"    Amount     : ${amount_usd:.2f}")
                print(f"    Spent Hour : ${spent_hour:.2f}")
                print(f"    Tx Hash    : https://sepolia.etherscan.io/tx/{tx_hash}\n")
            
            last_block = current_block
        time.sleep(4)
except KeyboardInterrupt:
    print("\nListener stopped.")

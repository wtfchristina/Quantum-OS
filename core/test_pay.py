import json
import glob
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

# 1. Load deployed contract addresses from Foundry broadcast
run_files = sorted(glob.glob("broadcast/Deploy.s.sol/31337/run-latest.json"))
with open(run_files[-1]) as f:
    broadcast_data = json.load(f)

# Convert broadcast addresses to checksum format
token_address = Web3.to_checksum_address(broadcast_data["transactions"][0]["contractAddress"])
vault_address = Web3.to_checksum_address(broadcast_data["transactions"][1]["contractAddress"])

# 2. Load the official compiled ABI directly from Foundry
with open("out/QuantumVault.sol/QuantumVault.json") as f:
    vault_artifact = json.load(f)
vault_abi = vault_artifact["abi"]

# Minimal ERC20 ABI for balance checks
erc20_abi = [
    {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}
]

vault = w3.eth.contract(address=vault_address, abi=vault_abi)
token = w3.eth.contract(address=token_address, abi=erc20_abi)

AGENT_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
agent = w3.eth.account.from_key(AGENT_KEY)
merchant = Web3.to_checksum_address("0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC")

print("--- QuantumVault Connected ---")
print(f"Vault Address   : {vault_address}")
print(f"Initial Vault Balance: ${token.functions.balanceOf(vault_address).call() / 1e6:.2f}")

# 3. Agent executes a $2.50 payment
payment_amount = int(2.50 * 1e6)
tx = vault.functions.pay(merchant, payment_amount).build_transaction({
    'from': agent.address,
    'nonce': w3.eth.get_transaction_count(agent.address),
    'gas': 200000,
    'gasPrice': w3.eth.gas_price
})

signed = w3.eth.account.sign_transaction(tx, AGENT_KEY)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

print(f"\n[SUCCESS] Paid $2.50 to Merchant!")
print(f"Tx Hash         : {tx_hash.hex()}")
print(f"Merchant Balance: ${token.functions.balanceOf(merchant).call() / 1e6:.2f}")
print(f"Vault Remaining : ${token.functions.balanceOf(vault_address).call() / 1e6:.2f}")
print(f"Spent This Hour : ${vault.functions.spentThisHour().call() / 1e6:.2f}")

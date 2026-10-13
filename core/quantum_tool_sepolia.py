import json
import glob
from web3 import Web3

# Connect to Sepolia public RPC
RPC_URL = "https://ethereum-sepolia-rpc.publicnode.com"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Load public deployment data (Chain ID 11155111 = Ethereum Sepolia)
with open("broadcast/Deploy.s.sol/11155111/run-latest.json") as f:
    broadcast_data = json.load(f)

# Transactions: 0 = TestUSD deploy, 1 = QuantumVault deploy
TOKEN_ADDR = Web3.to_checksum_address(broadcast_data["transactions"][0]["contractAddress"])
VAULT_ADDR = Web3.to_checksum_address(broadcast_data["transactions"][1]["contractAddress"])

with open("out/QuantumVault.sol/QuantumVault.json") as f:
    VAULT_ABI = json.load(f)["abi"]

vault_contract = w3.eth.contract(address=VAULT_ADDR, abi=VAULT_ABI)

print("--- QuantumCore Sepolia Gateway ---")
print(f"Connected to Sepolia : {w3.is_connected()}")
print(f"Live Vault Address   : {VAULT_ADDR}")
print(f"TestUSD Token Address: {TOKEN_ADDR}")
print(f"Max Single Tx Cap    : ${vault_contract.functions.maxPerTx().call() / 1e6:.2f}")
print(f"Hourly Spend Cap     : ${vault_contract.functions.hourlyCap().call() / 1e6:.2f}")

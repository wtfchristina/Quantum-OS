from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://sepolia.gateway.tenderly.co"))

deployer_key = "0xedbe2e1b7d566039dddb9d3e72559ebc56fe0472cf49b09eb59a79d5c37751cf"
deployer_acc = w3.eth.account.from_key(deployer_key)
agent_addr = Web3.to_checksum_address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8")

print(f"Deployer address : {deployer_acc.address}")
print(f"Deployer balance : {w3.from_wei(w3.eth.get_balance(deployer_acc.address), 'ether')} ETH")

base_fee = w3.eth.get_block("latest")["baseFeePerGas"]
tx = {
    "chainId": 11155111,
    "from": deployer_acc.address,
    "to": agent_addr,
    "value": w3.to_wei(0.02, "ether"),
    "nonce": w3.eth.get_transaction_count(deployer_acc.address),
    "gas": 21000,
    "maxFeePerGas": int(base_fee * 2) + w3.to_wei(2, "gwei"),
    "maxPriorityFeePerGas": w3.to_wei(2, "gwei")
}

signed = w3.eth.account.sign_transaction(tx, deployer_key)
raw_tx = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
tx_hash = w3.eth.send_raw_transaction(raw_tx)

print(f"Broadcasting 0.02 ETH transfer: {tx_hash.hex()}")
print("Waiting for block confirmation...")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
agent_bal = w3.eth.get_balance(agent_addr)

print(f"Transaction confirmed in Block #{receipt.blockNumber}")
print(f"Agent Balance: {w3.from_wei(agent_bal, 'ether')} ETH")

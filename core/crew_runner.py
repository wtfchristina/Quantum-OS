import os
import json
from crewai.tools import tool
from agent_runner import agent_pay, vault, w3

@tool("quantumcore_payment")
def quantumcore_payment(recipient: str, amount_usd: float) -> str:
    """
    Executes a real programmatic stablecoin payment through QuantumVault on Ethereum Sepolia.
    Enforces a strict $5.00 max per transaction and $20.00 hourly rolling cap.
    
    Args:
        recipient: The Ethereum address (0x...) of the merchant or provider.
        amount_usd: The dollar amount to disburse (e.g. 1.50).
    """
    return agent_pay(recipient, amount_usd)

def run_agent_scenarios():
    print("=================================================================")
    print("      QUANTUMCORE: AUTONOMOUS AGENT SETTLEMENT ROUTER           ")
    print("=================================================================")
    print(f"Vault: {vault.address}")
    print(f"Max Per Tx: ${vault.functions.maxPerTx().call() / 1e6:.2f}")
    print(f"Hourly Cap: ${vault.functions.hourlyCap().call() / 1e6:.2f}\n")

    vendor_a = "0x000000000000000000000000000000000000dEaD"

    # Scenario 1: Autonomous micro-payment within guardrails
    print("--- [Agent Action 1]: Procurement of satellite imagery telemetry ($0.75) ---")
    res1 = quantumcore_payment._run(recipient=vendor_a, amount_usd=0.75)
    print(res1)

    # Scenario 2: Rogue or prompt-injected high-value request
    print("\n--- [Agent Action 2]: Rogue transaction exceeding policy cap ($25.00) ---")
    res2 = quantumcore_payment._run(recipient=vendor_a, amount_usd=25.00)
    print(res2)

if __name__ == "__main__":
    run_agent_scenarios()

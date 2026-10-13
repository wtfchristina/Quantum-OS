from agent_runner import agent_pay

def make_payment(recipient: str, amount_usd: float) -> str:
    """
    Executes a guarded payment using QuantumCore.
    
    Args:
        recipient: The Ethereum address (0x...) of the merchant, API provider, or contractor.
        amount_usd: The dollar amount to transfer (capped at $5.00/tx).
    """
    return agent_pay(recipient, amount_usd)

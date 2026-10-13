import time
from quantum_agent_tool import make_payment

def mock_agent_workflow():
    print("==================================================")
    print("      QUANTUMCORE AUTONOMOUS AGENT ORCHESTRATOR   ")
    print("==================================================")
    
    tasks = [
        {
            "task": "Procure weather API subscription access",
            "vendor": "0x000000000000000000000000000000000000dEaD",
            "invoice_usd": 2.50
        },
        {
            "task": "Emergency GPU compute lease (Exceeds limit)",
            "vendor": "0x000000000000000000000000000000000000dEaD",
            "invoice_usd": 12.00
        }
    ]

    for item in tasks:
        print(f"\n[Agent Goal]: {item['task']}")
        print(f"Action: Initiating payment of ${item['invoice_usd']:.2f} to {item['vendor']}")
        
        result = make_payment(item['vendor'], item['invoice_usd'])
        print(result)
        time.sleep(2)

if __name__ == "__main__":
    mock_agent_workflow()

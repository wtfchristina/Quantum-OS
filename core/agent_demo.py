import time
from quantumcore import QuantumCoreClient

client = QuantumCoreClient()

# Simulated agent task execution queue
tasks = [
    {"service": "Vector Database Querying", "recipient": "0x000000000000000000000000000000000000dEaD", "cost": 0.50},
    {"service": "Synthetic Dataset Extraction", "recipient": "0x000000000000000000000000000000000000dEaD", "cost": 1.75},
    {"service": "Unauthorized Full Fleet Model Download", "recipient": "0x000000000000000000000000000000000000dEaD", "cost": 15.00},
]

print("=== AUTONOMOUS FINANCIAL AGENT INITIATED ===")
for task in tasks:
    print(f"\nEvaluating: {task['service']} (${task['cost']:.2f})")
    try:
        res = client.pay(task['recipient'], task['cost'])
        print(f"Payment Confirmed in Block #{res['block_number']}")
        print(f"Receipt: {res['explorer_url']}")
    except ValueError as e:
        print(f"Blocked by Local Guardrail: {e}")
    except Exception as e:
        print(f"Transaction Reverted: {e}")
    time.sleep(1)

print("\nFinal State:", client.get_limits())

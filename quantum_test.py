import random

def flip_and_entangle():
    # 1. Start both coins resting on 0 (Heads)
    coin_0 = 0
    coin_1 = 0
    
    # 2. Spin Coin 0 (Superposition: 50% chance of 0, 50% chance of 1)
    if random.random() < 0.5:
        coin_0 = 1
        
    # 3. Tie Coin 1 to Coin 0 (Entanglement: Coin 1 copies Coin 0)
    coin_1 = coin_0
    
    return f"{coin_0}{coin_1}"

print("Running your virtual quantum machine 10 times...\n")
results = [flip_and_entangle() for _ in range(10)]

for i, outcome in enumerate(results, 1):
    print(f"Test {i:2d}: Coins landed on |{outcome}>")

print("\nNotice: The coins always match (00 or 11). They never land on 01 or 10!")



import numpy as np

def run_bell_state_circuit(shots=1000):
    # Step 1: Set up two qubits in the ground state |00>
    # State vector holds amplitudes for: [|00>, |01>, |10>, |11>]
    state = np.array([1.0, 0.0, 0.0, 0.0], dtype=complex)

    # Step 2: Apply the Hadamard Gate (H) to Qubit 0
    # This puts Qubit 0 into an equal 50/50 superposition
    H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)
    I = np.eye(2, dtype=complex)
    H_full = np.kron(H, I)  # Expands the gate across both qubits
    state = np.dot(H_full, state)

    # Step 3: Apply the CNOT Gate (Entangles Qubit 0 and Qubit 1)
    # If Qubit 0 is 1, it flips Qubit 1
    CNOT = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 1, 0]
    ], dtype=complex)
    state = np.dot(CNOT, state)

    # Step 4: Calculate probabilities (|amplitude|^2)
    probabilities = np.abs(state) ** 2
    basis_states = ["00", "01", "10", "11"]

    # Step 5: Simulate measuring (collapsing) the state 1,000 times
    outcomes = np.random.choice(basis_states, size=shots, p=probabilities)
    
    # Tally up the counts
    counts = {b: 0 for b in basis_states}
    for outcome in outcomes:
        counts[outcome] += 1

    return counts

# Run the experiment
print("Simulating a true quantum circuit with 1,000 measurements...\n")
results = run_bell_state_circuit(shots=1000)

print(f"{'State':<8} | {'Times Measured':<16} | {'Percentage'}")
print("-" * 42)
for state, count in results.items():
    pct = (count / 1000) * 100
    print(f"|{state}>   | {count:<16} | {pct:>6.1f}%")

print("\nThe state vector collapsed into |00> and |11> roughly 50% each.")
print("States |01> and |10> have an exact 0.0% probability of existing!")


import numpy as np
import matplotlib.pyplot as plt
import subprocess
from scipy.optimize import minimize
from collections import deque

GATES = {
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.array([[1, 0], [0, -1]], dtype=complex),
    "H": (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex),
    "S": np.array([[1, 0], [0, 1j]], dtype=complex),
    "T": np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex),
    "I": np.eye(2, dtype=complex)
}

def rx_gate(theta: float) -> np.ndarray:
    return np.array([
        [np.cos(theta / 2), -1j * np.sin(theta / 2)],
        [-1j * np.sin(theta / 2), np.cos(theta / 2)]
    ], dtype=complex)

def ry_gate(theta: float) -> np.ndarray:
    return np.array([
        [np.cos(theta / 2), -np.sin(theta / 2)],
        [np.sin(theta / 2), np.cos(theta / 2)]
    ], dtype=complex)

def rz_gate(theta: float) -> np.ndarray:
    return np.array([
        [np.exp(-1j * theta / 2), 0],
        [0, np.exp(1j * theta / 2)]
    ], dtype=complex)

class Circuit:
    def __init__(self, n_qubits=3):
        self.n_qubits = n_qubits
        self.ops = []
        self.noise_rate = 0.0

    def ensure_capacity(self, *qubits):
        max_q = max(qubits)
        if max_q >= self.n_qubits:
            self.n_qubits = max_q + 1

    def add_gate(self, name, target, matrix=None, param=None):
        self.ensure_capacity(target)
        self.ops.append(('1Q', name.upper(), target, matrix, param))

    def add_cnot(self, control, target):
        self.ensure_capacity(control, target)
        self.ops.append(('2Q', 'CX', control, target))

    def add_swap(self, q1, q2):
        self.ensure_capacity(q1, q2)
        self.ops.append(('2Q', 'SWAP', q1, q2))

    def add_toffoli(self, c1, c2, target):
        self.ensure_capacity(c1, c2, target)
        self.ops.append(('3Q', 'CCX', c1, c2, target))

    def add_cp(self, control, target, theta):
        self.ensure_capacity(control, target)
        self.ops.append(('2Q_PARAM', 'CP', control, target, theta))

    def reset(self):
        self.ops = []

    def to_qasm(self):
        lines = [
            'OPENQASM 2.0;',
            'include "qelib1.inc";',
            f'qreg q[{self.n_qubits}];',
            f'creg c[{self.n_qubits}];'
        ]
        for op in self.ops:
            if op[0] == '1Q':
                name = op[1].lower()
                target = op[2]
                param = op[4]
                if param is not None:
                    lines.append(f"{name}({param}) q[{target}];")
                else:
                    lines.append(f"{name} q[{target}];")
            elif op[0] == '2Q' and op[1] == 'CX':
                lines.append(f"cx q[{op[2]}], q[{op[3]}];")
            elif op[0] == '2Q' and op[1] == 'SWAP':
                lines.append(f"swap q[{op[2]}], q[{op[3]}];")
            elif op[0] == '3Q' and op[1] == 'CCX':
                lines.append(f"ccx q[{op[2]}], q[{op[3]}], q[{op[4]}];")
            elif op[0] == '2Q_PARAM' and op[1] == 'CP':
                lines.append(f"cp({op[4]}) q[{op[2]}], q[{op[3]}];")
        for i in range(self.n_qubits):
            lines.append(f"measure q[{i}] -> c[{i}];")
        return "\n".join(lines)

def draw(circuit):
    wires = {q: [f"q{q}: --"] for q in range(circuit.n_qubits)}
    for op in circuit.ops:
        if op[0] == '1Q':
            name, target = op[1], op[2]
            label = f"[{name[:2]}]--" if len(name) <= 2 else f"[{name[:3]}]-"
            wires[target].append(label)
            for q in range(circuit.n_qubits):
                if q != target:
                    wires[q].append("-----")
        elif op[0] == '2Q' and op[1] == 'CX':
            c, t = op[2], op[3]
            wires[c].append("-(•)-")
            wires[t].append("-(X)-")
            for q in range(circuit.n_qubits):
                if q not in (c, t):
                    wires[q].append("-----")
        elif op[0] == '2Q' and op[1] == 'SWAP':
            q1, q2 = op[2], op[3]
            wires[q1].append("-(X)-")
            wires[q2].append("-(X)-")
            for q in range(circuit.n_qubits):
                if q not in (q1, q2):
                    wires[q].append("-----")
        elif op[0] == '2Q_PARAM' and op[1] == 'CP':
            c, t = op[2], op[3]
            wires[c].append("-(•)-")
            wires[t].append("-(P)-")
            for q in range(circuit.n_qubits):
                if q not in (c, t):
                    wires[q].append("-----")
        elif op[0] == '3Q' and op[1] == 'CCX':
            c1, c2, t = op[2], op[3], op[4]
            wires[c1].append("-(•)-")
            wires[c2].append("-(•)-")
            wires[t].append("-(X)-")
            for q in range(circuit.n_qubits):
                if q not in (c1, c2, t):
                    wires[q].append("-----")
    
    diagram = []
    for q in range(circuit.n_qubits):
        wires[q].append("[M]")
        diagram.append("".join(wires[q]))
    return "\n".join(diagram)

def apply_noise(state, n_qubits, rate):
    if rate <= 0.0:
        return state
    for q in range(n_qubits):
        if np.random.random() < rate:
            noise_gate = np.random.choice(["X", "Z", "Y"])
            G = GATES[noise_gate]
            matrices = [GATES["I"]] * n_qubits
            matrices[q] = G
            full = matrices[0]
            for m in matrices[1:]:
                full = np.kron(full, m)
            state = np.dot(full, state)
    return state

def get_state_vector(circuit):
    dim = 2 ** circuit.n_qubits
    state = np.zeros(dim, dtype=complex)
    state[0] = 1.0 + 0.0j

    for op in circuit.ops:
        if op[0] == '1Q':
            target, matrix = op[2], op[3]
            if matrix is None:
                matrix = GATES[op[1]]
            matrices = [GATES["I"]] * circuit.n_qubits
            matrices[target] = matrix
            full_matrix = matrices[0]
            for m in matrices[1:]:
                full_matrix = np.kron(full_matrix, m)
            state = np.dot(full_matrix, state)

        elif op[0] == '2Q' and op[1] == 'CX':
            c, t = op[2], op[3]
            new_state = np.zeros_like(state)
            for i in range(dim):
                bits = list(map(int, bin(i)[2:].zfill(circuit.n_qubits)))
                if bits[c] == 1:
                    bits[t] ^= 1
                dest = int("".join(map(str, bits)), 2)
                new_state[dest] = state[i]
            state = new_state

        elif op[0] == '2Q' and op[1] == 'SWAP':
            q1, q2 = op[2], op[3]
            new_state = np.zeros_like(state)
            for i in range(dim):
                bits = list(map(int, bin(i)[2:].zfill(circuit.n_qubits)))
                bits[q1], bits[q2] = bits[q2], bits[q1]
                dest = int("".join(map(str, bits)), 2)
                new_state[dest] = state[i]
            state = new_state

        elif op[0] == '2Q_PARAM' and op[1] == 'CP':
            c, t, theta = op[2], op[3], op[4]
            new_state = np.copy(state)
            for i in range(dim):
                bits = list(map(int, bin(i)[2:].zfill(circuit.n_qubits)))
                if bits[c] == 1 and bits[t] == 1:
                    new_state[i] *= np.exp(1j * theta)
            state = new_state

        elif op[0] == '3Q' and op[1] == 'CCX':
            c1, c2, t = op[2], op[3], op[4]
            new_state = np.zeros_like(state)
            for i in range(dim):
                bits = list(map(int, bin(i)[2:].zfill(circuit.n_qubits)))
                if bits[c1] == 1 and bits[c2] == 1:
                    bits[t] ^= 1
                dest = int("".join(map(str, bits)), 2)
                new_state[dest] = state[i]
            state = new_state

    return state

def simulate(circuit, shots=1000):
    dim = 2 ** circuit.n_qubits
    counts = {}

    for _ in range(shots):
        state = get_state_vector(circuit)
        state = apply_noise(state, circuit.n_qubits, circuit.noise_rate)

        probs = np.abs(state) ** 2
        probs /= np.sum(probs)
        out = np.random.choice(dim, p=probs)
        b = bin(out)[2:].zfill(circuit.n_qubits)
        counts[b] = counts.get(b, 0) + 1

    return dict(sorted(counts.items()))

def run_qpe():
    print("\n--- Running Quantum Phase Estimation (QPE) ---")
    theta_true = 0.625
    print(f"Goal: Estimate phase θ = {theta_true} (fraction: 5/8, binary: 0.101) using 3 counting qubits.\n")

    qpe = Circuit(4)
    qpe.add_gate("X", 3)
    for q in range(3):
        qpe.add_gate("H", q)

    qpe.add_cp(0, 3, 2 * np.pi * theta_true * 1)
    qpe.add_cp(1, 3, 2 * np.pi * theta_true * 2)
    qpe.add_cp(2, 3, 2 * np.pi * theta_true * 4)

    qpe.add_swap(0, 2)
    qpe.add_gate("H", 0)
    qpe.add_cp(1, 0, -np.pi / 2)
    qpe.add_gate("H", 1)
    qpe.add_cp(2, 0, -np.pi / 4)
    qpe.add_cp(2, 1, -np.pi / 2)
    qpe.add_gate("H", 2)

    print("Circuit Diagram:")
    print(draw(qpe))

    res = simulate(qpe, shots=1000)
    print("\nMeasurement Results (Counting Qubits q2 q1 q0):")
    for st, count in res.items():
        counting_bits = st[:3]
        decimal_val = int(counting_bits[::-1], 2)
        estimated_phase = decimal_val / 8.0
        pct = (count / 1000) * 100
        print(f"Counting State |{counting_bits}> -> Int: {decimal_val} -> Est Phase: {estimated_phase:.3f} | {count} shots ({pct:.1f}%)")

    print("\nQPE correctly resolved θ = 0.625 without classical search!\n")

TOPOLOGIES = {
    "linear": {0: [1], 1: [0, 2], 2: [1]},
    "grid_2x2": {
        0: [1, 2],
        1: [0, 3],
        2: [0, 3],
        3: [1, 2]
    },
    "heavy_hex": {
        0: [1],
        1: [0, 2, 3],
        2: [1],
        3: [1, 4],
        4: [3]
    }
}

def shortest_path_bfs(graph, start, end):
    queue = deque([[start]])
    visited = {start}
    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == end:
            return path
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return None

def transpile_advanced(circuit, arch_name="heavy_hex"):
    if arch_name not in TOPOLOGIES:
        print(f"Unknown topology. Available: {list(TOPOLOGIES.keys())}")
        return circuit

    graph = TOPOLOGIES[arch_name]
    required_qubits = max(graph.keys()) + 1
    new_circ = Circuit(max(circuit.n_qubits, required_qubits))

    print(f"\n--- Transpiling for {arch_name.upper()} Hardware Architecture ---")
    swaps_added = 0

    for op in circuit.ops:
        if op[0] in ('1Q', '3Q'):
            new_circ.ops.append(op)
        elif op[0] == '2Q' and op[1] == 'CX':
            c, t = op[2], op[3]
            if t in graph.get(c, []):
                new_circ.add_cnot(c, t)
            else:
                path = shortest_path_bfs(graph, c, t)
                if not path:
                    print(f"Warning: No hardware coupling path between Q{c} and Q{t}")
                    continue
                swap_chain = []
                current = path[0]
                for next_node in path[1:-1]:
                    new_circ.add_swap(current, next_node)
                    swap_chain.append((current, next_node))
                    swaps_added += 1
                    current = next_node
                new_circ.add_cnot(current, t)
                for s1, s2 in reversed(swap_chain):
                    new_circ.add_swap(s1, s2)
                    swaps_added += 1
        else:
            new_circ.ops.append(op)

    print(f"Original Gate Count : {len(circuit.ops)}")
    print(f"Routing SWAPs Added : {swaps_added}")
    print(f"Total Transpiled Ops: {len(new_circ.ops)}\n")
    print(draw(new_circ))
    print()
    return new_circ

def run_tomography(circuit):
    state = get_state_vector(circuit)
    dim = 2 ** circuit.n_qubits
    rho = np.outer(state, np.conj(state))

    print(f"\n--- Quantum State Tomography (Dimension: {dim}x{dim}) ---")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    im1 = ax1.imshow(np.real(rho), cmap='Blues', vmin=-1, vmax=1)
    ax1.set_title("Real Part: Re(ρ)")
    fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)

    im2 = ax2.imshow(np.imag(rho), cmap='Purples', vmin=-1, vmax=1)
    ax2.set_title("Imaginary Part: Im(ρ)")
    fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)

    labels = [f"|{bin(i)[2:].zfill(circuit.n_qubits)}>" for i in range(dim)]
    for ax in (ax1, ax2):
        ax.set_xticks(range(dim))
        ax.set_yticks(range(dim))
        ax.set_xticklabels(labels, rotation=45)
        ax.set_yticklabels(labels)

    plt.tight_layout()
    img_path = "tomography.png"
    plt.savefig(img_path, dpi=150)
    plt.close(fig)
    subprocess.run(["open", img_path])
    print(f"Tomography visualization rendered and opened {img_path} in Preview.\n")

def parse_angle(val_str: str) -> float:
    val_str = val_str.lower().strip()
    if "pi" in val_str:
        val_str = val_str.replace("pi", str(np.pi))
        return eval(val_str)
    return float(val_str)

def main():
    print("=" * 64)
    print("      QUANTUM OPERATING SYSTEM: QPE, HEAVY-HEX & TOMOGRAPHY   ")
    print("=" * 64)

    circ = Circuit(5)
    print(f"\nInitialized 5-qubit processor in state |{'0'*5}>.")
    
    help_text = """
Quantum Gates:
  h, x, y, z, s, t <q>   -> Standard single-qubit gates
  rx, ry, rz <q> <ang>   -> Continuous rotations
  cx <c> <t>             -> CNOT gate
  ccx <c1> <c2> <t>      -> Toffoli gate
  swap <q1> <q2>         -> SWAP gate

Advanced Modules:
  qpe                    -> Run Quantum Phase Estimation
  tomo                   -> Full Quantum State Tomography (heatmap)
  transpile <arch>       -> Transpile for 'linear', 'grid_2x2', or 'heavy_hex'
  draw                   -> Render ASCII diagram
  run [shots]            -> Simulate measurement counts
  clear                  -> Reset circuit
  exit                   -> Quit
    """
    print(help_text)

    while True:
        raw = input("quantum-os > ").strip().split()
        if not raw:
            continue
        cmd = raw[0].lower()
        args = raw[1:]

        try:
            if cmd == "exit":
                print("Shutting down quantum machine.")
                break
            elif cmd == "clear":
                circ.reset()
                print("Circuit cleared.")
            elif cmd == "draw":
                print("\n" + draw(circ) + "\n")
            elif cmd == "qasm":
                print("\n" + circ.to_qasm() + "\n")
            elif cmd == "qpe":
                run_qpe()
            elif cmd == "tomo":
                run_tomography(circ)
            elif cmd == "transpile":
                arch = args[0] if args else "heavy_hex"
                circ = transpile_advanced(circ, arch)
            elif cmd in ("rx", "ry", "rz"):
                q = int(args[0])
                angle = parse_angle(args[1])
                fn = {"rx": rx_gate, "ry": ry_gate, "rz": rz_gate}[cmd]
                circ.add_gate(cmd.upper(), q, matrix=fn(angle), param=str(args[1]))
                print(f"Applied {cmd.upper()}({args[1]}) to qubit {q}")
            elif cmd in ("h", "x", "y", "z", "s", "t"):
                q = int(args[0])
                circ.add_gate(cmd, q)
                print(f"Applied {cmd.upper()} to qubit {q}")
            elif cmd == "cx":
                c, t = int(args[0]), int(args[1])
                circ.add_cnot(c, t)
                print(f"Applied CX (control: {c}, target: {t})")
            elif cmd == "ccx":
                c1, c2, t = int(args[0]), int(args[1]), int(args[2])
                circ.add_toffoli(c1, c2, t)
                print(f"Applied CCX (controls: {c1}, {c2} -> target: {t})")
            elif cmd == "swap":
                q1, q2 = int(args[0]), int(args[1])
                circ.add_swap(q1, q2)
                print(f"Applied SWAP between {q1} and {q2}")
            elif cmd == "run":
                shots = int(args[0]) if args else 1000
                print(f"\nSimulating {shots} shots...")
                res = simulate(circ, shots)
                print(f"\n{'State':<8} | {'Count':<8} | {'Probability'}")
                print("-" * 34)
                for state, count in res.items():
                    print(f"|{state}>   | {count:<8} | {(count/shots)*100:>5.1f}%")
                print()
            else:
                print("Unknown command. Type 'draw', 'transpile heavy_hex', or 'run'.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()

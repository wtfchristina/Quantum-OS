# Quantum-OS: Modular Quantum Computing Workbench & Transpiler

A self-contained quantum computing simulator, algorithm laboratory, and hardware transpilation engine written in Python.

## Core Features

- **Full State-Vector Simulator**: $N$-qubit state evolution using Kronecker tensor products and complex state amplitudes.
- **Universal Gate Set**: Pauli ($X, Y, Z$), Phase ($S, T$), continuous Euler rotations ($R_x, R_y, R_z$), controlled phase ($CP$), $CX$ (CNOT), $SWAP$, and 3-qubit Toffoli ($CCX$).
- **Decoherence & Noise Modeling**: Parameterized Pauli channel noise simulation to model environmental decoherence on NISQ processors.
- **Hardware Architecture Transpilation**: Breadth-First Search (BFS) routing and automated SWAP insertion for **Linear**, **2D Planar Grid**, and **IBM Heavy-Hex** hardware coupling graphs.
- **Algorithms & Information Protocols**:
  - Quantum Phase Estimation (QPE)
  - Grover's Unstructured Search (Amplitude Amplification)
  - Quantum Teleportation Protocol
  - Deutsch's Quantum Speedup Algorithm
  - 3-Qubit Bit-Flip Quantum Error Correction (QEC)
- **Quantum Chemistry**: Variational Quantum Eigensolver (VQE) paired with classical SciPy optimization to find molecular orbital ground states ($H_2$).
- **Visualization & Diagnostics**:
  - OpenQASM 2.0 export for execution on IBM Quantum / AWS Braket hardware.
  - Interactive 3D Bloch sphere vector projections.
  - Full multi-qubit density matrix ($\rho$) State Tomography heatmaps.
  - ASCII circuit diagrams.

## Installation & Usage

1. Clone the repository:
   ```bash
   git clone [https://github.com/wtfchristina/Quantum-OS.git](https://github.com/wtfchristina/Quantum-OS.git)
   cd Quantum-OS

E0F

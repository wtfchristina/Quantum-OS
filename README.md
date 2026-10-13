# Quantum-OS: Unified Quantum-Relativistic Architecture

An integrated platform coupling Post-Quantum Cryptography (PQC), ETSI 014-compliant Quantum Key Distribution (QKD), Physics-Informed Neural Network (PINN) relativistic geodesic solvers, and real-time Three.js WebGL telemetry visualization.

---

## Subsystem Architecture

- C++ QKD Engine & Daemon (Port 8765): BB84 simulation, ETSI GS QKD 014 key pool, HKDF-SHA256 hybrid derivation.
- Python Runtime Orchestrator: RK4/PINN geodesic equations, AES-256-GCM envelope encryption, on-chain incident logging.
- Three.js Cockpit Frontend (Port 3000): In-browser Web Crypto API GCM decryption, custom GLSL spacetime curvature shader, dynamic orbital particle ribbon.

---

## Operational Commands

- make start: Launch C++ daemon, Python bridge, and WebGL web server concurrently.
- make stop: Terminate all running background processes cleanly.
- make verify: Execute the 4-tier automated integration smoke test suite.
- ./bin/simulate-attack: Inject real-time optical eavesdropping channel interception.

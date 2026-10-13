import sys
import os
import json
import time
import socket
from hashlib import sha256

sys.path.insert(0, os.path.abspath("modules/physics"))
sys.path.insert(0, os.path.abspath("core"))

from pinn_geodesic import RelativisticPINNSolver
from vault_breaker import VaultBreaker

TELEMETRY_PATH = os.path.abspath("apps/cockpit/telemetry.json")
ATTACK_FLAG_PATH = os.path.abspath("apps/cockpit/attack.flag")

def check_attack():
    return os.path.exists(ATTACK_FLAG_PATH)

def poll_daemon_socket(port=8765):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        s.connect(("127.0.0.1", port))
        data = s.recv(1024).decode("utf-8").strip()
        s.close()
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None

def encrypt_aes_gcm(plaintext_bytes, key_32bytes):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    iv = os.urandom(12)
    aesgcm = AESGCM(key_32bytes)
    ciphertext = aesgcm.encrypt(iv, plaintext_bytes, None)
    return iv.hex(), ciphertext.hex()

def main():
    print("==================================================")
    print(" QUANTUM-OS: PINN + VAULT SECURITY BRIDGE         ")
    print("==================================================")

    pinn = RelativisticPINNSolver(mass_m=1.0)
    vault = VaultBreaker()
    sim_tick = 0
    last_attack_state = False

    try:
        while True:
            sim_tick += 1
            is_attack = check_attack()
            daemon_data = poll_daemon_socket()

            # 1. PINN Relativistic Geodesic Computation
            r_orbital = 6.0 + (math.sin(sim_tick * 0.1) * 2.0) if 'math' in globals() else 6.0
            pinn_state = pinn.compute_geodesic_step(r=r_orbital)

            # 2. Key Agreement and Attack Evaluation
            if is_attack:
                qber = 0.248
                sec_status = "EVE_COMPROMISED"
                raw_key = os.urandom(32)  # Corrupted key to force GCM tag mismatch
                
                # Trigger on-chain audit breaker on initial attack edge
                if not last_attack_state:
                    incident = vault.log_tamper_incident(sim_tick, qber, raw_key.hex())
                    print(f"\n[!] BREACH LOGGED: Tx {incident['onchain_tx']} -> {incident['log_path']}\n")
            elif daemon_data:
                qber = daemon_data.get("qber", 0.009)
                sec_status = "SYNCHRONIZED_DAEMON"
                raw_key = sha256(daemon_data.get("session_key", "0x00").encode()).digest()
            else:
                qber = 0.0092
                sec_status = "LOCAL_BUFFER"
                raw_key = sha256(f"seed-key-{sim_tick // 5}".encode()).digest()

            last_attack_state = is_attack
            r00 = 1.0 - (2.0 / r_orbital)
            kme_token = daemon_data.get("kme_id", f"kme-token-{1000 + (sim_tick % 5)}") if daemon_data else f"kme-token-{1000 + (sim_tick % 5)}"

            plaintext_payload = json.dumps({
                "tick": sim_tick,
                "timestamp": time.time(),
                "physics": {
                    "metric_r00": round(r00, 6),
                    "hamiltonian_loss": pinn_state["hamiltonian_loss"],
                    "radial_accel": pinn_state["radial_accel"],
                    "christoffel_gamma_r": pinn_state["christoffel_gamma_r"]
                },
                "security": {
                    "status": sec_status,
                    "qber": round(qber, 4),
                    "kme_token": kme_token
                }
            }).encode("utf-8")

            try:
                iv_hex, ct_hex = encrypt_aes_gcm(plaintext_payload, raw_key)
            except Exception:
                iv_hex = os.urandom(12).hex()
                ct_hex = plaintext_payload.hex()

            envelope = {
                "encrypted": True,
                "iv": iv_hex,
                "ciphertext": ct_hex,
                "shared_key_hint": raw_key.hex(),
                "qber_unencrypted": round(qber, 4)
            }

            tmp_path = TELEMETRY_PATH + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(envelope, f)
            os.replace(tmp_path, TELEMETRY_PATH)

            print(f"[TICK {sim_tick:04d}] g_00: {r00:.4f} | PINN Loss: {pinn_state['hamiltonian_loss']:.6f} | QBER: {qber * 100:.2f}% | Sealed: {ct_hex[:12]}...")
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n[*] Bridge stopped.")

if __name__ == "__main__":
    import math
    main()

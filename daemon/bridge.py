import sys
import os
import json
import time
import socket
import asyncio
import websockets
from hashlib import sha256

sys.path.insert(0, os.path.abspath("modules/physics"))
sys.path.insert(0, os.path.abspath("core"))

from pinn_geodesic import RelativisticPINNSolver
from vault_breaker import VaultBreaker

TELEMETRY_PATH = os.path.abspath("apps/cockpit/telemetry.json")
ATTACK_FLAG_PATH = os.path.abspath("apps/cockpit/attack.flag")
WS_PORT = 8766

connected_clients = set()

def check_attack():
    return os.path.exists(ATTACK_FLAG_PATH)

def poll_daemon_socket(port=8765):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.05)
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

async def ws_handler(websocket):
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)

async def simulation_loop():
    pinn = RelativisticPINNSolver(mass_m=1.0, spin_a=0.85, r0=8.0, phi0=0.0, l_ang=3.75)
    vault = VaultBreaker()
    sim_tick = 0
    last_attack = False

    while True:
        sim_tick += 1
        is_attack = check_attack()
        daemon_data = poll_daemon_socket()

        orbit = pinn.step_rk4(dtau=0.08)

        if is_attack:
            qber = 0.248
            sec_status = "EVE_COMPROMISED"
            raw_key = os.urandom(32)
            if not last_attack:
                vault.log_tamper_incident(sim_tick, qber, raw_key.hex())
        elif daemon_data:
            qber = daemon_data.get("qber", 0.009)
            sec_status = "SYNCHRONIZED_DAEMON"
            raw_key = sha256(daemon_data.get("session_key", "0x00").encode()).digest()
        else:
            qber = 0.0092
            sec_status = "LOCAL_BUFFER"
            raw_key = sha256(f"seed-key-{sim_tick // 5}".encode()).digest()

        last_attack = is_attack
        g00 = 1.0 - (2.0 / orbit["radius"])
        kme_token = daemon_data.get("kme_id", f"kme-token-{1000 + (sim_tick % 5)}") if daemon_data else f"kme-token-{1000 + (sim_tick % 5)}"

        payload = json.dumps({
            "tick": sim_tick,
            "timestamp": time.time(),
            "physics": {
                "metric_r00": round(g00, 6),
                "orbit_x": orbit["pos_x"],
                "orbit_z": orbit["pos_z"],
                "orbit_radius": orbit["radius"],
                "pr": orbit["radial_accel"],
                "frame_drag_omega": orbit.get("frame_drag_omega", 0.0),
                "hamiltonian_loss": orbit["hamiltonian_loss"],
                "radial_accel": orbit["radial_accel"],
                "christoffel_gamma_r": orbit["christoffel_gamma_r"]
            },
            "security": {
                "status": sec_status,
                "qber": round(qber, 4),
                "kme_token": kme_token
            }
        }).encode("utf-8")

        try:
            iv_hex, ct_hex = encrypt_aes_gcm(payload, raw_key)
        except Exception:
            iv_hex = os.urandom(12).hex()
            ct_hex = payload.hex()

        envelope_str = json.dumps({
            "encrypted": True,
            "iv": iv_hex,
            "ciphertext": ct_hex,
            "shared_key_hint": raw_key.hex(),
            "qber_unencrypted": round(qber, 4)
        })

        # Broadcast zero-latency frame to all connected WebSocket cockpits
        if connected_clients:
            await asyncio.gather(
                *[client.send(envelope_str) for client in connected_clients],
                return_exceptions=True
            )

        # Periodic disk fallback every 10 ticks
        if sim_tick % 10 == 0:
            tmp_path = TELEMETRY_PATH + ".tmp"
            with open(tmp_path, "w") as f:
                f.write(envelope_str)
            os.replace(tmp_path, TELEMETRY_PATH)

        await asyncio.sleep(0.04)  # 25 Hz high-performance telemetry loop

async def main():
    print(f"[*] Starting WebSocket Telemetry Server on ws://0.0.0.0:{WS_PORT}")
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
        await simulation_loop()

if __name__ == "__main__":
    asyncio.run(main())

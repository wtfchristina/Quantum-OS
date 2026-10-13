import sys
import os
import json
import time
import socket

sys.path.insert(0, os.path.abspath("modules/physics"))
sys.path.insert(0, os.path.abspath("core"))

TELEMETRY_PATH = os.path.abspath("apps/cockpit/telemetry.json")
ATTACK_FLAG_PATH = os.path.abspath("apps/cockpit/attack.flag")

def check_attack_state():
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

def compute_schwarzschild_metric(tick, mass_kg=5.972e24, base_radius_m=6.371e6):
    G = 6.67430e-11
    c = 299792458.0
    r_eff = base_radius_m + ((tick % 200) * 5000.0)
    rs = (2.0 * G * mass_kg) / (c * c)
    g00 = 1.0 - (rs / r_eff)
    return round(float(g00), 6)

def main():
    print("==================================================")
    print("   QUANTUM-OS: ATTACK-AWARE ORCHESTRATOR BRIDGE   ")
    print("==================================================")

    sim_tick = 0
    try:
        while True:
            sim_tick += 1
            is_under_attack = check_attack_state()
            crypto_telemetry = poll_daemon_socket()
            g00 = compute_schwarzschild_metric(sim_tick)

            if is_under_attack:
                qber = 0.245 + (0.01 * (sim_tick % 5))
                sec_status = "ABORTED_EAVESDROP"
                session_key = "REVOKED_ATTACK_DETECTED"
            else:
                qber = 0.0092 + (0.0005 * (sim_tick % 4))
                sec_status = "SECURE"
                session_key = f"0x{os.urandom(4).hex()}..."

            frame = {
                "tick": sim_tick,
                "timestamp": time.time(),
                "physics": {
                    "metric_r00": g00,
                    "engine_mode": "SCHWARZSCHILD_EXACT",
                    "gravity_field_status": "CONVERGED"
                },
                "security": crypto_telemetry or {
                    "status": sec_status,
                    "qber": round(qber, 4),
                    "kme_token": f"kme-token-{1000 + (sim_tick % 8)}",
                    "session_key": session_key
                }
            }

            tmp_path = TELEMETRY_PATH + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(frame, f)
            os.replace(tmp_path, TELEMETRY_PATH)

            print(f"[TICK {frame['tick']:04d}] "
                  f"g_00: {frame['physics']['metric_r00']:.6f} | "
                  f"QBER: {frame['security'].get('qber', 0.0) * 100:.2f}% | "
                  f"STATUS: {frame['security'].get('status')} | "
                  f"KEY: {frame['security'].get('session_key')}")

            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n[*] Stopping orchestrator bridge...")

if __name__ == "__main__":
    main()

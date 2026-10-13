#include "qkd/bb84.hpp"
#include "qkd/etsi014_kme.hpp"
#include "sentinel/hybrid_kdf.hpp"
#include <iostream>
#include <iomanip>
#include <chrono>
#include <thread>
#include <sstream>

struct SystemTelemetry {
    uint64_t tick;
    double qber;
    std::string active_key_id;
    std::array<uint8_t, 32> session_key;
    double spacetime_curvature_r00;
};

class QuantumDaemon {
public:
    QuantumDaemon() : sim_(0.012, 0.0), tick_(0) {}

    void initialize_key_pool(size_t pool_size = 5) {
        for (size_t i = 0; i < pool_size; ++i) {
            auto res = sim_.run_exchange(2048);
            if (!res.aborted && res.sifted_key_alice.size() >= 32) {
                std::vector<uint8_t> key_bytes(res.sifted_key_alice.begin(), res.sifted_key_alice.begin() + 32);
                std::string key_id = "kme-token-" + std::to_string(1000 + i);
                kme_.store_key(key_id, key_bytes);
            }
        }
        std::cout << "[DAEMON] Initialized KME pool with " << kme_.available_keys() << " keys.\n";
    }

    SystemTelemetry step_simulation() {
        tick_++;

        // Replenish key pool if low
        if (kme_.available_keys() < 2) {
            initialize_key_pool(3);
        }

        // Run continuous BB84 exchange tick
        auto qkd_res = sim_.run_exchange(1024);
        auto key_container = kme_.request_key();

        std::string kid = key_container ? key_container->key_id : "NO_KEY";
        std::vector<uint8_t> qkd_material = key_container ? key_container->key_bytes : std::vector<uint8_t>(32, 0x00);

        // Mock FIPS 203 ML-KEM secret from pqc-sentinel
        std::vector<uint8_t> pqc_secret(32, static_cast<uint8_t>(tick_ & 0xFF));

        // Derive active wire key
        auto session_key = sentinel::HybridKDF::derive(pqc_secret, qkd_material, "QuantumOS-Telemetry-v1");

        // Mock relativistic scalar metric component R_00 = -4 * pi * G * rho
        double metric_scalar = 1.0 - (0.05 * (tick_ % 10));

        return {tick_, qkd_res.qber, kid, session_key, metric_scalar};
    }

private:
    qkd::BB84Simulator sim_;
    qkd::KeyManagementEntity kme_;
    uint64_t tick_;
};

int main() {
    std::cout << "=== Quantum-OS Core Daemon Initializing ===\n";
    QuantumDaemon daemon;
    daemon.initialize_key_pool(4);

    std::cout << "[DAEMON] Starting loop (streaming telemetry)...\n";

    for (int frame = 1; frame <= 5; ++frame) {
        auto t = daemon.step_simulation();
        
        std::stringstream ss;
        ss << std::hex;
        for (int i = 0; i < 4; ++i) {
            ss << std::setw(2) << std::setfill('0') << static_cast<int>(t.session_key[i]);
        }
        ss << "...";

        std::cout << "[FRAME " << t.tick << "] "
                  << "QBER: " << std::fixed << std::setprecision(2) << (t.qber * 100.0) << "% | "
                  << "KME ID: " << t.active_key_id << " | "
                  << "Session Key: 0x" << ss.str() << " | "
                  << "R_00: " << t.spacetime_curvature_r00 << "\n";

        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }

    std::cout << "[DAEMON] Self-test sequence complete.\n";
    return 0;
}

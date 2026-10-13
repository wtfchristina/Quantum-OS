#include "qkd/bb84.hpp"
#include "qkd/etsi014_kme.hpp"
#include "sentinel/hybrid_kdf.hpp"
#include <iostream>
#include <iomanip>
#include <chrono>
#include <thread>
#include <sstream>
#include <string>
#include <cstring>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>

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
        std::cout << "[DAEMON] KME Pool Active: " << kme_.available_keys() << " keys ready.\n";
    }

    SystemTelemetry step_simulation() {
        tick_++;
        if (kme_.available_keys() < 2) {
            initialize_key_pool(4);
        }

        auto qkd_res = sim_.run_exchange(1024);
        auto key_container = kme_.request_key();

        std::string kid = key_container ? key_container->key_id : "NO_KEY";
        std::vector<uint8_t> qkd_material = key_container ? key_container->key_bytes : std::vector<uint8_t>(32, 0x00);
        std::vector<uint8_t> pqc_secret(32, static_cast<uint8_t>(tick_ & 0xFF));

        auto session_key = sentinel::HybridKDF::derive(pqc_secret, qkd_material, "QuantumOS-Wire-v1");
        double metric_scalar = 1.0 - (0.02 * (tick_ % 10));

        return {tick_, qkd_res.qber, kid, session_key, metric_scalar};
    }

private:
    qkd::BB84Simulator sim_;
    qkd::KeyManagementEntity kme_;
    uint64_t tick_;
};

int main(int argc, char* argv[]) {
    int port = 8765;
    if (argc > 1) port = std::stoi(argv[1]);

    std::cout << "=== Quantum-OS Distributed Node Starting ===\n";
    QuantumDaemon daemon;
    daemon.initialize_key_pool(6);

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY; // Listen on all network interfaces
    address.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) {
        std::cerr << "[DAEMON ERROR] Bind failed on port " << port << "\n";
        return 1;
    }

    listen(server_fd, 8);
    fcntl(server_fd, F_SETFL, O_NONBLOCK);
    std::cout << "[DAEMON] Server bound on 0.0.0.0:" << port << " (awaiting cockpit nodes)...\n";

    while (true) {
        auto t = daemon.step_simulation();

        std::stringstream key_hex;
        key_hex << std::hex;
        for (int i = 0; i < 4; ++i) {
            key_hex << std::setw(2) << std::setfill('0') << static_cast<int>(t.session_key[i]);
        }

        std::string payload = "{\"tick\":" + std::to_string(t.tick) +
            ",\"qber\":" + std::to_string(t.qber) +
            ",\"kme_id\":\"" + t.active_key_id + "\"" +
            ",\"session_key\":\"0x" + key_hex.str() + "...\"" +
            ",\"r00\":" + std::to_string(t.spacetime_curvature_r00) + "}\n";

        sockaddr_in client_addr{};
        socklen_t client_len = sizeof(client_addr);
        int client_fd = accept(server_fd, (struct sockaddr*)&client_addr, &client_len);
        if (client_fd >= 0) {
            send(client_fd, payload.c_str(), payload.size(), 0);
            close(client_fd);
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }

    close(server_fd);
    return 0;
}

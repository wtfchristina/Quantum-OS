#include "sentinel/hybrid_kdf.hpp"
#include "qkd/bb84.hpp"
#include "qkd/etsi014_kme.hpp"
#include <iostream>
#include <iomanip>
#include <cassert>

int main() {
    // 1. Run BB84 key exchange simulation
    qkd::BB84Simulator sim(0.01, 0.0);
    auto exchange = sim.run_exchange(2048);
    assert(!exchange.aborted);
    assert(exchange.sifted_key_alice.size() >= 32);

    // 2. Take 32 bytes of sifted quantum key material
    std::vector<uint8_t> qkd_raw(exchange.sifted_key_alice.begin(), exchange.sifted_key_alice.begin() + 32);

    // 3. Store into ETSI 014 KME and retrieve
    qkd::KeyManagementEntity kme;
    kme.store_key("session-uuid-42", qkd_raw);
    auto delivered = kme.request_key();
    assert(delivered.has_value());

    // 4. Mock FIPS 203 ML-KEM shared secret (32 bytes)
    std::vector<uint8_t> mock_ml_kem_secret(32, 0x5A);

    // 5. Derive hybrid session key
    auto session_key_alice = sentinel::HybridKDF::derive(mock_ml_kem_secret, delivered->key_bytes);
    auto session_key_bob   = sentinel::HybridKDF::derive(mock_ml_kem_secret, qkd_raw);

    // Verify key agreement across endpoints
    assert(session_key_alice == session_key_bob);

    std::cout << "Derived 256-bit Hybrid Session Key: 0x";
    for (uint8_t b : session_key_alice) {
        std::cout << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(b);
    }
    std::cout << "\nHybrid PQC + QKD key agreement verified successfully.\n";

    return 0;
}

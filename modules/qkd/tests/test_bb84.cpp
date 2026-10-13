#include "qkd/bb84.hpp"
#include "qkd/etsi014_kme.hpp"
#include <iostream>
#include <cassert>

int main() {
    qkd::BB84Simulator sim_clean(0.01, 0.0);
    auto clean_result = sim_clean.run_exchange(4096);
    std::cout << "Clean channel QBER: " << clean_result.qber * 100.0 << "%\n";
    assert(!clean_result.aborted);
    assert(clean_result.sifted_key_alice.size() > 1000);

    qkd::BB84Simulator sim_eve(0.01, 0.80);
    auto compromised_result = sim_eve.run_exchange(4096);
    std::cout << "Compromised channel QBER: " << compromised_result.qber * 100.0 << "%\n";
    assert(compromised_result.aborted);

    qkd::KeyManagementEntity kme;
    kme.store_key("key-uuid-001", {0xAA, 0xBB, 0xCC, 0xDD});
    assert(kme.available_keys() == 1);

    auto key_req = kme.request_key();
    assert(key_req.has_value());
    assert(key_req->key_id == "key-uuid-001");
    assert(kme.available_keys() == 0);

    std::cout << "All QKD BB84 and KME assertions passed.\n";
    return 0;
}

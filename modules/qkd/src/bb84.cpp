#include "qkd/bb84.hpp"
#include <algorithm>

namespace qkd {

SiftResult BB84Simulator::run_exchange(size_t raw_bits_count, double sample_ratio) {
    std::uniform_int_distribution<int> bit_dist(0, 1);
    std::uniform_real_distribution<double> prob_dist(0.0, 1.0);

    std::vector<uint8_t> alice_bits(raw_bits_count);
    std::vector<Basis> alice_bases(raw_bits_count);
    std::vector<Basis> bob_bases(raw_bits_count);
    std::vector<uint8_t> bob_bits(raw_bits_count);

    for (size_t i = 0; i < raw_bits_count; ++i) {
        alice_bits[i] = static_cast<uint8_t>(bit_dist(rng_));
        alice_bases[i] = static_cast<Basis>(bit_dist(rng_));
        bob_bases[i] = static_cast<Basis>(bit_dist(rng_));

        uint8_t measured_bit = alice_bits[i];

        if (prob_dist(rng_) < eve_rate_) {
            Basis eve_basis = static_cast<Basis>(bit_dist(rng_));
            if (eve_basis != alice_bases[i]) {
                measured_bit = static_cast<uint8_t>(bit_dist(rng_));
            }
        }

        if (bob_bases[i] == alice_bases[i]) {
            if (prob_dist(rng_) < error_rate_) {
                measured_bit ^= 1;
            }
            bob_bits[i] = measured_bit;
        } else {
            bob_bits[i] = static_cast<uint8_t>(bit_dist(rng_));
        }
    }

    std::vector<uint8_t> matched_alice;
    std::vector<uint8_t> matched_bob;
    for (size_t i = 0; i < raw_bits_count; ++i) {
        if (alice_bases[i] == bob_bases[i]) {
            matched_alice.push_back(alice_bits[i]);
            matched_bob.push_back(bob_bits[i]);
        }
    }

    size_t sample_size = static_cast<size_t>(matched_alice.size() * sample_ratio);
    if (sample_size == 0) {
        return {{}, {}, 1.0, true};
    }

    size_t errors = 0;
    for (size_t i = 0; i < sample_size; ++i) {
        if (matched_alice[i] != matched_bob[i]) {
            errors++;
        }
    }

    double qber = static_cast<double>(errors) / static_cast<double>(sample_size);
    bool aborted = (qber > 0.11);

    std::vector<uint8_t> final_alice(matched_alice.begin() + sample_size, matched_alice.end());
    std::vector<uint8_t> final_bob(matched_bob.begin() + sample_size, matched_bob.end());

    return {final_alice, final_bob, qber, aborted};
}

} // namespace qkd

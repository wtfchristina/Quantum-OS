#pragma once
#include <vector>
#include <cstdint>
#include <random>

namespace qkd {

enum class Basis : uint8_t {
    RECTILINEAR = 0, // |0>, |1> (Z-basis)
    DIAGONAL    = 1  // |+>, |-> (X-basis)
};

struct SiftResult {
    std::vector<uint8_t> sifted_key_alice;
    std::vector<uint8_t> sifted_key_bob;
    double qber;
    bool aborted;
};

class BB84Simulator {
public:
    explicit BB84Simulator(double channel_error_rate = 0.02, double eavesdrop_rate = 0.0)
        : error_rate_(channel_error_rate), eve_rate_(eavesdrop_rate), rng_(std::random_device{}()) {}

    SiftResult run_exchange(size_t raw_bits_count, double sample_ratio = 0.1);

private:
    double error_rate_;
    double eve_rate_;
    std::mt19937 rng_;
};

} // namespace qkd

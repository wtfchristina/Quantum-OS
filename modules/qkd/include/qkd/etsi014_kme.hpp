#pragma once
#include <string>
#include <vector>
#include <optional>
#include <unordered_map>
#include <mutex>
#include <cstdint>

namespace qkd {

struct KeyContainer {
    std::string key_id;
    std::vector<uint8_t> key_bytes;
};

class KeyManagementEntity {
public:
    KeyManagementEntity() = default;

    void store_key(const std::string& key_id, std::vector<uint8_t> key_data);
    std::optional<KeyContainer> request_key();
    std::optional<std::vector<uint8_t>> get_key_by_id(const std::string& key_id);
    size_t available_keys() const;

private:
    mutable std::mutex pool_mutex_;
    std::unordered_map<std::string, std::vector<uint8_t>> key_pool_;
};

} // namespace qkd

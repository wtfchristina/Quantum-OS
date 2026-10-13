#include "qkd/etsi014_kme.hpp"

namespace qkd {

void KeyManagementEntity::store_key(const std::string& key_id, std::vector<uint8_t> key_data) {
    std::lock_guard<std::mutex> lock(pool_mutex_);
    key_pool_[key_id] = std::move(key_data);
}

std::optional<KeyContainer> KeyManagementEntity::request_key() {
    std::lock_guard<std::mutex> lock(pool_mutex_);
    if (key_pool_.empty()) {
        return std::nullopt;
    }
    auto it = key_pool_.begin();
    KeyContainer kc{it->first, it->second};
    key_pool_.erase(it);
    return kc;
}

std::optional<std::vector<uint8_t>> KeyManagementEntity::get_key_by_id(const std::string& key_id) {
    std::lock_guard<std::mutex> lock(pool_mutex_);
    auto it = key_pool_.find(key_id);
    if (it != key_pool_.end()) {
        std::vector<uint8_t> key = std::move(it->second);
        key_pool_.erase(it);
        return key;
    }
    return std::nullopt;
}

size_t KeyManagementEntity::available_keys() const {
    std::lock_guard<std::mutex> lock(pool_mutex_);
    return key_pool_.size();
}

} // namespace qkd

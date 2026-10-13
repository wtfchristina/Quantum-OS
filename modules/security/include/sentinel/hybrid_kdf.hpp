#pragma once
#include <vector>
#include <array>
#include <string>
#include <cstdint>
#include <openssl/evp.h>
#include <openssl/kdf.h>

namespace sentinel {

class HybridKDF {
public:
    static std::array<uint8_t, 32> derive(
        const std::vector<uint8_t>& pqc_kem_secret,
        const std::vector<uint8_t>& qkd_key,
        const std::string& label = "QuantumOS-Wire-v1")
    {
        std::vector<uint8_t> ikm;
        ikm.reserve(pqc_kem_secret.size() + qkd_key.size());
        ikm.insert(ikm.end(), pqc_kem_secret.begin(), pqc_kem_secret.end());
        ikm.insert(ikm.end(), qkd_key.begin(), qkd_key.end());

        std::array<uint8_t, 32> session_key{};
        EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_HKDF, nullptr);
        EVP_PKEY_derive_init(ctx);
        EVP_PKEY_CTX_set_hkdf_md(ctx, EVP_sha256());
        EVP_PKEY_CTX_set1_hkdf_key(ctx, ikm.data(), static_cast<int>(ikm.size()));
        EVP_PKEY_CTX_add1_hkdf_info(ctx, 
            reinterpret_cast<const unsigned char*>(label.data()), 
            static_cast<int>(label.size()));

        size_t out_len = session_key.size();
        EVP_PKEY_derive(ctx, session_key.data(), &out_len);
        EVP_PKEY_CTX_free(ctx);

        return session_key;
    }
};

} // namespace sentinel

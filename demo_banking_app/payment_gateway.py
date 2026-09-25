from cryptography.hazmat.primitives.asymmetric import dsa, dh

def establish_secure_handshake():
    # Deprecated DSA signing
    signer = dsa.generate_private_key(key_size=1024)
    # Classical Diffie-Hellman key exchange
    key_exchange = dh.generate_parameters(generator=2, key_size=2048)
    return signer, key_exchange

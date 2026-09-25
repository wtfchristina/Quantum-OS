from cryptography.hazmat.primitives.asymmetric import rsa, ec
import hashlib

def generate_user_keys():
    # Legacy RSA key generation vulnerable to Shor's algorithm
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    return private_key

def sign_jwt_payload(data):
    # Elliptic Curve signature vulnerable to quantum discrete log attacks
    curve = ec.SECP256R1()
    return curve

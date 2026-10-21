import base64

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from xcrap.utils.decryption import DecryptConfig, DecryptKeyConfig, decrypt_body


def encrypt_data(text: str, key: bytes, iv: bytes) -> bytes:
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(text.encode()) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    return encryptor.update(padded_data) + encryptor.finalize()


def test_decrypt_body_aes_cbc_hex():
    key = b"12345678901234567890123456789012"  # 32 bytes for AES-256
    iv = b"1234567890123456"  # 16 bytes for CBC
    secret = "Hello Decryption"

    encrypted = encrypt_data(secret, key, iv)
    encrypted_hex = encrypted.hex()

    config = DecryptConfig(
        inputEncoding="hex",
        outputEncoding="utf-8",
        algorithm="aes-256-cbc",
        key=DecryptKeyConfig(encoding="utf-8", value=key.decode()),
        iv=DecryptKeyConfig(encoding="utf-8", value=iv.decode()),
    )

    decrypted = decrypt_body(encrypted_hex, config)
    assert decrypted == secret


def test_decrypt_body_invalid_algorithm():
    config = DecryptConfig(key=DecryptKeyConfig(value="key"), iv=DecryptKeyConfig(value="iv"), algorithm="unknown")
    decryption_data = "deadbeef"
    with pytest.raises(ValueError, match="Unsupported algorithm"):
        decrypt_body(decryption_data, config)


def test_decrypt_body_aes_ecb_base64():
    key = b"12345678901234567890123456789012"
    secret = "ECB Secret"

    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(secret.encode()) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    encrypted = cipher.encryptor().update(padded_data) + cipher.encryptor().finalize()
    encrypted_b64 = base64.b64encode(encrypted).decode()

    config = DecryptConfig(
        inputEncoding="base64",
        algorithm="aes-256-ecb",
        key=DecryptKeyConfig(value=key.decode()),
        iv=DecryptKeyConfig(value="no-iv-needed"),  # ECB doesn't use IV but config requires it
    )

    decrypted = decrypt_body(encrypted_b64, config)
    assert decrypted == secret


def test_decrypt_body_unsupported_mode():
    config = DecryptConfig(
        key=DecryptKeyConfig(value="1" * 32),
        iv=DecryptKeyConfig(value="1" * 16),
        algorithm="aes-256-gcm",  # GCM not explicitly handled in my simple switcher
    )
    with pytest.raises(ValueError, match="Unsupported mode"):
        decrypt_body("deadbeef", config)

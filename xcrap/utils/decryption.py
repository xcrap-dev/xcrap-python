import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from pydantic import BaseModel, Field


class DecryptKeyConfig(BaseModel):
    encoding: str = "utf-8"
    value: str


class DecryptConfig(BaseModel):
    input_encoding: str = Field(alias="inputEncoding", default="hex")
    output_encoding: str = Field(alias="outputEncoding", default="utf-8")
    algorithm: str = "aes-256-cbc"
    key: DecryptKeyConfig
    iv: DecryptKeyConfig

    model_config = {"populate_by_name": True}


def _decode_value(value: str, encoding: str) -> bytes:
    if encoding == "hex":
        return bytes.fromhex(value)
    if encoding == "base64":
        return base64.b64decode(value)
    return value.encode(encoding)


def decrypt_body(encrypted_text: str, config: DecryptConfig) -> str:
    encrypted_buffer = _decode_value(encrypted_text, config.input_encoding)
    key_buffer = _decode_value(config.key.value, config.key.encoding)
    iv_buffer = _decode_value(config.iv.value, config.iv.encoding)

    # Simplified algorithm mapping for AES
    if "aes" in config.algorithm.lower():
        algorithm = algorithms.AES(key_buffer)
    else:
        raise ValueError(f"Unsupported algorithm: {config.algorithm}")

    if "cbc" in config.algorithm.lower():
        mode = modes.CBC(iv_buffer)
    elif "ecb" in config.algorithm.lower():
        mode = modes.ECB()
    else:
        raise ValueError(f"Unsupported mode in algorithm: {config.algorithm}")

    cipher = Cipher(algorithm, mode, backend=default_backend())
    decryptor = cipher.decryptor()

    padded_data = decryptor.update(encrypted_buffer) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()

    return data.decode(config.output_encoding)

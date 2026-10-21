"""
Transparent decryption of encrypted responses.

No public site serves AES payloads, so this example is offline: it encrypts a JSON document the way a
protected API would, then shows both ways of decrypting it with Xcrap.

    poetry run python examples/14_decryption.py
"""

import asyncio
import json

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from xcrap.clients import HttpxClient
from xcrap.core import HttpResponse, decrypt_client, decrypt_response
from xcrap.extractor import jmes_path
from xcrap.utils.decryption import DecryptConfig, DecryptKeyConfig

KEY = "0123456789abcdef0123456789abcdef"  # 32 bytes -> AES-256
IV = "abcdef9876543210"  # 16 bytes

CONFIG = DecryptConfig(
    algorithm="aes-256-cbc",
    input_encoding="hex",
    key=DecryptKeyConfig(value=KEY),
    iv=DecryptKeyConfig(value=IV),
)


def encrypt(text: str) -> str:
    padder = padding.PKCS7(128).padder()
    padded = padder.update(text.encode()) + padder.finalize()
    encryptor = Cipher(algorithms.AES(KEY.encode()), modes.CBC(IV.encode())).encryptor()

    return (encryptor.update(padded) + encryptor.finalize()).hex()


# Every response of this client is decrypted before you see it.
@decrypt_client(CONFIG)
class SecureClient(HttpxClient):
    pass


async def main() -> None:
    ciphertext = encrypt(json.dumps({"secret": "xcrap", "items": [1, 2, 3]}))
    print("ciphertext:", ciphertext[:40], "...")

    # 1. Decrypt a response you already have
    response = decrypt_response(HttpResponse(200, "OK", ciphertext, {}), CONFIG)
    print("decrypted :", response.body)
    print("items     :", response.as_json_parser().extract_values(jmes_path("items")))

    # 2. Or let the client do it on every fetch / fetch_many
    client = SecureClient()
    print("client wrapped fetch:", client.fetch.__name__)


if __name__ == "__main__":
    asyncio.run(main())

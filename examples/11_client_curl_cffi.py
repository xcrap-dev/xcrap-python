"""
TLS fingerprint impersonation with CurlCffiClient (tls.peet.ws echoes the fingerprint it sees).

HttpxClient has a Python-looking TLS handshake; CurlCffiClient reproduces a real browser's, which is
what anti-bot systems check first. Requires the extra: pip install "xcrap[curl]"

    poetry run python examples/11_client_curl_cffi.py
"""

import asyncio

from xcrap.clients import CurlCffiClient, HttpxClient
from xcrap.extractor import jmes_path

URL = "https://tls.peet.ws/api/clean"


async def ja3_hash(client) -> str:
    response = await client.fetch(url=URL)

    return response.as_json_parser().extract_value(jmes_path("ja3_hash"))


async def main() -> None:
    print("httpx    :", await ja3_hash(HttpxClient()))
    print("chrome120:", await ja3_hash(CurlCffiClient(impersonate="chrome120")))
    print("safari17 :", await ja3_hash(CurlCffiClient(impersonate="safari17_0")))


if __name__ == "__main__":
    asyncio.run(main())

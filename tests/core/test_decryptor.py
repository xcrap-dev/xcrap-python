import pytest
from unittest.mock import AsyncMock, MagicMock
from xcrap.core.decryptor import inject_decryptor, decrypt_client, decrypt_response
from xcrap.utils.decryption import DecryptConfig, DecryptKeyConfig
from xcrap.core.http_response import HttpResponse
from xcrap.core.http_client_base import HttpClientBase

class MockClient(HttpClientBase):
    async def fetch(self, *args, **kwargs):
        pass
    async def fetch_many(self, *args, **kwargs):
        pass

@pytest.fixture
def decrypt_config():
    return DecryptConfig(
        algorithm="aes-256-cbc",
        key=DecryptKeyConfig(value="1"*32),
        iv=DecryptKeyConfig(value="1"*16)
    )

@pytest.mark.asyncio
async def test_inject_decryptor(decrypt_config):
    # Mock decrypt_body to avoid real crypto overhead in this test
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("xcrap.core.decryptor.decrypt_body", lambda data, cfg: "decrypted_content")
        
        client = MockClient()
        client.fetch = AsyncMock(return_value=HttpResponse(
            status=200, status_text="OK", body="encrypted", headers={}
        ))
        
        inject_decryptor(client, decrypt_config)
        
        response = await client.fetch(url="test")
        assert response.body == "decrypted_content"
        assert response.headers.get("x-xcrap-decrypted") == "true"

@pytest.mark.asyncio
async def test_decrypt_client_decorator(decrypt_config):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("xcrap.core.decryptor.decrypt_body", lambda data, cfg: "decrypted_content")
        
        @decrypt_client(decrypt_config)
        class MyClient(MockClient):
            async def fetch(self, *args, **kwargs):
                return HttpResponse(status=200, status_text="OK", body="encrypted", headers={})

        client = MyClient()
        response = await client.fetch()
        assert response.body == "decrypted_content"

@pytest.mark.asyncio
async def test_inject_decryptor_fetch_many(decrypt_config):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("xcrap.core.decryptor.decrypt_body", lambda data, cfg: "decrypted")
        
        client = MockClient()
        client.fetch_many = AsyncMock(return_value=[
            HttpResponse(status=200, status_text="OK", body="enc1", headers={}),
            HttpResponse(status=404, status_text="Fail", body="fail", headers={})
        ])
        
        inject_decryptor(client, decrypt_config)
        
        responses = await client.fetch_many(requests=[])
        assert responses[0].body == "decrypted"
        assert responses[0].headers.get("x-xcrap-decrypted") == "true"
        assert responses[1].body == "fail"
        assert responses[1].headers.get("x-xcrap-decrypted") is None

def test_decrypt_response_util(decrypt_config):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("xcrap.core.decryptor.decrypt_body", lambda data, cfg: "decrypted")
        
        resp = HttpResponse(status=200, status_text="OK", body="enc", headers={})
        decrypted_resp = decrypt_response(resp, decrypt_config)
        assert decrypted_resp.body == "decrypted"
        
        # Test decryption failure fallback
        def fail_decrypt(d, c): raise Exception("fail")
        mp.setattr("xcrap.core.decryptor.decrypt_body", fail_decrypt)
        
        resp_fail = HttpResponse(status=200, status_text="OK", body="enc", headers={})
        fallback = decrypt_response(resp_fail, decrypt_config)
        assert fallback.body == "enc"

@pytest.mark.asyncio
async def test_inject_decryptor_fetch_error(decrypt_config):
    with pytest.MonkeyPatch.context() as mp:
        def fail_decrypt(d, c): raise Exception("fail")
        mp.setattr("xcrap.core.decryptor.decrypt_body", fail_decrypt)
        
        client = MockClient()
        client.fetch = AsyncMock(return_value=HttpResponse(
            status=200, status_text="OK", body="encrypted", headers={}
        ))
        
        inject_decryptor(client, decrypt_config)
        response = await client.fetch()
        assert response.body == "encrypted" # Fallback to original

@pytest.mark.asyncio
async def test_inject_decryptor_fetch_many_error(decrypt_config):
    with pytest.MonkeyPatch.context() as mp:
        def fail_decrypt(d, c): raise Exception("fail")
        mp.setattr("xcrap.core.decryptor.decrypt_body", fail_decrypt)
        
        client = MockClient()
        client.fetch_many = AsyncMock(return_value=[
            HttpResponse(status=200, status_text="OK", body="enc", headers={})
        ])
        
        inject_decryptor(client, decrypt_config)
        responses = await client.fetch_many(requests=[])
        assert responses[0].body == "enc"

@pytest.mark.asyncio
async def test_inject_decryptor_no_decrypt_on_fail(decrypt_config):
    client = MockClient()
    client.fetch = AsyncMock(return_value=HttpResponse(status=404, status_text="Not Found", body="error", headers={}))
    inject_decryptor(client, decrypt_config)
    resp = await client.fetch()
    assert resp.status == 404
    assert resp.body == "error"
    assert resp.headers.get("x-xcrap-decrypted") is None


@pytest.mark.asyncio
async def test_mock_client_stubs_are_callable():
    client = MockClient()

    assert await client.fetch("https://a.test") is None
    assert await client.fetch_many([]) is None

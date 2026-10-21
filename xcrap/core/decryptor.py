from typing import Type, TypeVar

from ..utils.decryption import DecryptConfig, decrypt_body
from .http_client_base import HttpClientBase
from .http_response import HttpResponse

T = TypeVar("T", bound=HttpClientBase)


def inject_decryptor(client: T, config: DecryptConfig) -> T:
    original_fetch = client.fetch
    original_fetch_many = client.fetch_many

    async def fetch_wrapper(*args, **kwargs) -> HttpResponse:
        response = await original_fetch(*args, **kwargs)
        if response.is_success() and response.body:
            try:
                decrypted = decrypt_body(response.body, config)
                return HttpResponse(
                    status=response.status,
                    status_text=response.status_text,
                    body=decrypted,
                    headers={**response.headers, "x-xcrap-decrypted": "true"},
                    attempts=response.attempts,
                    failed_attempts=response.failed_attempts,
                )
            except Exception:
                # If decryption fails, we might want to log it or just return the original response
                return response
        return response

    async def fetch_many_wrapper(*args, **kwargs) -> list[HttpResponse]:
        responses = await original_fetch_many(*args, **kwargs)
        new_responses = []
        for response in responses:
            if response.is_success() and response.body:
                try:
                    decrypted = decrypt_body(response.body, config)
                    new_responses.append(
                        HttpResponse(
                            status=response.status,
                            status_text=response.status_text,
                            body=decrypted,
                            headers={**response.headers, "x-xcrap-decrypted": "true"},
                            attempts=response.attempts,
                            failed_attempts=response.failed_attempts,
                        )
                    )
                    continue
                except Exception:
                    pass
            new_responses.append(response)
        return new_responses

    # Monkey patch the instance methods
    client.fetch = fetch_wrapper  # type: ignore
    client.fetch_many = fetch_many_wrapper  # type: ignore
    return client


def decrypt_client(config: DecryptConfig):
    """
    Class decorator to inject a decryptor into an HttpClient class.
    """

    def decorator(cls: Type[T]) -> Type[T]:
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            inject_decryptor(self, config)

        cls.__init__ = new_init  # type: ignore
        return cls

    return decorator


def decrypt_response(response: HttpResponse, config: DecryptConfig) -> HttpResponse:
    """
    Decrypts a single HttpResponse object.
    """
    if response.is_success() and response.body:
        try:
            decrypted = decrypt_body(response.body, config)
            return HttpResponse(
                status=response.status,
                status_text=response.status_text,
                body=decrypted,
                headers={**response.headers, "x-xcrap-decrypted": "true"},
                attempts=response.attempts,
                failed_attempts=response.failed_attempts,
            )
        except Exception:
            pass
    return response

import asyncio
from typing import Any, Callable, Optional

try:
    from curl_cffi.requests import AsyncSession, Response as CurlResponse
except ImportError:
    AsyncSession = None  # type: ignore
    CurlResponse = None  # type: ignore

from ..core.errors import DependencyMissingError
from ..core.http_client_base import (
    ExecuteRequestOptions,
    HttpClientBase,
    HttpClientFetchOptions,
)
from ..core.http_response import FailedAttempt, HttpResponse


class CurlCffiClient(HttpClientBase):
    """
    High-performance HTTP client utilizing curl-cffi for anti-bot, JA3, TLS/HTTP2 browser impersonation.
    Requires 'curl-cffi' package: pip install xcrap[curl]
    """

    def __init__(
        self,
        impersonate: str = "chrome120",
        proxy_url: Optional[str | Callable[[], str]] = None,
        proxy: Optional[str | Callable[[], str]] = None,
        user_agent: Optional[str | Callable[[], str]] = None,
        timeout: float = 30.0,
    ) -> None:
        if AsyncSession is None:
            raise DependencyMissingError(package_name="curl-cffi", extra_name="curl")

        super().__init__(proxy_url=proxy_url, proxy=proxy, user_agent=user_agent)
        self.impersonate = impersonate
        self.timeout = timeout

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        retries: Optional[int] = 0,
        max_retries: Optional[int] = 0,
        retry_delay: Optional[int] = 0,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> HttpResponse:
        if AsyncSession is None:
            raise DependencyMissingError(package_name="curl-cffi", extra_name="curl")

        current_retries = 0
        total_max_retries = max_retries or retries or 0
        current_retry_delay = retry_delay or 0

        req_headers = {"User-Agent": self._current_user_agent}
        if headers:
            req_headers.update(headers)

        proxy = self._current_proxy_url or self._current_proxy
        failed_attempts: list[FailedAttempt] = []

        while True:
            try:
                async with AsyncSession(impersonate=self.impersonate) as session:
                    response: CurlResponse = await session.request(
                        method=method,
                        url=url,
                        headers=req_headers,
                        proxy=proxy,
                        timeout=self.timeout,
                        **kwargs,
                    )

                return HttpResponse(
                    status=response.status_code,
                    status_text=getattr(response, "reason", "OK") or "OK",
                    body=response.text,
                    headers=dict(response.headers),
                    attempts=current_retries + 1,
                    failed_attempts=failed_attempts,
                )

            except Exception as e:
                failed_attempts.append(
                    {
                        "timestamp": int(asyncio.get_event_loop().time() * 1000),
                        "error": str(e),
                    }
                )

                if current_retries < total_max_retries:
                    current_retries += 1
                    if current_retry_delay > 0:
                        await asyncio.sleep(current_retry_delay / 1000)
                else:
                    return HttpResponse(
                        status=500,
                        status_text=f"Failed after {current_retries + 1} attempts: {str(e)}",
                        body="",
                        headers={},
                        attempts=current_retries + 1,
                        failed_attempts=failed_attempts,
                    )

    async def fetch_many(
        self,
        requests: list[HttpClientFetchOptions],
        request_delay: Optional[int] = None,
        concurrency: Optional[int] = None,
    ) -> list[HttpResponse]:
        results: list[HttpResponse | None] = [None] * len(requests)
        executing: list[asyncio.Task] = []

        for index, request in enumerate(requests):
            while self._should_throttle(executing, concurrency):
                await self._handle_concurrency(executing)

            task = asyncio.create_task(
                self._execute_request(
                    ExecuteRequestOptions(
                        index=index,
                        request=request,
                        results=results,
                        request_delay=request_delay,
                    )
                )
            )
            executing.append(task)

        if executing:
            await asyncio.gather(*executing)

        return [res for res in results if res is not None]


__all__ = ["CurlCffiClient"]

import asyncio
import time
from typing import Callable, Optional

import httpx

from ..core import (
    ExecuteRequestOptions,
    HttpClientBase,
    HttpClientFetchOptions,
    HttpResponse,
)


class HttpxClient(HttpClientBase):
    def __init__(
        self,
        proxy_url: Optional[str | Callable[[], str]] = None,
        proxy: Optional[str | Callable[[], str]] = None,
        user_agent: Optional[str | Callable[[], str]] = None,
    ) -> None:
        super().__init__(proxy_url, proxy, user_agent)
        self.httpx_client = httpx.AsyncClient(follow_redirects=True)

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        retries: Optional[int] = 0,
        max_retries: Optional[int] = 0,
        retry_delay: Optional[int] = 0,
        headers: Optional[dict[str, str]] = None,
    ) -> HttpResponse:
        max_retries = max_retries or 0
        retries = retries or 0
        retry_delay = retry_delay or 0

        failed_attempts = []
        request_headers = {"User-Agent": self._current_user_agent}
        if headers:
            request_headers.update(headers)

        async def attempt_request(current_retry: int) -> HttpResponse:
            try:
                target_url = f"{self._current_proxy_url}{url}" if self._current_proxy_url else url

                response = await self.httpx_client.request(
                    method=method,
                    url=target_url,
                    headers=request_headers,
                )

                if not self._is_success(response.status_code):
                    raise httpx.HTTPStatusError(
                        message=f"Invalid status code: {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                return HttpResponse(
                    status=response.status_code,
                    status_text=response.reason_phrase,
                    body=response.text,
                    headers=dict(response.headers),
                    attempts=current_retry + 1,
                    failed_attempts=failed_attempts,
                )

            except Exception as error:
                error_message = str(error)

                failed_attempts.append({"error": error_message, "timestamp": int(time.time())})

                if current_retry < max_retries:
                    if retry_delay and retry_delay > 0:
                        await asyncio.sleep(retry_delay / 1000)

                    return await attempt_request(current_retry + 1)

                status = 500
                status_text = "Request Failed"
                body = error_message
                headers = {}

                if isinstance(error, httpx.HTTPStatusError):
                    status = error.response.status_code
                    status_text = error.response.reason_phrase
                    body = error.response.text
                    headers = dict(error.response.headers)

                return HttpResponse(
                    status=status,
                    status_text=status_text,
                    body=body,
                    headers=headers,
                    attempts=current_retry + 1,
                    failed_attempts=failed_attempts,
                )

        return await attempt_request(retries)

    async def fetch_many(
        self,
        requests: list[HttpClientFetchOptions],
        request_delay: Optional[int],
        concurrency: Optional[int],
    ) -> list[HttpResponse]:

        results: list[HttpResponse | None] = [None] * len(requests)
        executing: list[asyncio.Task] = []

        for i, request in enumerate(requests):
            execute_options: ExecuteRequestOptions = {
                "index": i,
                "request": request,
                "results": results,
                "request_delay": request_delay,
            }

            task = asyncio.create_task(self._execute_request(execute_options))
            executing.append(task)

            if self._should_throttle(executing, concurrency):
                await self._handle_concurrency(executing)

        if executing:
            await asyncio.gather(*executing)

        return results


__all__ = ["HttpxClient"]

import asyncio
from typing import Any, Callable, Optional, Sequence, Union

try:
    from playwright.async_api import Browser, Page, async_playwright
except ImportError:
    async_playwright = None  # type: ignore
    Browser = None  # type: ignore
    Page = None  # type: ignore

from ..core.errors import DependencyMissingError
from ..core.http_client_base import (
    ExecuteRequestOptions,
    HttpClientBase,
    HttpClientFetchOptions,
)
from ..core.http_response import FailedAttempt, HttpResponse

PlaywrightActionFunc = Callable[[Page], Any]


class PlaywrightAction:
    def __init__(self, action_type: str, func: PlaywrightActionFunc) -> None:
        self.action_type = action_type.lower()
        self.func = func


class PlaywrightClient(HttpClientBase):
    """
    Headless browser client based on Playwright for client-side rendering (SPAs) and user interactions.
    Requires 'playwright' package: pip install xcrap[playwright]
    """

    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        proxy_url: Optional[str | Callable[[], str]] = None,
        proxy: Optional[str | Callable[[], str]] = None,
        user_agent: Optional[str | Callable[[], str]] = None,
        timeout: float = 30000.0,
        viewport: Optional[dict[str, int]] = None,
    ) -> None:
        if async_playwright is None:
            raise DependencyMissingError(package_name="playwright", extra_name="playwright")

        super().__init__(proxy_url=proxy_url, proxy=proxy, user_agent=user_agent)
        self.browser_type = browser_type.lower()
        self.headless = headless
        self.timeout = timeout
        self.viewport = viewport or {"width": 1920, "height": 1080}

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        retries: Optional[int] = 0,
        max_retries: Optional[int] = 0,
        retry_delay: Optional[int] = 0,
        headers: Optional[dict[str, str]] = None,
        actions: Optional[Sequence[Union[dict, Callable[[Page], Any]]]] = None,
        wait_until: str = "domcontentloaded",
        **kwargs: Any,
    ) -> HttpResponse:
        if async_playwright is None:
            raise DependencyMissingError(package_name="playwright", extra_name="playwright")

        current_retries = 0
        total_max_retries = max_retries or retries or 0
        current_retry_delay = retry_delay or 0
        failed_attempts: list[FailedAttempt] = []

        proxy_str = self._current_proxy_url or self._current_proxy
        proxy_cfg = {"server": proxy_str} if proxy_str else None

        while True:
            try:
                async with async_playwright() as p:
                    launcher = getattr(p, self.browser_type, p.chromium)
                    browser: Browser = await launcher.launch(
                        headless=self.headless,
                        proxy=proxy_cfg,
                    )
                    context = await browser.new_context(
                        user_agent=self._current_user_agent,
                        viewport=self.viewport,
                        extra_http_headers=headers,
                    )
                    page: Page = await context.new_page()
                    timeout_res = page.set_default_timeout(self.timeout)
                    
                    if asyncio.iscoroutine(timeout_res):
                        await timeout_res

                    # Execute beforeRequest actions
                    if actions:
                        for act in actions:
                            if isinstance(act, dict) and act.get("type", "").lower() in ("beforerequest", "before_request"):
                                fn = act.get("func") or act.get("exec")
                                if fn:
                                    res = fn(page)
                                    if asyncio.iscoroutine(res):
                                        await res

                    response = await page.goto(url, wait_until=wait_until)
                    status_code = response.status if response else 200

                    # Execute afterRequest / general actions
                    if actions:
                        for act in actions:
                            if callable(act):
                                res = act(page)
                                if asyncio.iscoroutine(res):
                                    await res
                            elif isinstance(act, dict) and act.get("type", "").lower() in ("afterrequest", "after_request", "action"):
                                fn = act.get("func") or act.get("exec")
                                if fn:
                                    res = fn(page)
                                    if asyncio.iscoroutine(res):
                                        await res

                    content = await page.content()
                    resp_headers = await response.all_headers() if response else {}

                    await browser.close()

                    return HttpResponse(
                        status=status_code,
                        status_text="OK" if status_code < 400 else "Error",
                        body=content,
                        headers=resp_headers,
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


__all__ = ["PlaywrightClient", "PlaywrightAction"]

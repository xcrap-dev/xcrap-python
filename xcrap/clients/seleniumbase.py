import asyncio
import time
from typing import Any, Callable, Optional, Sequence, Union

try:
    from seleniumbase import Driver
except ImportError:
    Driver = None  # type: ignore

from ..core.errors import DependencyMissingError
from ..core.http_client_base import (
    ExecuteRequestOptions,
    HttpClientBase,
    HttpClientFetchOptions,
)
from ..core.http_response import FailedAttempt, HttpResponse

SeleniumBaseActionFunc = Callable[[Any], Any]


class SeleniumBaseClient(HttpClientBase):
    """
    Browser client based on SeleniumBase (https://seleniumbase.io), with its UC (undetected-chromedriver) mode
    enabled by default to get past bot-detection systems such as Cloudflare Turnstile.
    WebDriver operations run in a worker thread via asyncio.to_thread.
    Requires 'seleniumbase' package: pip install xcrap[seleniumbase]

    `driver_options` are extra keyword arguments for `seleniumbase.Driver(...)` (e.g. `{"incognito": True}`).
    Actions receive the SeleniumBase driver, which exposes the SeleniumBase API (`uc_gui_click_captcha()`,
    `uc_click()`, ...) on top of the regular WebDriver one.
    """

    def __init__(
        self,
        browser_type: str = "chrome",
        headless: bool = True,
        uc: bool = True,
        reconnect_time: float = 3.0,
        proxy_url: Optional[str | Callable[[], str]] = None,
        proxy: Optional[str | Callable[[], str]] = None,
        user_agent: Optional[str | Callable[[], str]] = None,
        timeout: float = 30.0,
        driver_options: Optional[dict[str, Any]] = None,
    ) -> None:
        if Driver is None:
            raise DependencyMissingError(package_name="seleniumbase", extra_name="seleniumbase")

        super().__init__(proxy_url=proxy_url, proxy=proxy, user_agent=user_agent)
        self.browser_type = browser_type.lower()
        self.headless = headless
        self.uc = uc
        self.reconnect_time = reconnect_time
        self.timeout = timeout
        self.driver_options = driver_options or {}

    def _build_driver(self) -> Any:
        options: dict[str, Any] = {
            "browser": self.browser_type,
            "headless": self.headless,
            "uc": self.uc,
            "agent": self._current_user_agent,
        }

        proxy_str = self._current_proxy_url or self._current_proxy

        if proxy_str:
            # SeleniumBase expects "host:port" or "user:pass@host:port", without a scheme.
            options["proxy"] = proxy_str.split("://", 1)[-1]

        options.update(self.driver_options)
        driver = Driver(**options)

        if hasattr(driver, "set_page_load_timeout"):
            driver.set_page_load_timeout(self.timeout)

        return driver

    def _sync_fetch(
        self,
        url: str,
        actions: Optional[Sequence[Union[dict, SeleniumBaseActionFunc]]] = None,
    ) -> str:
        driver = self._build_driver()

        try:
            if actions:
                for act in actions:
                    if isinstance(act, dict) and act.get("type", "").lower() in ("beforerequest", "before_request"):
                        fn = act.get("func") or act.get("exec")
                        if fn:
                            fn(driver)

            # UC mode opens the page, disconnects the driver for `reconnect_time` seconds so the site cannot
            # detect it while its challenges run, then reconnects.
            if self.uc and hasattr(driver, "uc_open_with_reconnect"):
                driver.uc_open_with_reconnect(url, self.reconnect_time)
            else:
                driver.get(url)

            if actions:
                for act in actions:
                    if callable(act):
                        act(driver)
                    elif isinstance(act, dict) and act.get("type", "").lower() in ("afterrequest", "after_request", "action"):
                        fn = act.get("func") or act.get("exec")
                        if fn:
                            fn(driver)

            return driver.page_source
        finally:
            if hasattr(driver, "quit"):
                driver.quit()

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        retries: Optional[int] = 0,
        max_retries: Optional[int] = 0,
        retry_delay: Optional[int] = 0,
        headers: Optional[dict[str, str]] = None,
        actions: Optional[Sequence[Union[dict, SeleniumBaseActionFunc]]] = None,
        **kwargs: Any,
    ) -> HttpResponse:
        if Driver is None:
            raise DependencyMissingError(package_name="seleniumbase", extra_name="seleniumbase")

        current_retries = 0
        total_max_retries = max_retries or retries or 0
        current_retry_delay = retry_delay or 0
        failed_attempts: list[FailedAttempt] = []

        while True:
            try:
                body = await asyncio.to_thread(self._sync_fetch, url=url, actions=actions)

                # WebDriver cannot read HTTP status codes or headers: a rendered page is reported as 200.
                return HttpResponse(
                    status=200,
                    status_text="OK",
                    body=body,
                    headers={},
                    attempts=current_retries + 1,
                    failed_attempts=failed_attempts,
                )

            except Exception as e:
                failed_attempts.append({"timestamp": int(time.time() * 1000), "error": str(e)})

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


__all__ = ["SeleniumBaseClient"]

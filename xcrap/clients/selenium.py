import asyncio
import time
from typing import Any, Callable, Optional, Sequence, Union

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
except ImportError:
    webdriver = None  # type: ignore
    ChromeOptions = None  # type: ignore
    FirefoxOptions = None  # type: ignore
    EdgeOptions = None  # type: ignore

from ..core.errors import DependencyMissingError
from ..core.http_client_base import (
    ExecuteRequestOptions,
    HttpClientBase,
    HttpClientFetchOptions,
)
from ..core.http_response import FailedAttempt, HttpResponse

SeleniumActionFunc = Callable[[Any], Any]


class SeleniumClient(HttpClientBase):
    """
    Automated browser client based on Selenium WebDriver.
    Executes WebDriver operations asynchronously via asyncio.to_thread.
    Requires 'selenium' package: pip install xcrap[selenium]
    """

    def __init__(
        self,
        browser_type: str = "chrome",
        headless: bool = True,
        proxy_url: Optional[str | Callable[[], str]] = None,
        proxy: Optional[str | Callable[[], str]] = None,
        user_agent: Optional[str | Callable[[], str]] = None,
        timeout: float = 30.0,
        driver_options: Optional[Any] = None,
    ) -> None:
        if webdriver is None:
            raise DependencyMissingError(package_name="selenium", extra_name="selenium")

        super().__init__(proxy_url=proxy_url, proxy=proxy, user_agent=user_agent)
        self.browser_type = browser_type.lower()
        self.headless = headless
        self.timeout = timeout
        self.driver_options = driver_options

    def _build_driver(self) -> Any:
        proxy_str = self._current_proxy_url or self._current_proxy
        ua_str = self._current_user_agent

        if self.browser_type == "firefox":
            options = self.driver_options or FirefoxOptions()
            if self.headless and hasattr(options, "add_argument"):
                options.add_argument("-headless")
            if ua_str and hasattr(options, "set_preference"):
                options.set_preference("general.useragent.override", ua_str)
            if proxy_str and hasattr(options, "add_argument"):
                options.add_argument(f"--proxy-server={proxy_str}")
            driver = webdriver.Firefox(options=options)

        elif self.browser_type == "edge":
            options = self.driver_options or EdgeOptions()
            if self.headless and hasattr(options, "add_argument"):
                options.add_argument("--headless=new")
            if ua_str and hasattr(options, "add_argument"):
                options.add_argument(f"--user-agent={ua_str}")
            if proxy_str and hasattr(options, "add_argument"):
                options.add_argument(f"--proxy-server={proxy_str}")
            driver = webdriver.Edge(options=options)

        else:
            # Default: Chrome
            options = self.driver_options or ChromeOptions()
            if self.headless and hasattr(options, "add_argument"):
                options.add_argument("--headless=new")
            if ua_str and hasattr(options, "add_argument"):
                options.add_argument(f"--user-agent={ua_str}")
            if proxy_str and hasattr(options, "add_argument"):
                options.add_argument(f"--proxy-server={proxy_str}")
            driver = webdriver.Chrome(options=options)

        if hasattr(driver, "set_page_load_timeout"):
            driver.set_page_load_timeout(self.timeout)

        return driver

    def _sync_fetch(
        self,
        url: str,
        actions: Optional[Sequence[Union[dict, SeleniumActionFunc]]] = None,
    ) -> tuple[int, str, str, dict[str, str]]:
        driver = self._build_driver()
        try:
            # Execute before_request actions
            if actions:
                for act in actions:
                    if isinstance(act, dict) and act.get("type", "").lower() in ("beforerequest", "before_request"):
                        fn = act.get("func") or act.get("exec")
                        if fn:
                            fn(driver)

            driver.get(url)

            # Execute after_request actions
            if actions:
                for act in actions:
                    if callable(act):
                        act(driver)
                    elif isinstance(act, dict) and act.get("type", "").lower() in ("afterrequest", "after_request", "action"):
                        fn = act.get("func") or act.get("exec")
                        if fn:
                            fn(driver)

            body = driver.page_source
            return 200, "OK", body, {}
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
        actions: Optional[Sequence[Union[dict, SeleniumActionFunc]]] = None,
        **kwargs: Any,
    ) -> HttpResponse:
        if webdriver is None:
            raise DependencyMissingError(package_name="selenium", extra_name="selenium")

        current_retries = 0
        total_max_retries = max_retries or retries or 0
        current_retry_delay = retry_delay or 0
        failed_attempts: list[FailedAttempt] = []

        while True:
            try:
                status, status_text, body, resp_headers = await asyncio.to_thread(
                    self._sync_fetch,
                    url=url,
                    actions=actions,
                )

                return HttpResponse(
                    status=status,
                    status_text=status_text,
                    body=body,
                    headers=resp_headers,
                    attempts=current_retries + 1,
                    failed_attempts=failed_attempts,
                )

            except Exception as e:
                failed_attempts.append(
                    {
                        "timestamp": int(time.time() * 1000),
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


__all__ = ["SeleniumClient"]

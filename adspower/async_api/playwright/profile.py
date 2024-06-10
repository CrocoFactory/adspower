from datetime import datetime
from typing import Optional, AsyncContextManager
from adspower.async_api._base_profile import _BaseProfile
from adspower.async_api.group import Group
from adspower.async_api.category import Category
from playwright.async_api import async_playwright, BrowserContext, Playwright, Browser
from adspower.types import IpChecker


class Profile(_BaseProfile):
    def __init__(
            self,
            id_: str,
            serial_number: int,
            name: str | None,
            group: Group,
            domain_name: str | None,
            username: str | None,
            remark: str | None,
            created_time: datetime,
            category: Category | None,
            ip: str | None,
            ip_country: str | None,
            ip_checker: IpChecker,
            fakey: str | None,
            password: str | None,
            last_open_time: datetime | None
    ):
        """
        The class interacting with profile management.

        :param id_: Profile id
        :param serial_number: Serial number of the profile
        :param name: Name of the profile
        :param group: Group where the profile is located
        :param domain_name: Domain name, such as facebook.com, amazon.com... Will open when getting the browser.
        :param username: If username duplication is allowed, leave here empty.
        :param remark: Description of the profile
        :param created_time: Creation time of the profile
        :param category: Extension category for the profile
        :param ip: Proxy IP used for an account to log in. Fill in when proxy software is lumauto or oxylabs.
        :param ip_country: Country or region your lumauto and oxylabs account belongs to. Without lumauto and oxylabs IP please enter country.
        :param ip_checker: IP checker for the profile. Choose from ['ip2location', 'ipapi']
        :param fakey: 2FA-key. This applies to online 2FA code generator, which works similarly to authenticators.
        :param password: If password duplication is allowed, leave here empty.
        :param last_open_time: Last open time of the profile
        """
        super().__init__(
            id_,
            serial_number,
            name,
            group,
            domain_name,
            username,
            remark,
            created_time,
            category,
            ip,
            ip_country,
            ip_checker,
            fakey,
            password,
            last_open_time,
        )
        self.__playwright: Playwright | None = None
        self.__browser_app: Browser | None = None

    @classmethod
    async def anonymous(cls, group: Group) -> AsyncContextManager[BrowserContext]:
        return super().anonymous(group)

    async def __aenter__(self) -> BrowserContext:
        return await super().__aenter__()

    @property
    def browser(self) -> BrowserContext:
        """
        :return: WebDriver connected to the profile if it's open, None otherwise
        """
        return self._browser

    async def get_browser(
            self,
            ip_tab: bool = True,
            new_first_tab: bool = True,
            launch_args: Optional[list[str]] = None,
            headless: bool = False,
            disable_password_filling: bool = False,
            clear_cache_after_closing: bool = False,
            enable_password_saving: bool = False,
            close_tabs: bool = True,
            start_maximized: bool = True
    ) -> BrowserContext:
        """
        Get a BrowserContext connected to the profile
        :param ip_tab: Whether to open the ip detection page
        :param new_first_tab: Whether to use the new version of the ip detection page
        :param launch_args: Browser startup parameters. eg: --blink-settings=imagesEnabled=false:
                            Prohibit image loading. --disable-notifications: Disable notifications
        :param headless: Whether to start the headless browser
        :param disable_password_filling: Whether to disable the function of filling password
        :param clear_cache_after_closing: Whether to delete the cache after closing the browser
        :param enable_password_saving: Whether to allow password saving
        :param close_tabs: Whether to close all startup tabs
        :param start_maximized: Whether to enable maximized window size at start
        :return: BrowserContext instance
        """
        response = await self._get_browser(
            ip_tab,
            new_first_tab,
            launch_args,
            headless,
            disable_password_filling,
            clear_cache_after_closing,
            enable_password_saving,
        )
        playwright = self.__playwright = (await async_playwright().start())
        browser_app = await playwright.chromium.connect_over_cdp(f'http://localhost:{response["debug_port"]}')
        self.__browser_app = browser_app
        browser = self._browser = browser_app.contexts[0]

        return browser

    async def close_tabs(self) -> None:
        """
        Closes all tabs, exclude current tab
        :return: None
        """
        browser = self._browser
        new_page = await browser.new_page()

        for page in browser.pages:
            if not (page is new_page):
                await page.close()

    async def quit(self) -> None:
        """
        Quit the browser
        :return: None
        """
        await self._quit()
        await self._browser.close()
        await self.__browser_app.close()
        await self.__playwright.stop()

        self._browser = None
        self.__playwright = None
        self.__browser_app = None

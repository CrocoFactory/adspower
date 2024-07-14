from datetime import datetime
from typing import Optional, ClassVar, Self, Any
from .category import Category
from .http_client import HTTPClient
from .group import Group
from adspower._base_profile_api import _BaseProfileAPI
from adspower.types import (ProxyConfig, Cookies, FingerprintConfig, RepeatConfigType, BrowserResponse,
                            UserSort, IpChecker)
from ..utils import _convert_json


class ProfileAPI(_BaseProfileAPI):
    _client: ClassVar[type[HTTPClient]] = HTTPClient

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
        The class interacting with profile management. It doesn't interact with getting a browser to use it with Selenium or
        Playwright. If you want to interact with that, you need to use `Profile` class. 

        :param id_: Profile id
        :param serial_number: Serial number of the profile
        :param name: Name of the profile
        :param group: Group where the profile is located
        :param domain_name: Domain name, such as facebook.com, amazon.com... Will open when getting the browser.
        :param username: Username for the domain name (e.g. facebook.com, amazon)
        :param remark: Description of the profile
        :param created_time: Creation time of the profile
        :param category: Extension category for the profile
        :param ip: Proxy IP used for an account to log in. Fill in when proxy software is lumauto or oxylabs.
        :param ip_country: Country or region your lumauto and oxylabs account belongs to. Without lumauto and oxylabs IP please enter country.
        :param ip_checker: IP checker for the profile. Choose from ['ip2location', 'ipapi']
        :param fakey: 2FA-key for the domain name (e.g. facebook.com, amazon).
                      This applies to online 2FA code generator, which works similarly to authenticators.
        :param password: Password for the domain name (e.g. facebook.com, amazon)
        :param last_open_time: Last open time of the profile
        """
        _BaseProfileAPI.__init__(
            self,
            id_,
            serial_number,
            name, group,
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
            last_open_time
        )

    @staticmethod
    def _get_init_args(response: dict[str, Any]) -> dict[str, Any]:
        response = _convert_json(response)

        response['id_'] = response.pop('user_id')
        response['category'] = Category(id_=id_, name=None, remark=None) if (
            id_ := response.pop('sys_app_cate_id')) else None

        last_open_time = response['last_open_time']
        response['created_time'] = datetime.fromtimestamp(response['created_time'])
        response['last_open_time'] = datetime.fromtimestamp(last_open_time) if last_open_time else None
        response['ip_checker'] = response.pop('ipchecker')

        response['group'] = Group(id_=response.pop('group_id'), name=response.pop('group_name'), remark=None)

        response.pop('fbcc_proxy_acc_id')

        return response

    @classmethod
    def create(
            cls,
            group: Group,
            name: Optional[str] = None,
            domain_name: Optional[str] = None,
            open_urls: Optional[list[str]] = None,
            repeat_config: Optional[RepeatConfigType] = None,
            username: Optional[str] = None,
            password: Optional[str] = None,
            fakey: Optional[str] = None,
            cookies: Optional[Cookies] = None,
            ignore_cookie_error: bool = False,
            ip: Optional[str] = None,
            ip_country: Optional[str] = None,
            region: Optional[str] = None,
            city: Optional[str] = None,
            remark: Optional[str] = None,
            ip_checker: Optional[IpChecker] = None,
            category: Optional[Category] = None,
            proxy_config: Optional[ProxyConfig] = None,
            fingerprint_config: Optional[FingerprintConfig] = None
    ) -> Self:
        """
        Create a new profile

        :param name: Name of the profile
        :param group: Group where the profile is located
        :param domain_name: Domain name, such as facebook.com, amazon.com... Will open when getting the browser.
        :param open_urls: Other urls when opening browser. If leaving it empty, will open the domain name url.
        :param repeat_config: Account deduplication. Default setting: Allow duplication.
                              0: Allow duplication;
                              2: Deduplication based on the account name/password;
                              3: Deduplication based on cookie;
                              4: Deduplication based on c_user (c_user is a specific tag for Facebook)
        :param username: Username for the domain name (e.g. facebook.com, amazon)
        :param remark: Description of the profile
        :param category: Extension category for the profile
        :param ip: Proxy IP used for an account to log in. Fill in when proxy software is lumauto or oxylabs.
        :param ip_country: Country or region your lumauto and oxylabs account belongs to.Without lumauto and oxylabs IP please enter country.
        :param region: State or province where account logged in.
        :param city: City where account logged in.
        :param ip_checker: IP checker for the profile. Choose from ['ip2location', 'ipapi']
        :param fakey: 2FA-key for the domain name (e.g. facebook.com, amazon).
                      This applies to online 2FA code generator, which works similarly to authenticators.
        :param password: Password for the domain name (e.g. facebook.com, amazon)
        :param cookies: Cookies to be set when opening browser
        :param ignore_cookie_error: 0：When the cookie verification fails, the cookie format is incorrectly returned directly
                                    1：When the cookie verification fails, filter out the data in the wrong format and keep the cookie in the correct format
                                    Only supports netspace
        :param proxy_config: Dictionary containing proxy info
        :param fingerprint_config: Dictionary containing fingerprint info

        :return: A Profile instance
        """
        http_client = cls._client
        args, handler = cls._create(
            group,
            name,
            domain_name,
            open_urls,
            repeat_config,
            username,
            password,
            fakey,
            cookies,
            ignore_cookie_error,
            ip,
            ip_country,
            region,
            city,
            remark,
            ip_checker,
            category,
            proxy_config,
            fingerprint_config
        )

        with http_client() as client:
            response = client.post(**args).json()['data']

        return handler(response)[0]

    @classmethod
    def query(
            cls,
            group: Optional[Group] = None,
            id_: Optional[str] = None,
            name: Optional[str] = None,
            serial_number: Optional[int] = None,
            user_sort: Optional[UserSort] = None,
            page: int = 1,
            page_size: int = 100,
    ) -> list[Self]:
        """
        Query the list of profiles
        :param group: Group where profiles are located
        :param id_: Id of the profile
        :param name: Name of the profile
        :param serial_number: Serial number of the profile
        :param user_sort: User sorting. Can be sorted by the specified type, supporting
                          three fields serial_number, last_open_time, created_time, and two values asc and desc.
        :param page: Number of page in returning list. Default value - 1.
                     Numbers of elements in returning list is equal to the range(page, page + page_size)
        :param page_size: Maximum length of returning list. Default value - 100
        :return: List of profiles
        """
        http_client = cls._client
        args, handler = cls._query(
            group,
            id_,
            name,
            serial_number,
            user_sort,
            page,
            page_size
        )

        with http_client() as client:
            response = client.get(**args).json()['data']

        return handler(response)

    @classmethod
    def delete_cache(cls) -> None:
        """
        Deletes cache of all profiles
        :return: None
        """
        http_client = cls._client
        args, _ = cls._delete_cache()

        with http_client() as client:
            client.post(**args)

    def _get_browser(
            self,
            ip_tab: bool = True,
            new_first_tab: bool = True,
            launch_args: Optional[list[str]] = None,
            headless: bool = False,
            disable_password_filling: bool = False,
            clear_cache_after_closing: bool = False,
            enable_password_saving: bool = False
    ) -> BrowserResponse:
        http_client = self._client

        args, handler = super()._get_browser(
            ip_tab,
            new_first_tab,
            launch_args,
            headless,
            disable_password_filling,
            clear_cache_after_closing,
            enable_password_saving
        )

        with http_client() as client:
            response = client.get(**args).json()['data']

        handler()
        return response

    def update(
            self,
            name: Optional[str] = None,
            domain_name: Optional[str] = None,
            open_urls: Optional[list[str]] = None,
            username: Optional[str] = None,
            password: Optional[str] = None,
            fakey: Optional[str] = None,
            cookies: Optional[Cookies] = None,
            ignore_cookie_error: bool = False,
            ip: Optional[str] = None,
            ip_country: Optional[str] = None,
            region: Optional[str] = None,
            city: Optional[str] = None,
            remark: Optional[str] = None,
            category: Optional[Category] = None,
            proxy_config: Optional[ProxyConfig] = None,
            fingerprint_config: Optional[FingerprintConfig] = None
    ) -> None:
        """
        Update the profile

        :param name: Name of the profile
        :param domain_name: Domain name, such as facebook.com, amazon.com... Will open when getting the browser.
        :param open_urls: Other urls when opening browser. If leaving it empty, will open the domain name url.
        :param username: If username duplication is allowed, leave here empty.
        :param remark: Description of the profile
        :param category: Extension category for the profile
        :param ip: Proxy IP used for an account to log in. Fill in when proxy software is lumauto or oxylabs.
        :param ip_country: Country or region your lumauto and oxylabs account belongs to.Without lumauto and oxylabs IP please enter country.
        :param region: State or province where account logged in.
        :param city: City where account logged in.
        :param fakey: 2FA-key. This applies to online 2FA code generator, which works similarly to authenticators.
        :param cookies: Cookies to be set when opening browser
        :param ignore_cookie_error: 0：When the cookie verification fails, the cookie format is incorrectly returned directly
                                    1：When the cookie verification fails, filter out the data in the wrong format and keep the cookie in the correct format
                                    Only supports netspace
        :param password: If password duplication is allowed, leave here empty.
        :param proxy_config: Dictionary containing proxy info
        :param fingerprint_config: Dictionary containing fingerprint info
        """
        http_client = self._client
        args, handler = self._update(
            name,
            domain_name,
            open_urls,
            username,
            password,
            fakey,
            cookies,
            ignore_cookie_error,
            ip,
            ip_country,
            region,
            city,
            remark,
            category,
            proxy_config,
            fingerprint_config
        )

        with http_client() as client:
            client.post(**args)

        handler()

    def move(self, group: Group) -> None:
        """
        Move profile from one group to another
        :param group: Group to which an account is to be moved,
        :return: None
        """
        http_client = self._client
        args, handler = self._move(group)

        with http_client() as client:
            client.post(**args)

        handler()

    def active(self) -> bool:
        """
        Return whether a browser is active
        :return: True if browser is active, False otherwise
        """
        args, handler = self._active()
        http_client = self._client

        with http_client() as client:
            response = client.get(**args).json()['data']

        return handler(response)

    def delete(self) -> None:
        """
        Delete profile
        :return: None
        """
        http_client = self._client
        args, _ = self._delete()

        with http_client() as client:
            client.post(**args)

    def _quit(self) -> None:
        http_client = self._client
        args, _ = super()._quit()

        with http_client() as client:
            client.get(**args)

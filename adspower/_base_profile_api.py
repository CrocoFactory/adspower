from datetime import datetime
from typing import Optional, Self, Any
from abc import ABC, abstractmethod
from adspower._api_entity import _APIEntity
from ._base_group import _BaseGroup as Group
from ._base_category import _BaseCategory as Category
from adspower.types import (ProxyConfig, Cookies, FingerprintConfig, RepeatConfigType, ProfileInfo,
                            UserSort, IpChecker, HandlingTuple)
from .exceptions import InvalidProxyConfig


class _BaseProfileAPI(_APIEntity, ABC):

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
        self.__id = id_

        self._serial_number = serial_number
        self._name = name
        self._group = group
        self._domain_name = domain_name
        self._username = username
        self._remark = remark
        self._created_time = created_time
        self._ip = ip
        self._ip_country = ip_country
        self._password = password
        self._ip_checker = ip_checker
        self._category = category
        self._fakey = fakey
        self._last_open_time = last_open_time

        self._browser = None

    @staticmethod
    @abstractmethod
    def _get_init_args(response: dict[str, Any]) -> dict[str, Any]:
        pass

    @classmethod
    @abstractmethod
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
        pass

    @classmethod
    def _create(
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
    ) -> HandlingTuple:
        path = '/api/v1/user/create'

        if not proxy_config:
            proxy_config = {'proxy_soft': 'no_proxy'}
        else:
            proxy_config = cls.__parse_proxy_config(proxy_config)

        data = {
            'group_id': group.id,
            'name': name,
            'domain_name': domain_name,
            'open_urls': open_urls,
            'username': username,
            'repeat_config': repeat_config,
            'password': password,
            'fakey': fakey,
            'cookie': cookies,
            'ignore_cookie_error': ignore_cookie_error,
            'ip': ip,
            'country': ip_country,
            'region': region,
            'city': city,
            'remark': remark,
            'ip_checker': ip_checker,
            'sys_app_cate_id': category.id if category else 0,
            'user_proxy_config': proxy_config,
            'fingerprint_config': fingerprint_config
        }

        args = {
            'url': path,
            'json': data,
            'error_msg': 'The profile creation is failed'
        }

        def handler(response: dict[str, Any]) -> list[Self]:
            return cls.query(group=group, id_=response['id'])

        return args, handler

    @classmethod
    @abstractmethod
    def query(
            cls,
            group: Optional[Group] = None,
            id_: Optional[str] = None,
            serial_number: Optional[int] = None,
            user_sort: Optional[UserSort] = None,
            page: int = 1,
            page_size: int = 100,
    ) -> list[Self]:
        pass

    @classmethod
    def _query(
            cls,
            group: Optional[Group] = None,
            id_: Optional[str] = None,
            name: Optional[str] = None,
            serial_number: Optional[int] = None,
            user_sort: Optional[UserSort] = None,
            page: int = 1,
            page_size: int = 100,
    ) -> HandlingTuple:
        path = '/api/v1/user/list'

        data = {
            'group_id': group.id if group else None,
            'user_id': id_,
            'serial_number': serial_number,
            'user_sort': user_sort,
            'page_size': page_size,
            'page': page
        }

        args = {
            'url': path,
            'params': data,
            'error_msg': 'Querying the profile is failed'
        }

        def handler(response: dict[str, Any]) -> list[Self]:
            profiles = []
            for profile_info in response['list']:
                profile_info = cls._get_init_args(profile_info)

                if name is None or profile_info['name'] == name:
                    profiles.append(cls(**profile_info))
            return profiles

        return args, handler

    @classmethod
    @abstractmethod
    def delete_cache(
            cls
    ) -> None:
        pass

    @classmethod
    def _delete_cache(
            cls
    ) -> HandlingTuple:
        path = '/api/v1/user/delete-cache'
        args = {
            'url': path,
            'error_msg': 'Deleting cache is failed'
        }

        def handler() -> None:
            pass

        return args, handler

    @property
    def id(self) -> str:
        """
        :return: Id of the profile
        """
        return self.__id

    @property
    def serial_number(self) -> int:
        """
        :return: Serial number of the profile
        """
        return self._serial_number

    @property
    def name(self) -> str | None:
        """
        :return: Name of the profile
        """
        return self._name

    @property
    def group(self) -> Group:
        """
        :return: Group where the profile is located
        """
        return self._group

    @property
    def domain_name(self) -> str | None:
        """
        :return: Domain name, such as facebook.com, amazon.com... Will open when getting the browser
        """
        return self._domain_name

    @property
    def username(self) -> str | None:
        """
        :return: Username for the domain name (e.g. facebook.com, amazon)
        """
        return self._username

    @property
    def remark(self) -> str | None:
        """
        :return: Description of the profile
        """
        return self._remark

    @property
    def created_time(self) -> datetime:
        """
        :return: Creation time of the profile
        """
        return self._created_time

    @property
    def ip(self) -> str | None:
        """
        :return: Proxy IP used for an account to log in. None when proxy software is not lumauto or oxylabs.
        """
        return self._ip

    @property
    def ip_country(self) -> str | None:
        """
        :return: Country of the proxy ip
        """
        return self._ip_country

    @property
    def ip_checker(self) -> IpChecker:
        """
        :return: IP checker for the profile. It can be 'ip2location' or 'ipapi'
        """
        return self._ip_checker

    @property
    def password(self) -> str | None:
        """
        :return: Password for the domain name (e.g. facebook.com, amazon)
        """
        return self._password

    @property
    def last_open_time(self) -> datetime | None:
        """
        :return: Last open time of the profile
        """
        return self._last_open_time

    @property
    def category(self) -> Category | None:
        """
        :return: Extension category of the profile
        """
        return self._category

    @property
    def fakey(self) -> str | None:
        """
        :return: 2FA-key for the domain name (e.g. facebook.com, amazon).
                 This applies to online 2FA code generator, which works similarly to authenticators.
        """
        return self._fakey

    def to_dict(self) -> ProfileInfo:
        """
        Converts the Profile/ProfileAPI instance to the dictionary containing info about profile
        :return: Dictionary containing info about profile
        """
        return ProfileInfo(
            profile_id=self.id,
            serial_number=self.serial_number,
            name=self.name,
            group_id=self.group.id,
            group_name=self.group.name,
            domain_name=self.domain_name,
            username=self.username,
            remark=self.remark,
            category_id=category.id if (category := self.category) else None,
            created_time=int(self.created_time.timestamp()),
            ip=self.ip,
            ip_country=self.ip_country,
            ip_checker=self.ip_checker,
            fakey=self.fakey,
            password=self.password
        )

    @staticmethod
    def __parse_proxy_config(proxy_config: ProxyConfig | None) -> dict[str, Any] | None:
        if proxy_config:
            try:
                parsed_proxy = {
                    'proxy_soft': proxy_config['soft'],
                    'proxy_type': proxy_config['type'],
                    'proxy_host': proxy_config['host'],
                    'proxy_port': str(proxy_config['port']),
                    'proxy_user': proxy_config['user'],
                    'proxy_password': proxy_config['password']
                }
                return parsed_proxy
            except (KeyError, TypeError):
                raise InvalidProxyConfig(proxy_config)
        else:
            return None

    @abstractmethod
    def _get_browser(
            self,
            ip_tab: bool = True,
            new_first_tab: bool = True,
            launch_args: Optional[list[str]] = None,
            headless: bool = False,
            disable_password_filling: bool = False,
            clear_cache_after_closing: bool = False,
            enable_password_saving: bool = False
    ) -> HandlingTuple:
        profile_id = self.id
        path = '/api/v1/browser/start'

        params = {
            'user_id': profile_id,
            'ip_tab': int(ip_tab),
            'new_first_tab': int(new_first_tab),
            'launch_args': launch_args,
            'headless': int(headless),
            'disable_password_filling': int(disable_password_filling),
            'clear_cache_after_closing': int(clear_cache_after_closing),
            'enable_password_saving': int(enable_password_saving)
        }

        args = {
            'url': path,
            'params': params,
            'error_msg': 'Getting browser is failed'
        }

        def handler() -> None:
            self._profile_id = profile_id
            self.__last_open_time = datetime.now()

        return args, handler

    def _update(
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
    ) -> HandlingTuple:
        path = '/api/v1/user/update'
        proxy_config = self.__parse_proxy_config(proxy_config)

        data = {
            'user_id': self.id,
            'name': name,
            'domain_name': domain_name,
            'open_urls': open_urls,
            'username': username,
            'password': password,
            'fakey': fakey,
            'cookie': cookies,
            'ignore_cookie_error': int(ignore_cookie_error),
            'ip': ip,
            'country': ip_country,
            'region': region,
            'sys_app_cate_id': category.id if category else None,
            'remark': remark,
            'city': city,
            'user_proxy_config': proxy_config,
            'fingerprint_config': fingerprint_config
        }

        args = {
            'url': path,
            'json': data,
            'error_msg': 'Updating profile is failed'
        }

        def handler() -> None:
            data.pop('city')
            data.pop('user_id')
            data.pop('user_proxy_config')
            data.pop('fingerprint_config')
            data.pop('ignore_cookie_error')

            data['ip_country'] = data.pop('country')
            data['category'] = Category.query(id_) if (id_ := data.pop('sys_app_cate_id')) else self.category

            for key, value in data.items():
                if value is not None:
                    self.__setattr__(f'_{key}', value)

        return args, handler

    @abstractmethod
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
        pass

    def _move(self, group: Group) -> HandlingTuple:
        path = '/api/v1/user/regroup'

        data = {
            'user_ids': [self.id],
            'group_id': group.id
        }

        args = {
            'url': path,
            'json': data,
            'error_msg': f'Moving profile is failed. Profile ID: {self.id}. Group ID: {group.id}'
        }

        def handler() -> None:
            self._group = group

        return args, handler

    @abstractmethod
    def move(self, group: Group) -> None:
        pass

    def _active(self) -> HandlingTuple:
        path = '/api/v1/browser/active'

        data = {
            'user_id': self.id
        }

        args = {
            'url': path,
            'json': data,
            'error_msg': 'Checking browser for activity is failed'
        }

        def handler(response: dict[str, Any]) -> bool:
            active = response['status'] == 'Active'
            return active

        return args, handler

    @abstractmethod
    def active(self) -> bool:
        pass

    def _delete(self) -> HandlingTuple:
        path = '/api/v1/user/delete'

        data = {'user_ids': [self.id]}

        args = {
            'url': path,
            'json': data,
            'error_msg': 'The profile deletion is failed'
        }

        def handler() -> None: pass

        return args, handler

    @abstractmethod
    def delete(self) -> None:
        pass

    @abstractmethod
    def _quit(self) -> HandlingTuple:
        path = '/api/v1/browser/stop'
        profile_id = self.id

        params = {'user_id': profile_id}
        args = {
            'url': path,
            'params': params,
            'error_msg': 'Quitting profile is failed. Profile can be already closed'
        }

        def handler() -> None: pass

        return args, handler

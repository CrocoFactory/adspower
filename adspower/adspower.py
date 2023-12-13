import time
import requests
from requests.exceptions import ConnectionError as RequestConnectionError, InvalidURL
from urllib3.exceptions import MaxRetryError, NewConnectionError
from .types import *
from .exceptions import *
from functools import wraps
from selenium import webdriver
from typing import Self, Optional, Any, Type, Iterable
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from .utils import is_typed_dict

_request_accessibility = 0

__all__ = ['AdsPower']


class AdsPower:
    """Controls AdsPower overall and the instance of corresponding profile"""

    def __init__(self, profile_id: Optional[str] = None, port: int = 50325):
        """
        :param profile_id: ID of existed profile in AdsPower
        :param port: The port of AdsPower's API
        """
        self._driver = None
        self.__profile_id = profile_id
        self.__api_url = self._validate_api_url('http://local.adspower.net', port)

    def __enter__(self):
        driver = self.get_driver()
        driver.maximize_window()
        for _ in range(3):
            time.sleep(1.5)
            self.close_tabs()
        return driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()

    @property
    def driver(self) -> WebDriver | None:
        """
        :return: The driver instance or None if get_driver() was not called
        """
        return self._driver

    @property
    def api_url(self) -> str:
        """
        :return: The URL of API of an anti-detect browser
        """
        return self.__api_url

    @property
    def profile_id(self) -> str:
        """
        Returns ID of existed profile in anti-detect browser
        :return: The ID of existed profile in anti-detect
        """
        return self.__profile_id

    @profile_id.setter
    def profile_id(self, value: str):
        self.__profile_id = value

    @staticmethod
    def _wait_for_delay(func):
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_time = time.time()
            global _request_accessibility

            if _request_accessibility < current_time:
                result = func(*args, **kwargs)
            else:
                time.sleep(_request_accessibility - current_time)
                result = func(*args, **kwargs)

            _request_accessibility = time.time() + 0.7
            return result

        return wrapper

    @staticmethod
    def _validate_response(exception: Type[Exception], request: dict[str, Any], response: dict[str, Any]):
        if response['code'] != 0:
            if response['msg'] == 'Too many request per second, please check':
                raise ExceededQPS
            else:
                raise exception(request, response)

    @staticmethod
    def _validate_api_url(api_url: str, port: int) -> str:
        url = f'{api_url}:{port}'
        try:
            status_url = url + '/status'
            requests.get(url=status_url)
        except (MaxRetryError, RequestConnectionError, NewConnectionError, ConnectionRefusedError, InvalidURL):
            raise UnavailableAPI(port)
        else:
            return url

    @_wait_for_delay
    def get_driver(self, profile_id: Optional[str] = None) -> WebDriver:
        """
        Returns a driver associated with profile_id

        :raise ProfileNotFound: Raised when profile getting or deleting is failed
        :raise NoProfileFound: Raised when profile ID is not specified
        :return: A WebDriver instance associated with profile_id
        """
        profile_id = profile_id or self.profile_id
        if not profile_id:
            raise NoProfileIdFound

        self.profile_id = profile_id
        url = self.api_url + '/api/v1/browser/start'

        params = {
            'ip_tab': 0,
            'user_id': profile_id
        }

        response = requests.get(url=url, params=params).json()
        self._validate_response(ProfileNotFound, params, response)

        debugger_address = response['data']['ws']['selenium']
        chrome_driver = response['data']['webdriver']

        options = Options()
        options.add_experimental_option('debuggerAddress', debugger_address)
        options.page_load_strategy = 'none'
        options.add_argument('--headless=new')

        service = Service(executable_path=chrome_driver)
        self._driver = webdriver.Chrome(service=service, options=options)
        return self.driver

    @classmethod
    @_wait_for_delay
    def create_profile(
            cls,
            data: Optional[CreateProfileParams] = None,
            port: int = 50325,
            *,
            group_id: Optional[int] = None,
            name: Optional[str] = None,
            user_proxy_config: Optional[UserProxyConfig] = None,
            fingerprint_config: Optional[FingerprintConfig] = None
    ) -> Self:
        """
        Returns an instance of class referring to a new profile

        :param data: Keyword arguments as dictionary to create profile
        :param port: The port of API
        :param name: The name of the account, no more than 100 characters
        :param group_id: The group ID corresponding to the group in which an account is to be created,
        :param user_proxy_config: Dictionary arguments to update a proxy
        :param fingerprint_config: Dictionary arguments to update a fingerprint

        :raise ProfileCreationError: Raised when profile creation is failed
        :return: An AdsPower instance with the specified profile ID

        Request parameters
        ----------
            {
                'name':
                      The name of the account, no more than 100 characters,
                'group_id':
                          The group ID corresponding to the group in which an account is to be created,
                'user_proxy_config': {
                    'proxy_soft':
                                The proxy software. Currently, supports:
                                luminati, lumauto, oxylabsatuto, 922S5，ipideaauto，ipfoxyauto，ssh, other, no_proxy,
                                Default value - no_proxy,
                    'proxy_type':
                                The proxy type. Currently, supports:
                                http, https, socks5;
                                For no_proxy, you may pass the parameter or not,
                    'proxy_host':
                                Address of the proxy server, users can enter domain name or IP;
                                For no_proxy, you may pass the parameter or not,
                    'proxy_port':
                                Port of the proxy server;
                                For no_proxy, you may pass the parameter or not,
                    'proxy_user':
                                The username of the proxy,
                    'proxy_password':
                                    The password of the proxy
                },

                'fingerprint_config': {
                    'language_switch':
                                     Configure languages based on IP country. Default value - 0
                                     0: Off;
                                     1: On.
                    'ua':
                        String containing user agent.
                        When customizing please make sure that ua format and content meet
                        the requirement.
                }
            }
        """
        kwargs = locals()
        del kwargs['port']
        del kwargs['data']
        del kwargs['cls']

        api_url = cls._validate_api_url('http://local.adspower.net', port)

        url = api_url + '/api/v1/user/create'

        data = data or kwargs
        if not data.get('group_id'):
            raise NoGroupIdFound

        if not data.get('user_proxy_config'):
            data['user_proxy_config'] = {'proxy_soft': 'no_proxy'}

        response = requests.post(url=url, json=data).json()
        cls._validate_response(ProfileCreationError, data, response)

        return cls(response['data']['id'], port)

    @classmethod
    @_wait_for_delay
    def delete_profiles(cls, profile_ids: str | Iterable[str], port: int = 50325) -> None:
        """
        Deletes profiles associated with specified profile_ids in AdsPower
        :param profile_ids: Iterable containing profile_ids or one profile ID
        :param port: The port of AdsPower's API

        :raise ProfileNotFound: Raised when a profile does not exist
        :return: None
        """
        if not profile_ids:
            raise NoProfileIdFound

        api_url = cls._validate_api_url('http://local.adspower.net', port)
        url = api_url + '/api/v1/user/delete'

        if isinstance(profile_ids, str):
            profile_ids = [profile_ids]
        else:
            profile_ids_ = []
            for profile_id in profile_ids:
                profile_ids_.append(profile_id)
            profile_ids = profile_ids_

        data = {'user_ids': profile_ids}

        response = requests.post(url=url, json=data).json()
        cls._validate_response(ProfileNotFound, data, response)

    @classmethod
    @_wait_for_delay
    def query_group(
            cls,
            params: Optional[QueryGroupParams] = None,
            port: int = 50325,
            *,
            group_name: Optional[str] = None,
            profile_id: Optional[str] = None,
            page_size: Optional[int] = 100
    ) -> GroupResponse:
        """
        Returns dictionaries containing information about the groups by specified parameters. If there are no
        params, excluding page_size, it returns a list of dictionaries, containing information about all groups

        :param params: Keyword arguments as dictionary to query groups
        :param port: The port of AdsPower's API
        :param group_name: The group name corresponding to the group
        :param profile_id: ID of existed profile in AdsPower
        :param page_size: The maximum length of returning list. Default value - 100

        :raise GroupQueryError: Raised when group query is failed
        :return: List of dictionaries containing information about corresponding groups

        Request parameters
        ----------
            {
                'group_name':
                            The group name corresponding to the group,
                'profile_id':
                         ID of existed profile in AdsPower,
                'page_size':
                           The maximum length of returning list. Default value - 100
            }
        """
        kwargs = locals()
        del kwargs['cls']
        del kwargs['params']
        del kwargs['port']

        api_url = cls._validate_api_url('http://local.adspower.net', port)
        url = api_url + '/api/v1/group/list'

        params = params or kwargs
        if not params.get('page_size'):
            params['page_size'] = 100

        if len(params) == 1:
            response = requests.get(url=url, params=params).json()
            cls._validate_response(GroupQueryError, params, response)
            return response['data']['list']
        else:
            params['user_id'] = params.pop('profile_id')
            response = requests.get(url=url, params=params).json()
            cls._validate_response(GroupQueryError, params, response)
            return response['data']['list'][0]

    @classmethod
    @_wait_for_delay
    def query_profiles(
            cls,
            params: Optional[QueryProfilesParams] = None,
            port: int = 50325,
            *,
            group_id: Optional[int] = None,
            page_size: Optional[int] = 100
    ) -> ProfileResponse:
        """
        Returns a list consisting of dictionaries containing information about the profiles by specified parameters

        :param params: Keyword arguments as dictionary to query profiles
        :param port: The port of AdsPower's API
        :param group_id: The group ID corresponding to the group in which an account is to be created,
        :param page_size: The maximum length of returning list. Default value - 100

        :raise ProfileQueryError: Raised when profile query is failed
        :return: list[dict[str, str]]: List of dictionaries containing information about corresponding profiles

        Request parameters
        ----------
            {
                'group_id':
                           The group ID corresponding to the group in which an account exists,
                'page_size':
                            The maximum length of returning list. Default value - 100
            }
        """
        kwargs = locals()
        del kwargs['cls']
        del kwargs['params']
        del kwargs['port']

        api_url = cls._validate_api_url('http://local.adspower.net', port)
        url = api_url + '/api/v1/user/list'

        params = params or kwargs
        if not params.get('page_size'):
            params['page_size'] = 100

        response = requests.get(url=url, params=params).json()

        cls._validate_response(ProfileQueryError, params, response)

        return response['data']['list']

    @_wait_for_delay
    def update_proxy(
            self,
            data: Optional[UpdatingProxyParams] = None,
            *,
            profile_id: Optional[str] = None,
            proxy_soft: Optional[str] = None,
            proxy_type: Optional[str] = None,
            proxy_host: Optional[str] = None,
            proxy_user: Optional[str] = None,
            proxy_password: Optional[str] = None
    ) -> None:
        """
        Updates proxy in current profile

        :param data: Keyword arguments as dictionary to update proxy
        :param profile_id: ID of existed profile in AdsPower
        :param proxy_soft: The proxy software. Currently, supports:
                            luminati, lumauto, oxylabsatuto, 922S5，ipideaauto，ipfoxyauto，ssh, other, noproxy,
                            By default you should to set 'other'.
        :param proxy_type: The proxy type. Currently, supports:
                            http, https, socks5;
                            For no_proxy, you may pass the parameter or not
        :param proxy_host: Address of the proxy server, users can enter domain name or IP;
                            For no_proxy, you may pass the parameter or not,
        :param proxy_user: The username of the proxy,
        :param proxy_password: The password of the proxy

        :raise InvalidProxyConfig: Raised when proxy config is invalid
        :raise ProxyUpdateError: Raised when proxy update is failed
        :return: None

        Request parameters
        ----------
            {
                'profile_id':
                            ID of existed profile in AdsPower
                'proxy_soft':
                            The proxy software. Currently, supports:
                            luminati, lumauto, oxylabsatuto, 922S5，ipideaauto，ipfoxyauto，ssh, other, noproxy,
                            By default you should to set 'other',
                'proxy_type':
                            The proxy type. Currently, supports:
                            http, https, socks5;
                            For no_proxy, you may pass the parameter or not,
                'proxy_host':
                            Address of the proxy server, users can enter domain name or IP;
                            For no_proxy, you may pass the parameter or not,
                'proxy_port':
                            Port of the proxy server;
                            For no_proxy, you may pass the parameter or not,
                'proxy_user':
                            The username of the proxy,
                'proxy_password':
                                The password of the proxy
            }
        """
        kwargs = locals()
        del kwargs['data']
        del kwargs['self']

        url = self.api_url + '/api/v1/user/update'

        data = data or kwargs
        if not data.get('profile_id'):
            data['profile_id'] = self.profile_id

        if not is_typed_dict(data, UpdatingProxyParams):
            raise InvalidProxyConfig(data)

        profile_id = data.pop('profile_id')
        data_to_send = {
            'user_id': profile_id,
            'user_proxy_config': data
        }

        response = requests.post(url=url, json=data_to_send).json()
        self._validate_response(ProxyUpdateError, data_to_send, response)

    @_wait_for_delay
    def update_user_agent(self, user_agent: str, profile_id: Optional[str] = None) -> None:
        """
        Updates user agent in current profile

        :param profile_id: ID of existed profile in AdsPower
        :param user_agent: String containing user agent.
                           When customizing please make sure that ua format and content meet
                           the requirement.

        :raise NoUserAgentFound: Raised when user agent is not specified
        :raise UserAgentUpdateError: Raised when user agent update is failed
        :return: None
        """
        url = self.api_url + '/api/v1/user/update'
        if not user_agent:
            raise NoUserAgentFound

        user_agent = user_agent
        profile_id = self.profile_id or profile_id
        data = {
            'user_id': profile_id,
            'fingerprint_config': {'ua': user_agent}
        }
        response = requests.post(url=url, json=data).json()

        self._validate_response(UserAgentUpdateError, data, response)

    def close_tabs(self) -> None:
        """
        Closes all tabs in anti-detect browser

        :return: None
        """
        driver = self.driver
        original_window_handle = driver.current_window_handle
        windows = driver.window_handles
        for window in windows:
            if original_window_handle != window:
                driver.switch_to.window(window)
                driver.close()
        driver.switch_to.window(original_window_handle)

    @_wait_for_delay
    def quit(self) -> None:
        """
        Closes current profile

        :raise QuittingProfileError: Quitting profile is failed. Profile can be already closed
        :return: None
        """
        self.driver.quit()
        profile_id = self.profile_id
        url = self.api_url + '/api/v1/browser/stop'
        params = {'user_id': profile_id}
        response = requests.get(url=url, params=params).json()
        self._validate_response(QuittingProfileError, params, response)

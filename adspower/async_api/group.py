from typing import ClassVar, Optional
from typing import Self
from adspower._base_group import _BaseGroup
from .http_client import HTTPClient


class Group(_BaseGroup):
    _client: ClassVar[type[HTTPClient]] = HTTPClient

    def __init__(self, id_: int, name: str, remark: str | None) -> None:
        """
        The class interacting with groups. You can use groups to combine profiles
        :param id_: Id of the group
        :param name: Name of the group
        :param remark: Description of the group
        """
        super().__init__(id_, name, remark)

    @classmethod
    async def create(cls, name: str, remark: Optional[str] = None) -> Self:
        """
        Create a new group

        :param name: Name of the group
        :param remark: Description of the group
        :return: Instance of the Group
        """
        http_client = cls._client
        args, handler = cls._create(name, remark)
        async with http_client() as client:
            response = (await client.post(**args)).json()['data']

        return handler(response)

    @classmethod
    async def query(
            cls,
            name: Optional[str] = None,
            profile_id: Optional[str] = None,
            page_size: Optional[int] = 100,
    ) -> list[Self]:
        """
        Query the list of groups.

        :param name: Name of the group
        :param profile_id: ID of existing profile in AdsPower
        :param page_size: Maximum length of returning list. Default value - 100

        :return: List of groups
        """
        http_client = cls._client
        args, handler = cls._query(name, profile_id, page_size)

        async with http_client() as client:
            response = (await client.get(**args)).json()['data']

        return handler(response)

    async def update(self, name: Optional[str] = None, remark: Optional[str] = None) -> None:
        """
        Updates a group name or description for the existing group

        :param name: Name of the group
        :param remark: Description of the group
        :return: None
        """
        http_client = self._client
        args, handler = self._update(name, remark)

        async with http_client() as client:
            (await client.post(**args))

        handler()

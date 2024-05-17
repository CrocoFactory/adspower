from typing import Self, Optional, ClassVar
from adspower._base_category import _BaseCategory
from .http_client import HTTPClient


class Category(_BaseCategory):
    _client: ClassVar[type[HTTPClient]] = HTTPClient

    def __init__(self, id_: int, name: str | None, remark: str | None):
        """
        The class interacting with extension categories. You can use an extension category to specify extensions for
        profiles
        :param id_: Id of the extension category
        :param name: Name of the extension category
        :param remark: Description of the extension category
        """
        super().__init__(id_, name, remark)

    @classmethod
    async def query(cls, id_: Optional[int] = None, name: Optional[str] = None, page: int = 1, page_size: int = 100) -> list[Self]:
        """
        Query the list of extension categories.
        :param id_: Id of the extension category
        :param name: Name of the extension category
        :param page: Number of page in returning list. Default value - 1.
                     Numbers of elements in returning list is equal to the range(page, page + page_size)
        :param page_size: Maximum length of returning list. Default value - 100

        :return: List of categories
        """
        http_client = cls._client
        args, handler = cls._query(id_, name, page, page_size)

        async with http_client() as client:
            response = (await client.get(**args)).json()['data']

        return handler(response)

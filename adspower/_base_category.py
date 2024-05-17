from abc import ABC, abstractmethod
from typing import Self, Optional, Any
from adspower._api_entity import _APIEntity
from adspower.types import CategoryInfo, HandlingTuple


class _BaseCategory(_APIEntity, ABC):

    def __init__(self, id_: int, name: str | None, remark: str | None):
        self.__remark = remark
        self.__name = name
        self.__id = id_

    @property
    def id(self) -> int:
        """
        :return: Id of the category
        """
        return self.__id

    @property
    def name(self) -> str | None:
        """
        :return: Name of the category
        """
        return self.__name

    @property
    def remark(self) -> str | None:
        """
        :return: Description of the category
        """
        return self.__remark

    def to_dict(self) -> CategoryInfo:
        """
        Converts the Category instance to the dictionary containing info about extension category
        :return: Dictionary containing info about extension category
        """
        return CategoryInfo(
            id=self.id,
            name=self.name,
            remark=self.remark
        )

    @classmethod
    @abstractmethod
    def query(cls, id_: Optional[int] = None, page: int = 1, page_size: int = 100) -> list[Self]:
        pass

    @classmethod
    def _query(cls, id_: Optional[int] = None, name: Optional[str] = None, page: int = 1, page_size: int = 100) -> HandlingTuple:
        path = '/api/v1/application/list'
        data = {
            'page': page,
            'page_size': page_size,
        }

        args = {
            'url': path,
            'params': data,
            'error_msg': 'Querying categories is failed'
        }

        def handler(response: dict[str, Any]) -> list[Self]:
            categories = []
            for category_info in response['list']:
                if (not id_ or category_info['id'] == id_) and (not name or category_info['name'] == name):
                    categories.append(cls(int(category_info['id']), category_info['name'], category_info['remark']))
                    if id_:
                        break

            return categories

        return args, handler

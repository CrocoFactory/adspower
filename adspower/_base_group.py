from abc import ABC, abstractmethod
from typing import Optional, Any
from typing import Self
from adspower.types import GroupInfo
from adspower._api_entity import _APIEntity
from adspower.types import HandlingTuple
from adspower.utils import _convert_json


class _BaseGroup(_APIEntity, ABC):
    def __init__(self, id_: int, name: str, remark: str | None) -> None:
        self.__id = id_
        self.__name = name
        self.__remark = remark

    def to_dict(self) -> GroupInfo:
        """
        Converts the Group instance to the dictionary containing info about group
        :return: Dictionary containing info about group
        """
        return GroupInfo(
            group_id=self.id,
            group_name=self.name,
            remark=self.remark
        )

    @classmethod
    @abstractmethod
    def create(cls, group_name: str, remark: Optional[str] = None) -> Self:
        pass

    @classmethod
    def _create(cls, group_name: str, remark: Optional[str] = None) -> HandlingTuple:
        path = '/api/v1/group/create'

        data = {'group_name': group_name, 'remark': remark}

        args = {
            'url': path,
            'json': data,
            'error_msg': 'Creating group is failed'
        }

        def handler(response: dict[str, Any]) -> Self:
            response = _convert_json(response)
            return cls(id_=response['group_id'], name=response['group_name'], remark=response['remark'])

        return args, handler

    @classmethod
    @abstractmethod
    def query(
            cls,
            name: Optional[str] = None,
            profile_id: Optional[str] = None,
            page_size: Optional[int] = 100,
    ) -> list[Self]:
        pass

    @classmethod
    def _query(
            cls,
            name: Optional[str] = None,
            profile_id: Optional[str] = None,
            page_size: Optional[int] = 100,
    ) -> HandlingTuple:
        path = '/api/v1/group/list'

        params = {
            'group_name': name,
            'profile_id': profile_id,
            'page_size': page_size,
        }

        args = {
            'url': path,
            'params': params,
            'error_msg': 'The group query is failed'
        }

        def handler(response: dict[str, Any]) -> list[Self]:
            groups = []
            for info in response['list']:
                info = _convert_json(info)
                groups.append(cls(id_=int(info['group_id']), name=info['group_name'], remark=info['remark']))

            return groups

        return args, handler

    @property
    def id(self) -> int:
        """
        :return: Id of the group
        """
        return self.__id

    @property
    def name(self) -> str:
        """
        :return: Name of the group
        """
        return self.__name

    @property
    def remark(self) -> str | None:
        """
        :return: Description of the group
        """
        return self.__remark

    @abstractmethod
    def update(self, name: Optional[str] = None, remark: Optional[str] = None) -> None:
        pass

    def _update(self, name: Optional[str] = None, remark: Optional[str] = None) -> HandlingTuple:
        path = '/api/v1/group/update'

        if not name:
            name = self.name

        data = {"group_id": self.id, "group_name": name, "remark": remark}
        args = {
            'url': path,
            'json': data,
            'error_msg': 'Updating group is failed'
        }

        def handler() -> None:
            self.__name = name if name else self.__name
            self.__remark = remark if remark else self.__remark

        return args, handler

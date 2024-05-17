from abc import ABC, abstractmethod
from typing import Mapping, MutableMapping


class _APIEntity(ABC):
    @property
    @abstractmethod
    def id(self) -> int | str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def to_dict(self) -> Mapping | MutableMapping:
        pass

    def __str__(self):
        str_ = f'{self.__class__.__name__}(id={self.id}; name={self.name})'
        return str_

    def __eq__(self, other):
        return isinstance(other, _APIEntity) and self.to_dict() == other.to_dict()

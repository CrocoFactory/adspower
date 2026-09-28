from __future__ import annotations

from collections.abc import Mapping
from typing import TypeAlias, TypeVar

from .errors import AdsPowerProtocolError

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

T = TypeVar("T")


def require_json_value(value: object, *, field: str = "value") -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [require_json_value(item, field=field) for item in value]
    if isinstance(value, Mapping):
        result: JsonObject = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise AdsPowerProtocolError(f"{field} contains a non-string object key")
            result[key] = require_json_value(item, field=f"{field}.{key}")
        return result
    raise AdsPowerProtocolError(f"{field} is not valid JSON")


def require_object(value: object, *, field: str = "data") -> JsonObject:
    result = require_json_value(value, field=field)
    if not isinstance(result, dict):
        raise AdsPowerProtocolError(f"{field} must be an object")
    return result


def require_list(value: object, *, field: str = "data") -> list[JsonValue]:
    result = require_json_value(value, field=field)
    if not isinstance(result, list):
        raise AdsPowerProtocolError(f"{field} must be a list")
    return result


def require_string(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise AdsPowerProtocolError(f"{field} must be a string")
    return value


def optional_string(value: object, *, field: str) -> str | None:
    if value is None or value == "":
        return None
    return require_string(value, field=field)


def require_int(value: object, *, field: str) -> int:
    if isinstance(value, bool):
        raise AdsPowerProtocolError(f"{field} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass
    raise AdsPowerProtocolError(f"{field} must be an integer")


def optional_int(value: object, *, field: str) -> int | None:
    if value is None or value == "":
        return None
    return require_int(value, field=field)


def require_id_string(value: object, *, field: str) -> str:
    if isinstance(value, bool) or value in (None, ""):
        raise AdsPowerProtocolError(f"{field} must contain an id")
    if isinstance(value, (str, int)):
        return str(value)
    raise AdsPowerProtocolError(f"{field} must be a string or integer id")


def optional_id_string(value: object, *, field: str) -> str | None:
    if value is None or value == "":
        return None
    return require_id_string(value, field=field)


def collect_extra(data: Mapping[str, object], known: set[str]) -> JsonObject:
    return {key: require_json_value(value, field=key) for key, value in data.items() if key not in known}


def first_present(data: Mapping[str, object], *keys: str) -> object | None:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None

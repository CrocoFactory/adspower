from typing import TypeVar

_KT = TypeVar('_KT')
_VT = TypeVar('_VT')


def _convert_json(data: dict[_KT, _VT]) -> dict[_KT, _VT]:
    """
    Convert string representations of numbers to actual numeric types within a dictionary and convert
    empty strings to None.

    :param data: A dictionary containing various key-value pairs.
    :return: A dictionary with string representations of numbers converted to their actual numeric types.
    """
    for key, value in data.items():
        if isinstance(value, str) and value.isdigit():
            data[key] = int(value)
        elif isinstance(value, str) and _is_float(value):
            data[key] = float(value)
        elif isinstance(value, str) and not len(value):
            data[key] = None
    return data


def _is_float(__str: str) -> bool:
    """
    Check if a string represents a floating-point number.

    :param __str: A string to check.
    :return: True if the string represents a floating-point number, False otherwise.
    """
    try:
        float(__str)
        return True
    except ValueError:
        return False

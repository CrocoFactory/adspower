import ctypes
import platform
import subprocess
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


def _get_screen_size() -> tuple[int, int]:
    os_name = platform.system()
    if os_name == "Windows":
        h = ctypes.windll.user32.GetDC(0)
        width = ctypes.windll.gdi32.GetDeviceCaps(h, 118)
        height = ctypes.windll.gdi32.GetDeviceCaps(h, 117)
        ctypes.windll.user32.ReleaseDC(0, h)
        return width, height

    elif os_name == "Darwin":
        output = subprocess.run(['system_profiler', 'SPDisplaysDataType'], capture_output=True, text=True).stdout
        for line in output.split('\n'):
            if 'Resolution' in line:
                parts = line.split()
                width = int(parts[1])
                height = int(parts[3])
                return width, height

    elif os_name == "Linux":
        output = subprocess.run(['xrandr'], capture_output=True, text=True).stdout
        for line in output.split('\n'):
            if '*' in line:
                resolution = line.split()[0]
                width, height = map(int, resolution.split('x'))
                return width, height

    else:
        raise NotImplementedError(f"OS {os_name} not supported")

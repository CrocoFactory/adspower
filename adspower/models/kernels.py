from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from .._json import JsonValue, collect_extra, first_present, optional_string, require_object
from ..errors import AdsPowerProtocolError


@dataclass(frozen=True, slots=True)
class KernelInfo:
    kernel_type: str
    version: str
    status: str | None = None
    extra: Mapping[str, JsonValue] = field(default_factory=dict)


def parse_kernel(value: object) -> KernelInfo:
    data = require_object(value, field="kernel")
    kernel_type = optional_string(first_present(data, "kernel_type", "type"), field="kernel_type")
    version = optional_string(first_present(data, "kernel_version", "version"), field="kernel_version")
    if kernel_type is None or version is None:
        raise AdsPowerProtocolError("kernel response requires kernel type and version")
    return KernelInfo(
        kernel_type,
        version,
        optional_string(data.get("status"), field="status"),
        collect_extra(data, {"kernel_type", "type", "kernel_version", "version", "status"}),
    )

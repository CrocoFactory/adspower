from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping

from .._json import JsonValue, collect_extra, first_present, optional_string, require_id_string, require_object


@dataclass(frozen=True, slots=True)
class BrowserTag:
    tag_id: str
    name: str | None = None
    color: str | None = None
    extra: Mapping[str, JsonValue] = field(default_factory=dict)


def parse_browser_tag(value: object) -> BrowserTag:
    data = require_object(value, field="browser tag")
    return BrowserTag(
        require_id_string(first_present(data, "id", "tag_id"), field="tag_id"),
        optional_string(data.get("name"), field="name"),
        optional_string(data.get("color"), field="color"),
        collect_extra(data, {"id", "tag_id", "name", "color"}),
    )

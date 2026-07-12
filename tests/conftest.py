"""Test stubs for the minimal Home Assistant surface used by the integration."""

from __future__ import annotations

from dataclasses import dataclass
import sys
from types import ModuleType
from typing import Any


class _Schema:
    def __init__(self, schema: Any) -> None:
        self.schema = schema

    def __call__(self, value: Any) -> Any:
        return value


class _Required:
    def __init__(self, key: str) -> None:
        self.key = key

    def __hash__(self) -> int:
        return hash(self.key)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Required) and self.key == other.key


class _Length:
    def __init__(self, *, min: int | None = None) -> None:
        self.min = min

    def __call__(self, value: Any) -> Any:
        return value


def _all(*validators: Any) -> Any:
    return validators[-1]


voluptuous = ModuleType("voluptuous")
voluptuous.Schema = _Schema
voluptuous.Required = _Required
voluptuous.Length = _Length
voluptuous.All = _all
sys.modules.setdefault("voluptuous", voluptuous)

aiohttp = ModuleType("aiohttp")


class ClientError(Exception):
    """Stub aiohttp client error."""


aiohttp.ClientError = ClientError
sys.modules.setdefault("aiohttp", aiohttp)

homeassistant = ModuleType("homeassistant")
config_entries = ModuleType("homeassistant.config_entries")
core = ModuleType("homeassistant.core")
helpers = ModuleType("homeassistant.helpers")
aiohttp_client = ModuleType("homeassistant.helpers.aiohttp_client")
llm = ModuleType("homeassistant.helpers.llm")
util = ModuleType("homeassistant.util")
json_module = ModuleType("homeassistant.util.json")


class HomeAssistant:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}


class ConfigEntry:
    def __init__(self, *, data: dict[str, Any], entry_id: str = "entry-1") -> None:
        self.data = data
        self.entry_id = entry_id


class ConfigFlow:
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__()

    async def async_set_unique_id(self, unique_id: str) -> None:
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self) -> None:
        return None

    def async_create_entry(self, *, title: str, data: dict[str, Any]) -> dict[str, Any]:
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(self, *, step_id: str, data_schema: Any) -> dict[str, Any]:
        return {"type": "form", "step_id": step_id, "data_schema": data_schema}


class API:
    def __init__(self, *, hass: HomeAssistant, id: str, name: str) -> None:
        self.hass = hass
        self.id = id
        self.name = name


class Tool:
    pass


class LLMContext:
    pass


@dataclass
class ToolInput:
    tool_args: dict[str, Any]


@dataclass
class APIInstance:
    api: API
    api_prompt: str
    llm_context: LLMContext
    tools: list[Tool]


def async_register_api(hass: HomeAssistant, api: API) -> Any:
    hass.data.setdefault("_registered_apis", []).append(api)

    def unregister() -> None:
        hass.data["_registered_apis"].remove(api)

    return unregister


def async_get_clientsession(hass: HomeAssistant) -> Any:
    return hass.data["session"]


config_entries.ConfigEntry = ConfigEntry
config_entries.ConfigFlow = ConfigFlow
config_entries.ConfigFlowResult = dict[str, Any]
core.HomeAssistant = HomeAssistant
aiohttp_client.async_get_clientsession = async_get_clientsession
llm.API = API
llm.APIInstance = APIInstance
llm.LLMContext = LLMContext
llm.Tool = Tool
llm.ToolInput = ToolInput
llm.async_register_api = async_register_api
json_module.JsonObjectType = dict[str, Any]

homeassistant.config_entries = config_entries
homeassistant.core = core
helpers.aiohttp_client = aiohttp_client
helpers.llm = llm
homeassistant.helpers = helpers
util.json = json_module
homeassistant.util = util

sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.config_entries", config_entries)
sys.modules.setdefault("homeassistant.core", core)
sys.modules.setdefault("homeassistant.helpers", helpers)
sys.modules.setdefault("homeassistant.helpers.aiohttp_client", aiohttp_client)
sys.modules.setdefault("homeassistant.helpers.llm", llm)
sys.modules.setdefault("homeassistant.util", util)
sys.modules.setdefault("homeassistant.util.json", json_module)

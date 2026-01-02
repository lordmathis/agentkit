from typing import Any, Dict

from agentkit.config import ProviderConfig
from agentkit.providers import Provider


class ProviderRegistry:
    _providers: Dict[str, Provider] = {}

    @classmethod
    def register_all(cls, providers: Dict[str, ProviderConfig]):
        for name, provider_cfg in providers.items():
            provider = Provider(provider_cfg)
            cls._providers[name] = provider

    @classmethod
    def get_provider(cls, name: str) -> Provider | None:
        return cls._providers.get(name)
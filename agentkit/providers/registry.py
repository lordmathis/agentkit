from typing import Any, Dict

from agentkit.config import ProviderConfig
from agentkit.providers import Provider


class ProviderRegistry:
    _providers: Dict[str, Provider] = {}

    def __init__(self, providers: Dict[str, ProviderConfig]) -> None:
        for name, provider_cfg in providers.items():
            provider = Provider(provider_cfg)
            self._providers[name] = provider

    def get_provider(self, name: str) -> Provider | None:
        return self._providers.get(name)
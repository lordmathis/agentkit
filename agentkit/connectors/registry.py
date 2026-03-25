from typing import Dict
import logging

from agentkit.config import ConnectorsConfig, ConnectorType
from agentkit.connectors.client_base import ConnectorClient
from agentkit.connectors.github import GitHubClient
from agentkit.connectors.forgejo import ForgejoClient

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: Dict[str, ConnectorClient] = {}

    @classmethod
    async def create(
        cls, connectors: Dict[str, ConnectorsConfig]
    ) -> "ConnectorRegistry":
        registry = cls()
        for name, cfg in connectors.items():
            connector = await registry._create_connector(name, cfg)
            if connector:
                registry._connectors[name] = connector
                logger.info(f"Registered connector: {name} ({cfg.type})")
        logger.info(f"Registered {len(registry._connectors)} connector(s)")
        return registry

    async def _create_connector(
        self, name: str, cfg: ConnectorsConfig
    ) -> ConnectorClient | None:
        connector = None
        if cfg.type == ConnectorType.GITHUB:
            connector = GitHubClient(token=cfg.token)
        elif cfg.type == ConnectorType.FORGEJO:
            connector = ForgejoClient(
                token=cfg.token,
                base_url=cfg.base_url or "https://codeberg.org/api/v1",
            )
        else:
            logger.error(f"Unknown connector type: {cfg.type}")
            return None

        if not await connector.authenticate():
            logger.error(f"Failed to authenticate connector {name} ({cfg.type})")
            return None

        logger.info(f"Successfully authenticated connector {name} ({cfg.type})")
        return connector

    def get_connector(self, name: str) -> ConnectorClient | None:
        return self._connectors.get(name)

    def list_connectors(self) -> Dict[str, ConnectorClient]:
        """List all registered connectors."""
        return self._connectors.copy()

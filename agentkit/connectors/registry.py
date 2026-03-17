from typing import Dict
import logging

from agentkit.config import ConnectorsConfig, ConnectorType
from agentkit.connectors.client_base import RepoBrowserClient
from agentkit.connectors.github import GitHubClient

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    def __init__(self, connectors: Dict[str, ConnectorsConfig]) -> None:
        self._connectors: Dict[str, RepoBrowserClient] = {}
        for name, cfg in connectors.items():
            self._connectors[name] = self._create_connector(name, cfg)

    def _create_connector(self, name: str, cfg: ConnectorsConfig) -> RepoBrowserClient:
        connector = None
        if cfg.type == ConnectorType.GITHUB:
            connector = GitHubClient(token=cfg.token)
        else:
            logger.error(f"Unknown connector type: {cfg.type}")

        if not connector.authenticate():
            logger.error(f"Failed to authenticate connector {name}")
            return None
        
        return connector

    def get_connector(self, name: str) -> RepoBrowserClient | None:
        return self._connectors.get(name)

    def list_connectors(self) -> Dict[str, RepoBrowserClient]:
        """List all registered connectors."""
        return self._connectors.copy()

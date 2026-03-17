from abc import ABC, abstractmethod
from typing import Dict, List

from pydantic import BaseModel


class FileNode(BaseModel):
    """Represents a file or directory in a repository tree"""

    path: str
    name: str
    type: str
    size: int | None = None
    children: List["FileNode"] | None = None


class TokenEstimate(BaseModel):
    """Represents token count estimates for files"""

    total_tokens: int
    files: Dict[str, int]


class RepoBrowserClient(ABC):
    """Abstract base class for repository browser clients"""

    @abstractmethod
    async def authenticate(self) -> bool:
        """Verify that the client is properly authenticated"""
        ...

    @abstractmethod
    async def list_repositories(self) -> List[Dict]:
        """List repositories accessible with the current credentials"""
        ...

    @abstractmethod
    async def browse_tree(self, repo: str, path: str = "") -> FileNode:
        """Browse the file tree of a repository

        Args:
            repo: Repository identifier (format depends on implementation)
            path: Path within the repository (empty string for root)

        Returns:
            FileNode representing the directory with its children
        """
        ...

    @abstractmethod
    async def get_file_content(self, repo: str, path: str) -> bytes:
        """Fetch raw file content from a repository

        Args:
            repo: Repository identifier
            path: File path to fetch

        Returns:
            Raw bytes of the file content
        """
        ...

    @abstractmethod
    async def fetch_files(self, repo: str, paths: List[str]) -> Dict[str, str]:
        """Fetch file contents from a repository

        Args:
            repo: Repository identifier
            paths: List of file paths to fetch

        Returns:
            Dictionary mapping file path to content
        """
        ...

    @abstractmethod
    async def estimate_tokens(
        self, repo: str, paths: List[str], ref: str = "HEAD"
    ) -> TokenEstimate:
        """Estimate token count for files

        Args:
            repo: Repository identifier
            paths: List of file paths to estimate tokens for
            ref: Git reference (branch, tag, or commit) to use

        Returns:
            TokenEstimate with total and per-file token counts
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources"""
        ...

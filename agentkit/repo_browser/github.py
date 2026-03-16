import base64
import logging
from typing import Dict, List

import httpx

from agentkit.repo_browser.client_base import FileNode, RepoBrowserClient, TokenEstimate

logger = logging.getLogger(__name__)


class GitHubClient(RepoBrowserClient):
    """Client for interacting with GitHub REST API"""

    def __init__(self, token: str):
        """Initialize GitHub client with authentication token

        Args:
            token: GitHub personal access token
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=30.0,
        )
        self._token_cache: Dict[tuple, int] = {}

    async def authenticate(self) -> bool:
        """Verify that the token is valid

        Returns:
            True if authentication is successful, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/user")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    async def list_repositories(self) -> List[Dict]:
        """List repositories accessible with the current token

        Returns:
            List of repository dictionaries with name, full_name, description, etc.
        """
        try:
            repos = []
            page = 1
            per_page = 100

            while True:
                response = await self.client.get(
                    f"{self.base_url}/user/repos",
                    params={
                        "per_page": per_page,
                        "page": page,
                        "sort": "updated",
                        "affiliation": "owner,collaborator,organization_member",
                    },
                )
                response.raise_for_status()
                page_repos = response.json()

                if not page_repos:
                    break

                repos.extend(page_repos)

                if len(page_repos) < per_page:
                    break

                page += 1

            return repos
        except Exception as e:
            logger.error(f"Failed to list repositories: {e}")
            raise

    async def browse_tree(self, repo: str, path: str = "") -> FileNode:
        """Browse the file tree of a repository

        Args:
            repo: Repository in format "owner/repo"
            path: Path within the repository (empty string for root)

        Returns:
            FileNode representing the directory with its children
        """
        try:
            url = f"{self.base_url}/repos/{repo}/contents/{path}"
            response = await self.client.get(url)
            response.raise_for_status()
            contents = response.json()

            if isinstance(contents, dict):
                return FileNode(
                    path=contents["path"],
                    name=contents["name"],
                    type="file",
                    size=contents.get("size"),
                )

            children = []
            for item in contents:
                child = FileNode(
                    path=item["path"],
                    name=item["name"],
                    type="file" if item["type"] == "file" else "dir",
                    size=item.get("size"),
                )
                children.append(child)

            return FileNode(
                path=path,
                name=path.split("/")[-1] if path else repo.split("/")[-1],
                type="dir",
                children=children,
            )
        except Exception as e:
            logger.error(f"Failed to browse tree for {repo} at {path}: {e}")
            raise

    async def get_file_content(self, repo: str, path: str) -> bytes:
        """Fetch raw file content from a repository

        Args:
            repo: Repository in format "owner/repo"
            path: File path to fetch

        Returns:
            Raw bytes of the file content
        """
        try:
            url = f"{self.base_url}/repos/{repo}/contents/{path}"
            response = await self.client.get(url)
            response.raise_for_status()
            content_data = response.json()

            if "content" in content_data:
                encoded_content = content_data["content"]
                encoded_content = encoded_content.replace("\n", "")
                return base64.b64decode(encoded_content)
            else:
                raise ValueError(f"No content found for {path} in {repo}")
        except Exception as e:
            logger.error(f"Failed to get file content for {path} in {repo}: {e}")
            raise

    async def fetch_files(self, repo: str, paths: List[str]) -> Dict[str, str]:
        """Fetch file contents from a repository

        Args:
            repo: Repository in format "owner/repo"
            paths: List of file paths to fetch

        Returns:
            Dictionary mapping file path to content
        """
        try:
            file_contents = {}

            for path in paths:
                url = f"{self.base_url}/repos/{repo}/contents/{path}"
                response = await self.client.get(url)
                response.raise_for_status()
                content_data = response.json()

                if "content" in content_data:
                    encoded_content = content_data["content"]
                    encoded_content = encoded_content.replace("\n", "")
                    decoded_content = base64.b64decode(encoded_content).decode("utf-8")
                    file_contents[path] = decoded_content
                else:
                    logger.warning(f"No content found for {path} in {repo}")

            return file_contents
        except Exception as e:
            logger.error(f"Failed to fetch files from {repo}: {e}")
            raise

    async def estimate_tokens(
        self, repo: str, paths: List[str], ref: str = "HEAD"
    ) -> TokenEstimate:
        """Estimate token count for files with caching based on commit hash

        Args:
            repo: Repository in format "owner/repo"
            paths: List of file paths to estimate tokens for
            ref: Git reference (branch, tag, or commit) to use (default: HEAD)

        Returns:
            TokenEstimate with total and per-file token counts
        """
        try:
            commits_url = f"{self.base_url}/repos/{repo}/commits/{ref}"
            commits_response = await self.client.get(commits_url)
            commits_response.raise_for_status()
            commit_data = commits_response.json()
            commit_hash = commit_data["sha"]

            file_tokens = {}
            total_tokens = 0
            paths_to_fetch = []

            for path in paths:
                cache_key = (repo, commit_hash, path)

                if cache_key in self._token_cache:
                    tokens = self._token_cache[cache_key]
                    file_tokens[path] = tokens
                    total_tokens += tokens
                else:
                    paths_to_fetch.append(path)

            if paths_to_fetch:
                file_contents = await self.fetch_files(repo, paths_to_fetch)

                for path, content in file_contents.items():
                    tokens = len(content) // 4
                    file_tokens[path] = tokens
                    total_tokens += tokens

                    cache_key = (repo, commit_hash, path)
                    self._token_cache[cache_key] = tokens

            return TokenEstimate(total_tokens=total_tokens, files=file_tokens)
        except Exception as e:
            logger.error(f"Failed to estimate tokens for {repo}: {e}")
            raise

    async def close(self) -> None:
        """Clean up resources"""
        await self.client.aclose()

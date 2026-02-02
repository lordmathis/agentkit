import base64
import hashlib
import logging
from typing import Dict, List, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class FileNode(BaseModel):
    """Represents a file or directory in a GitHub repository tree"""
    path: str
    name: str
    type: str  # "file" or "dir"
    size: Optional[int] = None
    children: Optional[List['FileNode']] = None


class TokenEstimate(BaseModel):
    """Represents token count estimates for files"""
    total_tokens: int
    files: Dict[str, int]  # path -> token count


class GitHubClient:
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
                "Accept": "application/vnd.github+json"
            },
            timeout=30.0
        )
        # Cache for token estimation: (repo, commit_hash, path) -> token_count
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
                        "affiliation": "owner,collaborator,organization_member"
                    }
                )
                response.raise_for_status()
                page_repos = response.json()
                
                if not page_repos:
                    break
                
                repos.extend(page_repos)
                
                # Check if we've received all repos
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
            # Get contents at the specified path
            url = f"{self.base_url}/repos/{repo}/contents/{path}"
            response = await self.client.get(url)
            response.raise_for_status()
            contents = response.json()
            
            # If it's a single file, return it as a FileNode
            if isinstance(contents, dict):
                return FileNode(
                    path=contents["path"],
                    name=contents["name"],
                    type="file",
                    size=contents.get("size")
                )
            
            # If it's a directory, create FileNodes for all children
            children = []
            for item in contents:
                child = FileNode(
                    path=item["path"],
                    name=item["name"],
                    type="file" if item["type"] == "file" else "dir",
                    size=item.get("size")
                )
                children.append(child)
            
            # Return the directory node with children
            return FileNode(
                path=path,
                name=path.split("/")[-1] if path else repo.split("/")[-1],
                type="dir",
                children=children
            )
        except Exception as e:
            logger.error(f"Failed to browse tree for {repo} at {path}: {e}")
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
                
                # Decode base64 content
                if "content" in content_data:
                    encoded_content = content_data["content"]
                    # Remove newlines from base64 string
                    encoded_content = encoded_content.replace("\n", "")
                    decoded_content = base64.b64decode(encoded_content).decode("utf-8")
                    file_contents[path] = decoded_content
                else:
                    logger.warning(f"No content found for {path} in {repo}")
            
            return file_contents
        except Exception as e:
            logger.error(f"Failed to fetch files from {repo}: {e}")
            raise
    
    async def estimate_tokens(self, repo: str, paths: List[str], ref: str = "HEAD") -> TokenEstimate:
        """Estimate token count for files with caching based on commit hash
        
        Args:
            repo: Repository in format "owner/repo"
            paths: List of file paths to estimate tokens for
            ref: Git reference (branch, tag, or commit) to use (default: HEAD)
        
        Returns:
            TokenEstimate with total and per-file token counts
        """
        try:
            # Get the current commit hash for the ref
            commits_url = f"{self.base_url}/repos/{repo}/commits/{ref}"
            commits_response = await self.client.get(commits_url)
            commits_response.raise_for_status()
            commit_data = commits_response.json()
            commit_hash = commit_data["sha"]
            
            # Check cache for all files with this commit hash
            file_tokens = {}
            total_tokens = 0
            paths_to_fetch = []
            
            for path in paths:
                cache_key = (repo, commit_hash, path)
                
                if cache_key in self._token_cache:
                    # File is cached for this exact commit
                    tokens = self._token_cache[cache_key]
                    file_tokens[path] = tokens
                    total_tokens += tokens
                else:
                    # Need to fetch this file
                    paths_to_fetch.append(path)
            
            # Fetch and process files that weren't in cache
            if paths_to_fetch:
                file_contents = await self.fetch_files(repo, paths_to_fetch)
                
                for path, content in file_contents.items():
                    # Simple estimation: divide character count by 4
                    tokens = len(content) // 4
                    file_tokens[path] = tokens
                    total_tokens += tokens
                    
                    # Cache the result with commit hash
                    cache_key = (repo, commit_hash, path)
                    self._token_cache[cache_key] = tokens
            
            return TokenEstimate(
                total_tokens=total_tokens,
                files=file_tokens
            )
        except Exception as e:
            logger.error(f"Failed to estimate tokens for {repo}: {e}")
            raise
    
    async def close(self):
        """Clean up resources"""
        await self.client.aclose()

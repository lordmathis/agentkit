"""Handle file uploads and GitHub file operations."""
import logging
import os
from typing import Dict, List, Optional

from agentkit.db.db import Database
from agentkit.github.client import FileNode, GitHubClient

logger = logging.getLogger(__name__)


class FileHandler:
    """Handles file uploads and GitHub file operations for chat context."""

    def __init__(self, chat_id: str, db: Database, github_client: Optional[GitHubClient] = None):
        self.chat_id = chat_id
        self.db = db
        self.github_client = github_client
        self._img_files: List[str] = []
        self._file_contents: Dict[str, str] = {}
        self._github_files: set[str] = set()  # Track which files came from GitHub

    async def handle_file_upload(self, file_path: str, content_type: str) -> None:
        """Handle a file upload by storing it in the pending context.
        
        Args:
            file_path: Path to the uploaded file
            content_type: MIME type of the file
            
        Raises:
            ValueError: If file encoding is unsupported
        """
        logger.info(f"Handling file upload: {file_path} with content type: {content_type}")

        if content_type.startswith("image/"):
            self._img_files.append(file_path)
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                self._file_contents[file_path] = content
                logger.info(f"Read content from {file_path}, length: {len(content)} characters")
        except (UnicodeDecodeError, UnicodeError) as e:
            logger.error(f"Failed to read file {file_path}: {str(e)}")
            raise ValueError(f"Unsupported file encoding for file: {file_path}")

    async def add_files_from_github(
        self, 
        repo: str, 
        paths: List[str], 
        exclude_paths: Optional[List[str]] = None
    ) -> List[str]:
        """Add files from GitHub to chat context.
        
        Args:
            repo: Repository in format "owner/repo"
            paths: List of file or directory paths
            exclude_paths: Optional list of paths to exclude
            
        Returns:
            List of file paths that were added
            
        Raises:
            ValueError: If GitHub integration is not configured
        """
        if not self.github_client:
            raise ValueError("GitHub integration is not configured")
        
        if exclude_paths is None:
            exclude_paths = []
        
        # Expand directories to get all files
        all_file_paths = await self._expand_paths_to_files(repo, paths, exclude_paths)
        
        # Fetch file contents
        file_contents = await self.github_client.fetch_files(repo, all_file_paths)
        
        uploads_dir = f"uploads/{self.chat_id}"
        os.makedirs(uploads_dir, exist_ok=True)
        
        saved_paths = []
        for github_path, content in file_contents.items():
            # Create a safe filename from the GitHub path
            safe_filename = github_path.replace("/", "_")
            local_path = f"{uploads_dir}/{safe_filename}"
            
            # Write content to disk
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Add to pending context with local path
            self._file_contents[local_path] = content
            self._github_files.add(local_path)  # Track that this is a GitHub file
            saved_paths.append(local_path)
            
        return saved_paths

    def remove_github_files(self) -> None:
        """Remove all GitHub files from the pending context."""
        # Remove files that are tracked as GitHub files
        for github_path in list(self._github_files):
            self._file_contents.pop(github_path, None)
            self._img_files = [f for f in self._img_files if f != github_path]
        
        # Clear the tracking set
        self._github_files.clear()

    def remove_uploaded_file(self, file_path: str) -> None:
        """Remove a specific uploaded file from the pending context.
        
        Args:
            file_path: The file path to remove (relative to chat uploads directory)
        """
        # Remove from file contents dict
        self._file_contents.pop(file_path, None)
        
        # Remove from image files list
        if file_path in self._img_files:
            self._img_files.remove(file_path)

    def save_attachments_to_db(self, message_id: str) -> None:
        """Save pending file attachments metadata to database.
        
        Args:
            message_id: The message ID to attach files to
        """
        # Save file attachments metadata to database (files are already on disk)
        for file_path in self._file_contents.keys():
            filename = os.path.basename(file_path)
            self.db.save_file_attachment(
                message_id=message_id,
                filename=filename,
                file_path=file_path,
                content_type="text/plain"  # Could be enhanced to detect actual content type
            )
        
        # Save image attachments metadata to database
        for img_path in self._img_files:
            filename = os.path.basename(img_path)
            self.db.save_file_attachment(
                message_id=message_id,
                filename=filename,
                file_path=img_path,
                content_type=f"image/{os.path.splitext(img_path)[1].lower().lstrip('.')}"
            )

    def clear_pending_files(self) -> None:
        """Clear all pending files from temporary storage."""
        self._img_files.clear()
        self._file_contents.clear()
        self._github_files.clear()

    async def _expand_paths_to_files(
        self, 
        repo: str, 
        paths: List[str], 
        exclude_paths: List[str]
    ) -> List[str]:
        """Expand paths (which may include directories) to a list of file paths.
        
        Args:
            repo: Repository in format "owner/repo"
            paths: List of file or directory paths
            exclude_paths: List of paths to exclude
            
        Returns:
            List of file paths only (directories expanded)
            
        Raises:
            ValueError: If GitHub client is not configured
        """
        if not self.github_client:
            raise ValueError("GitHub client is not configured")
            
        exclude_set = set(exclude_paths)
        all_files = []
        
        for path in paths:
            if path in exclude_set:
                continue
                
            # Check if this is a file or directory
            try:
                tree_node = await self.github_client.browse_tree(repo, path)
                
                if tree_node.type == "file":
                    all_files.append(path)
                else:
                    # It's a directory, recursively get all files
                    files_in_dir = await self._get_all_files_in_dir(repo, tree_node, exclude_set)
                    all_files.extend(files_in_dir)
            except Exception as e:
                logger.error(f"Failed to process path {path}: {e}")
                continue
        
        return all_files

    async def _get_all_files_in_dir(
        self, 
        repo: str, 
        node: FileNode, 
        exclude_set: set
    ) -> List[str]:
        """Recursively get all file paths in a directory.
        
        Args:
            repo: Repository in format "owner/repo"
            node: Directory node to traverse
            exclude_set: Set of paths to exclude
            
        Returns:
            List of file paths in the directory
            
        Raises:
            ValueError: If GitHub client is not configured
        """
        if not self.github_client:
            raise ValueError("GitHub client is not configured")
            
        files = []
        
        if not node.children:
            return files
        
        for child in node.children:
            if child.path in exclude_set:
                continue
                
            if child.type == "file":
                files.append(child.path)
            else:
                # It's a subdirectory, load and recurse
                try:
                    subtree = await self.github_client.browse_tree(repo, child.path)
                    subfiles = await self._get_all_files_in_dir(repo, subtree, exclude_set)
                    files.extend(subfiles)
                except Exception as e:
                    logger.error(f"Failed to process subdirectory {child.path}: {e}")
                    continue
        
        return files

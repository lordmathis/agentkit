import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class EstimateTokensRequest(BaseModel):
    repo: str
    paths: List[str]
    exclude_paths: Optional[List[str]] = []


@router.get("/repo/repositories")
async def list_repositories(request: Request):
    """
    List repositories accessible with the configured credentials.
    """
    repo_browser = getattr(request.app.state, "repo_browser", None)

    if not repo_browser:
        raise HTTPException(
            status_code=503,
            detail="Repository browser is not configured. Please set repo_browser in your config.",
        )

    try:
        repos = await repo_browser.list_repositories()
        return {"repositories": repos}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list repositories: {str(e)}"
        )


@router.get("/repo/tree")
async def browse_tree(request: Request, repo: str, path: str = ""):
    """
    Browse the file tree of a repository.

    Query parameters:
    - repo: Repository identifier
    - path: Path within the repository (empty for root)
    """
    repo_browser = getattr(request.app.state, "repo_browser", None)

    if not repo_browser:
        raise HTTPException(
            status_code=503,
            detail="Repository browser is not configured. Please set repo_browser in your config.",
        )

    try:
        tree = await repo_browser.browse_tree(repo, path)
        return tree.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to browse tree: {str(e)}")


@router.post("/repo/estimate")
async def estimate_tokens(request: Request, body: EstimateTokensRequest):
    """
    Estimate token count for files from a repository.
    Supports both individual files and directories (which are expanded recursively).
    Optionally exclude specific paths.
    """
    repo_browser = getattr(request.app.state, "repo_browser", None)

    if not repo_browser:
        raise HTTPException(
            status_code=503,
            detail="Repository browser is not configured. Please set repo_browser in your config.",
        )

    try:
        logger.info(
            f"Estimating tokens for repo={body.repo}, paths={body.paths}, exclude={body.exclude_paths}"
        )

        all_file_paths = await _expand_paths_to_files(
            repo_browser, body.repo, body.paths, body.exclude_paths or []
        )

        logger.info(
            f"Expanded to {len(all_file_paths)} files: {all_file_paths[:10]}..."
        )

        if not all_file_paths:
            return {"total_tokens": 0, "files": {}}

        estimate = await repo_browser.estimate_tokens(body.repo, all_file_paths)
        logger.info(f"Token estimate: {estimate.total_tokens}")
        return estimate.model_dump()
    except Exception as e:
        logger.error(f"Failed to estimate tokens: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to estimate tokens: {str(e)}"
        )


async def _expand_paths_to_files(
    repo_browser, repo: str, paths: List[str], exclude_paths: List[str]
) -> List[str]:
    """Expand paths (which may include directories) to a list of file paths."""
    exclude_set = set(exclude_paths)
    all_files = []

    for path in paths:
        if path in exclude_set:
            continue

        try:
            logger.debug(f"Processing path: '{path}'")
            tree_node = await repo_browser.browse_tree(repo, path)
            logger.debug(f"Path '{path}' type: {tree_node.type}")

            if tree_node.type == "file":
                all_files.append(path)
            else:
                files_in_dir = await _get_all_files_in_dir(
                    repo_browser, repo, tree_node, exclude_set
                )
                logger.debug(f"Found {len(files_in_dir)} files in directory '{path}'")
                all_files.extend(files_in_dir)
        except Exception as e:
            logger.error(f"Failed to process path '{path}': {str(e)}")
            continue

    return all_files


async def _get_all_files_in_dir(
    repo_browser, repo: str, node, exclude_set: set
) -> List[str]:
    """Recursively get all file paths in a directory."""
    files = []

    if not node.children:
        return files

    for child in node.children:
        if child.path in exclude_set:
            continue

        if child.type == "file":
            files.append(child.path)
        else:
            try:
                subtree = await repo_browser.browse_tree(repo, child.path)
                subfiles = await _get_all_files_in_dir(
                    repo_browser, repo, subtree, exclude_set
                )
                files.extend(subfiles)
            except Exception:
                continue

    return files

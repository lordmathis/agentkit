from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()


class EstimateTokensRequest(BaseModel):
    repo: str
    paths: List[str]


@router.get("/github/repositories")
async def list_repositories(request: Request):
    """
    List GitHub repositories accessible with the configured token.
    """
    github_client = request.app.state.github_client
    
    if not github_client:
        raise HTTPException(
            status_code=503,
            detail="GitHub integration is not configured. Please set GITHUB_TOKEN environment variable."
        )
    
    try:
        repos = await github_client.list_repositories()
        return {"repositories": repos}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list repositories: {str(e)}"
        )


@router.get("/github/tree")
async def browse_tree(request: Request, repo: str, path: str = ""):
    """
    Browse the file tree of a GitHub repository.
    
    Query parameters:
    - repo: Repository in format "owner/repo"
    - path: Path within the repository (empty for root)
    """
    github_client = request.app.state.github_client
    
    if not github_client:
        raise HTTPException(
            status_code=503,
            detail="GitHub integration is not configured. Please set GITHUB_TOKEN environment variable."
        )
    
    try:
        tree = await github_client.browse_tree(repo, path)
        return tree.model_dump()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to browse tree: {str(e)}"
        )


@router.post("/github/estimate")
async def estimate_tokens(request: Request, body: EstimateTokensRequest):
    """
    Estimate token count for files from a GitHub repository.
    """
    github_client = request.app.state.github_client
    
    if not github_client:
        raise HTTPException(
            status_code=503,
            detail="GitHub integration is not configured. Please set GITHUB_TOKEN environment variable."
        )
    
    try:
        estimate = await github_client.estimate_tokens(body.repo, body.paths)
        return estimate.model_dump()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to estimate tokens: {str(e)}"
        )

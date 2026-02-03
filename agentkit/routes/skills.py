"""Skills API endpoints."""
import logging
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/skills")
async def list_skills(request: Request) -> Dict[str, List[Dict]]:
    """
    List all available skills.
    
    Returns:
        Dictionary with 'skills' key containing list of skill metadata
    """
    try:
        skill_registry = request.app.state.skill_registry
        skills = skill_registry.list_skills()
        return {"skills": skills}
    except Exception as e:
        logger.error(f"Error listing skills: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list skills: {str(e)}")


@router.get("/skills/{skill_name}")
async def get_skill(skill_name: str, request: Request) -> Dict:
    """
    Get details of a specific skill including its content.
    
    Args:
        skill_name: Name of the skill to retrieve
        
    Returns:
        Dictionary with skill metadata and content
    """
    try:
        skill_registry = request.app.state.skill_registry
        skill = skill_registry.get_skill(skill_name)
        
        if skill is None:
            raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")
        
        content = skill_registry.get_skill_content(skill_name)
        
        return {
            "name": skill.name,
            "path": str(skill.path),
            "exists": skill.exists,
            "content": content
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting skill {skill_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get skill: {str(e)}")

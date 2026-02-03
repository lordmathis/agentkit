"""Skill registry for discovering and managing skills."""
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class Skill:
    """Represents a skill with its metadata."""
    
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.skill_file = path / "SKILL.md"
    
    @property
    def exists(self) -> bool:
        """Check if the SKILL.md file exists."""
        return self.skill_file.exists()
    
    def read_content(self) -> str:
        """Read the content of the SKILL.md file on demand."""
        if not self.exists:
            raise FileNotFoundError(f"SKILL.md not found for skill: {self.name}")
        return self.skill_file.read_text(encoding="utf-8")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert skill to dictionary representation."""
        return {
            "name": self.name,
            "path": str(self.path),
            "exists": self.exists,
        }


class SkillRegistry:
    """Registry for discovering and managing skills."""
    
    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)
        self._skills: Dict[str, Skill] = {}
        self._discover_skills()
    
    def _discover_skills(self):
        """Discover all skills in the skills directory."""
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory does not exist: {self.skills_dir}")
            return
        
        if not self.skills_dir.is_dir():
            logger.warning(f"Skills path is not a directory: {self.skills_dir}")
            return
        
        # Find all subdirectories that contain a SKILL.md file
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            # Skip private/hidden directories
            if skill_dir.name.startswith("_") or skill_dir.name.startswith("."):
                continue
            
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skill_name = skill_dir.name
                skill = Skill(name=skill_name, path=skill_dir)
                self._skills[skill_name] = skill
                logger.info(f"Discovered skill: {skill_name}")
        
        logger.info(f"Discovered {len(self._skills)} skill(s)")
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """List all available skills."""
        return [skill.to_dict() for skill in self._skills.values()]
    
    def get_skill(self, name: str) -> Skill | None:
        """Get a specific skill by name."""
        return self._skills.get(name)
    
    def get_skill_content(self, name: str) -> str | None:
        """Read the content of a specific skill."""
        skill = self.get_skill(name)
        if skill is None:
            return None
        try:
            return skill.read_content()
        except FileNotFoundError:
            logger.error(f"SKILL.md not found for skill: {name}")
            return None

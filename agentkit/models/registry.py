from agentkit.models import BaseModel
from typing import Dict, Optional

class ModelRegistry():
    _models: Dict[str, BaseModel] = {}

    @classmethod
    def register_model(cls, name: str, model: BaseModel) -> None:
        """Register a new model."""
        if name in cls._models:
            return
        cls._models[name] = model

    @classmethod
    def get_model(cls, name: str) -> Optional[BaseModel]:
        """Retrieve a model by name."""
        return cls._models.get(name)
    
    @classmethod
    def list_models(cls) -> Dict[str, BaseModel]:
        """List all registered models."""
        return cls._models.copy()
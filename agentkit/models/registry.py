import importlib.util
import inspect
import os
from typing import Dict, Optional

from agentkit.models import BaseModel


class ModelRegistry():
    _models: Dict[str, BaseModel] = {}

    def register_all(self):
        # Discover and register all models in this folder
        models_folder = os.path.dirname(__file__)
        skip_files = ["registry.py", "model.py", "__init__.py"]
        model_files = [
            f
            for f in os.listdir(models_folder)
            if f.endswith(".py") and f not in skip_files
        ]
        for filename in model_files:
            # Construct module path
            module_path = os.path.join(models_folder, filename)
            module_name = f"agentkit.models.{filename[:-3]}"

            # Load the module dynamically
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find all classes that inherit from BaseModel
            model_class = None
            for _, obj in inspect.getmembers(module, inspect.isclass):
                # Skip imported classes (only get classes defined in this module)
                if obj.__module__ != module_name:
                    continue
                # Check if it inherits from BaseModel (but is not BaseModel itself)
                if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel:
                    model_class = obj
                    break

            # Instantiate and register the model
            if model_class is not None:
                try:
                    model_instance = model_class()
                    # Use the class name (without "Model" suffix if present) as the registration name
                    model_name = model_class.__name__
                    if model_name.endswith("Model"):
                        model_name = model_name[:-5]
                    model_name = model_name.lower()
                    self.register_model(model_name, model_instance)
                except Exception as e:
                    print(f"Warning: Failed to instantiate model from {filename}: {e}")

    def register_model(self, name: str, model: BaseModel) -> None:
        """Register a new model."""
        if name in self._models:
            return
        self._models[name] = model

    def get_model(self, name: str) -> Optional[BaseModel]:
        """Retrieve a model by name."""
        return self._models.get(name)
    
    def list_models(self) -> Dict[str, BaseModel]:
        """List all registered models."""
        return self._models.copy()
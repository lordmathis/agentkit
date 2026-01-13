import httpx
from openai import OpenAI
from typing import Any

from agentkit.config import ProviderConfig

class PreEncodedBasicAuth(httpx.Auth):  
    def __init__(self, encoded_token):  
        self.encoded_token = encoded_token  
      
    def auth_flow(self, request):  
        request.headers['Authorization'] = f'Basic {self.encoded_token}'  
        yield request  


class Provider:
    def __init__(self, config: ProviderConfig, name: str):
        self.config = config
        self._name = name
        self._http_client = None
        self._openai_client = None

    def name(self) -> str:
        return self._name
    
    def _get_http_client(self) -> httpx.Client:
        """Get or create a persistent httpx client with proper auth and SSL settings."""
        if self._http_client is None:
            self._http_client = httpx.Client(
                verify=self.config.verify_ssl,
                auth=PreEncodedBasicAuth(self.config.basic_auth_token) if self.config.basic_auth_token else None,
            )
        return self._http_client

    def get_client_kwargs(self) -> dict:
        """Get client kwargs including authorization headers and SSL verification."""
        return {
            "api_key": self.config.api_key or "",
            "base_url": self.config.api_base or "",
            "http_client": self._get_http_client(),
        }

    def get_model_ids(self) -> list[str] | None:
        """Query the /models endpoint to get available model IDs.
        
        If model_filter is configured, fetches and filters models from the API.
        If model_ids is configured, returns the static list.
        Otherwise, fetches all models from the provider.

        Returns:
            List of model IDs if successful, None if an error occurs
        """
        # If static model_ids are configured and no filter, return them
        if self.config.model_ids and not self.config.model_filter:
            return self.config.model_ids
        
        # Fetch models from API
        if self._openai_client is None:
            self._openai_client = OpenAI(**self.get_client_kwargs())
        
        try:
            models = self._openai_client.models.list()
            
            # Apply filters if configured
            if self.config.model_filter and self.config.model_filter.conditions:
                filtered_ids = []
                
                for model in models.data:
                    # Convert model to dict for easier field access
                    model_dict = model.model_dump() if hasattr(model, 'model_dump') else model.dict()
                    
                    # Check if model passes all filter conditions
                    if self._matches_filter(model_dict, self.config.model_filter.conditions):
                        filtered_ids.append(model_dict.get('id'))
                
                return filtered_ids
            
            # No filter, return all model IDs
            return [model.id for model in models.data]
            
        except Exception as e:
            print(f"Error fetching models from {self._name}: {e}")
            return self.config.model_ids  # Fallback to static list if available

    def _matches_filter(self, model_dict: dict, conditions: list) -> bool:
        """Check if a model matches all filter conditions.
        
        Args:
            model_dict: The model data as a dictionary
            conditions: List of FilterCondition objects
            
        Returns:
            True if the model matches all conditions, False otherwise
        """
        for condition in conditions:
            # Get the field value using JSONPath-like notation (e.g., "pricing.prompt")
            value = self._get_nested_value(model_dict, condition.field)
            
            if value is None:
                return False
            
            # Convert value to string for string operations
            value_str = str(value)
            
            # Check contains condition
            if condition.contains is not None:
                if condition.contains not in value_str:
                    return False
            
            # Check excludes condition
            if condition.excludes is not None:
                if condition.excludes in value_str:
                    return False
            
            # Check equals condition
            if condition.equals is not None:
                if value != condition.equals:
                    return False
        
        return True

    def _get_nested_value(self, data: dict, path: str) -> Any:
        """Get a nested value from a dictionary using dot notation.
        
        Args:
            data: The dictionary to search
            path: Dot-separated path (e.g., "pricing.prompt" or "id")
            
        Returns:
            The value at the path, or None if not found
        """
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return None
            else:
                return None
        
        return current

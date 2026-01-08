import httpx
from openai import OpenAI

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

        Returns:
            List of model IDs if successful, None if an error occurs
        """
        if self._openai_client is None:
            self._openai_client = OpenAI(**self.get_client_kwargs())
        
        models = self._openai_client.models.list()
        return [model.id for model in models.data]

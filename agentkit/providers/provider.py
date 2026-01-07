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
    def __init__(self, config: ProviderConfig):
        self.config = config

    def get_client_kwargs(self) -> dict:
        """Get client kwargs including authorization headers and SSL verification."""
        http_client = httpx.Client(
            verify=self.config.verify_ssl,
            auth=PreEncodedBasicAuth(self.config.basic_auth_token) if self.config.basic_auth_token else None,
        )
        return {
            "api_key": self.config.api_key,
            "base_url": self.config.api_base,
            "http_client": http_client,
        }

    def get_model_ids(self) -> list[str] | None:
        """Query the /models endpoint to get available model IDs.

        Returns:
            List of model IDs if successful, None if an error occurs
        """
        try:
            client = OpenAI(api_key=self.config.api_key, base_url=self.config.api_base)
            models = client.models.list()
            return [model.id for model in models.data]
        except Exception:
            return None
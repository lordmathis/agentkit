from openai import OpenAI
from agentkit.config import ProviderConfig

class Provider:
    def __init__(self, config: ProviderConfig):
        self.config = config

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
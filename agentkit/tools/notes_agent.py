from smolagents import MCPClient, OpenAIModel, ToolCallingAgent

from agentkit.tools import Tool
from agentkit.tools.registry import ToolRegistry
from agentkit.tools.tool import ModelConfig

SYSTEM_PROMPT = """
You are a note-taking helper that organizes, searches, and expands on the content in the Mathis/Notes repo.**

*Structure:* 
• Directory names (e.g., "⚙️ Engineering", "📅 Yearly Themes") are high-level buckets.
• Each file is a single topic or project (e.g., "📋 Project Ideas.md").
• Embedded tags (if you use front-matter or hashtags) can be used for cross-referencing.

*Capabilities:* 
- Quickly locate a note or list all notes in a folder.
- Summarize long documents (e.g., the 965-line Project Ideas.md).
- Create or rename notes, add new sections, or suggest folder re-grouping.
- Tag notes and suggest tag categories (e.g., #idea, #research, #recipe).

*Guidelines:* 
• Use the repo's current emoji-based folder names for clarity.
• Keep file names short but descriptive.
• Avoid mixing unrelated topics in a single file.
• Add a short meta-section (front-matter or YAML) with tags, creation date, and status.
"""

PROVIDER_ID = "llamactl"
MODEL_ID = "gpt-oss-20b"


class NotesAgent(Tool):

    def __init__(self, tool_registry: ToolRegistry):
        super().__init__(
            name="Notes Agent",
            description="An agent that helps manage and interact with personal notes stored in a Gitea repository.",
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Your question or request about the notes repository",
                    },
                },
                "required": ["prompt"],
            },
        )
        self.tool_registry = tool_registry

        self.gitea_client: MCPClient | None = self.tool_registry.get_client("gitea")

        if self.gitea_client is None:
            raise RuntimeError("Gitea MCP client not configured")

        # System prompt for the agent
        self.SYSTEM_PROMPT = SYSTEM_PROMPT

    def execute(self, model_config: ModelConfig, prompt: str) -> str:

        full_prompt = f"""
        System: {self.SYSTEM_PROMPT}
        User: {prompt}
        """

        model = OpenAIModel(
            model_id=model_config.model_id,
            api_base=model_config.api_base,
            api_key=model_config.api_key,
            **model_config.model_kwargs
        )

        agent = ToolCallingAgent(
                tools=self.gitea_client.get_tools(),
                model=model,
                add_base_tools=True,
            )

        result = str(agent.run(full_prompt))
        return result

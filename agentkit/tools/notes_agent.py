from typing import List

from agentkit.tools.manager import ToolManager
from agentkit.tools.smolagents import SmolAgentsAgent


class NotesAgent(SmolAgentsAgent):
    def __init__(self, tool_manager: ToolManager):
        super().__init__(
            tool_manager=tool_manager,
            name="notes_agent",
            tool_servers=["gitea"],
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
            system_prompt="""
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
            """,
        )

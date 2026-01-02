import json
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from agentkit.agents import AgentRegistry
from agentkit.mcps.manager import MCPManager
from agentkit.providers import Provider
from agentkit.providers.registry import ProviderRegistry


class BaseModel():
    """Base model for OpenAI-compatible chat with agent tool calling.

    Subclasses should define:
    - system_prompt: str - The system prompt for the model
    - allowed_agents: Optional[List[str]] - List of allowed agent names (None = all agents)
    """

    system_prompt: str = ""
    allowed_agents: Optional[List[str]] = None

    provider: Optional[Provider] = None
    model_id: str = ""

    client: OpenAI

    def __init__(self, provider_registry: ProviderRegistry, agent_registry: AgentRegistry, mcp_manager: MCPManager):
        self.provider_registry = provider_registry
        self.agent_registry = agent_registry
        self.mcp_manager = mcp_manager
        self.messages: List[ChatCompletionMessageParam] = []


    def chat(self, messages: List[ChatCompletionMessageParam]) -> Dict[str, Any]:
        """Send messages and get completion response with agent tool calling.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            OpenAI chat completion response dict
        """
        print(f"[DEBUG] Starting chat with {len(messages)} messages")

        # Add system prompt if defined and not already present
        if self.system_prompt:
            if not messages or messages[0].get("role") != "system":
                print("[DEBUG] Adding system prompt to messages")
                messages = [{"role": "system", "content": self.system_prompt}] + messages  # type: ignore

        self.messages = messages

        # Get agent tools from registry
        all_tools = self.agent_registry.list_tools()
        print(f"[DEBUG] Retrieved {len(all_tools)} tools from agent registry")

        # Filter tools if allowed_agents is specified
        if self.allowed_agents is not None:
            tools = [
                tool for tool in all_tools
                if tool["function"]["name"] in self.allowed_agents
            ]
            print(f"[DEBUG] Filtered to {len(tools)} allowed tools: {[t['function']['name'] for t in tools]}")
        else:
            tools = all_tools
            print("[DEBUG] No tool filtering applied")

        # Prepare API call params
        api_params: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages
        }

        if tools:
            api_params["tools"] = tools

        print(f"[DEBUG] Calling OpenAI API with model={self.model_id}, tools={'enabled' if tools else 'disabled'}")

        # Call API
        response = self.client.chat.completions.create(**api_params)
        message = response.choices[0].message

        print(f"[DEBUG] Received response, has tool_calls={bool(message.tool_calls)}")

        # Handle tool calls
        if message.tool_calls:
            print(f"[DEBUG] Processing {len(message.tool_calls)} tool calls")

            # Add assistant message with tool calls
            self.messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })  # type: ignore

            # Execute tool calls (run agents)
            for tool_call in message.tool_calls:
                agent_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                prompt = args.get("prompt", "")

                print(f"[DEBUG] Executing tool call: {agent_name} with prompt={prompt[:100]}...")

                # Get and run the agent
                agent = self.agent_registry.get_agent(agent_name)
                if agent:
                    try:
                        print(f"[DEBUG] Running agent: {agent_name}")
                        result = agent.run(prompt)
                        print(f"[DEBUG] Agent {agent_name} completed successfully")
                    except Exception as e:
                        print(f"[ERROR] Error running agent {agent_name}: {str(e)}")
                        result = f"Error running agent: {str(e)}"
                else:
                    print(f"[WARNING] Agent {agent_name} not found")
                    result = f"Agent {agent_name} not found"

                # Add tool result
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result)
                })  # type: ignore

            print("[DEBUG] Getting final response after tool execution")

            # Get final response after tool execution
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=self.messages
            )

            print("[DEBUG] Final response received")

        print("[DEBUG] Chat completed successfully")
        return response.model_dump()

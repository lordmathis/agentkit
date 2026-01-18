# AgentKit

A flexible chat client with Web UI that integrates multiple AI providers, tools, and agent frameworks through a unified plugin architecture.

**Features**:
- OpenAI-compatible API support (OpenRouter, custom endpoints)
- MCP and smolagents tool integration
- React/TypeScript web interface
- Extensible plugin architecture
- SQLAlchemy conversation persistence
- FastAPI backend with async execution

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js (for Web UI)
- uv (Python package manager)

### Installation

1. **Install Python dependencies:**
   ```bash
   uv sync
   ```

2. **Configure the application:**
   Edit `config.yaml` to set up providers, MCP servers, and plugins (see Configuration section)

### Running the Application

1. **Build the Web UI:**
   ```bash
   cd webui
   npm install
   npm run build
   cd ..
   ```

2. **Start the server:**
   ```bash
   source .venv/bin/activate  # Activate virtual environment
   python -m agentkit.main
   ```

   Server will start on `http://localhost:8000` with the Web UI served at the same address

### Running with Docker

1. **Build the Docker image:**
   ```bash
   docker build -t agentkit .
   ```

2. **Run the container:**

   ```bash
   docker run -p 8000:8000 \
     -v $(pwd)/config.yaml:/app/config.yaml \  # Mount config file
     -v $(pwd)/agentkit.db:/app/agentkit.db \  # Mount persistance db
     -e OPENROUTER_API_KEY=your_key_here \     # Set config secrets via env vars
     agentkit
   ```

## Configuration

AgentKit uses a YAML configuration file (`config.yaml`) to set up providers, MCP servers, and plugins. Environment variables can be referenced using `${ENV_VAR}` syntax, which will be automatically expanded with values from your environment.

### Server Configuration

```yaml
server:
  host: "0.0.0.0"
  port: 8000
```

### Provider Configuration

Providers define AI model endpoints (OpenAI-compatible APIs):

```yaml
providers:
  openrouter:
    api_base: "https://openrouter.ai/api/v1"
    api_key: "${OPENROUTER_API_KEY}"
    model_filter:
      conditions:
        - field: "id"
          contains: ":free"  # Filter for free models
  
  custom_provider:
    api_base: "https://your-api.example.com/v1"
    api_key: "${YOUR_API_KEY}"
    verify_ssl: true
```

**Configuration options:**
- `api_base`: Base URL for the API endpoint
- `api_key`: API authentication key (supports environment variables)
- `basic_auth_token`: Optional basic auth token
- `verify_ssl`: Enable/disable SSL verification (default: true)
- `model_filter`: Dynamic model filtering based on conditions

### MCP (Model Context Protocol) Configuration

MCP servers provide tools and capabilities to agents:

```yaml
mcps:
  time:
    command: uvx
    type: stdio
    args:
      - mcp-server-time
  
  filesystem:
    command: npx
    type: stdio
    args:
      - -y
      - "@modelcontextprotocol/server-filesystem"
      - /path/to/directory
mcp_timeout: 60  # Timeout for MCP operations in seconds
```

**MCP Types:**
- `stdio`: Standard input/output communication (currently supported)
- `sse`: Server-sent events (planned support)

### Plugin Configuration

```yaml
plugins:
  chatbots_dir: "chatbots"  # Directory for chatbot plugins
  agents_dir: "agents"      # Directory for agent plugins
```

### Database Configuration

```yaml
history_db_path: "agentkit.db"  # SQLite database for conversation history
```

## Available Tools

Your chatbots and agents can use the following tools:

**Built-in Tools:**
- `web_search`: Search the web using DuckDuckGo
- `visit_webpage`: Extract and read content from web pages

**MCP Tools:**
Configure any MCP-compatible server in your `config.yaml`

**Custom Agent Tools:**
Create your own agents in the `agents/` directory that can combine multiple tools for complex tasks.

## Plugins

Extend AgentKit's functionality by creating custom chatbots and agents:

### Chatbots

Chatbot plugins allow you to create custom chat interfaces with specific configurations. They inherit from `ChatbotPlugin` and provide a consistent initialization pattern.

**Creating a Chatbot Plugin:**

1. Create a Python file in the `chatbots/` directory (e.g., `chatbots/my_bot.py`)
2. Inherit from `ChatbotPlugin` and implement the `configure()` method:

```python
from agentkit.chatbots.plugin import ChatbotPlugin, ChatbotConfig
from agentkit.providers.registry import ProviderRegistry
from agentkit.tools.manager import ToolManager

class MyCustomBot(ChatbotPlugin):
    def configure(self) -> ChatbotConfig:
        provider = self.provider_registry.get_provider("openrouter")
        
        return ChatbotConfig(
            provider=provider,
            model_id="openai/gpt-4",
            system_prompt="You are a helpful assistant.",
            tool_servers=["web_search", "time"],  # Tool servers to use
            max_iterations=5,
            temperature=0.7,
            max_tokens=2000
        )
```

**Key Features:**
- Automatic discovery: Chatbots are automatically loaded from the `chatbots_dir`
- Provider integration: Access to all configured providers
- Tool access: Can specify which MCP/agent tools to use
- Configurable parameters: temperature, max_tokens, max_iterations

### Agents

Agent plugins are [smolagents](https://github.com/huggingface/smolagents)-based autonomous agents that can use multiple tools to accomplish tasks. They inherit from `SmolAgentPlugin`.

**Creating an Agent Plugin:**

1. Create a Python file in the `agents/` directory (e.g., `agents/research_agent.py`)
2. Inherit from `SmolAgentPlugin` and implement the `configure()` method:

```python
from agentkit.tools.smolagents import SmolAgentPlugin, SmolAgentConfig
from agentkit.tools.manager import ToolManager

class ResearchAgent(SmolAgentPlugin):
    def configure(self) -> SmolAgentConfig:
        return SmolAgentConfig(
            name="research_agent",
            description="Research agent that can search and analyze information",
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Research query or task"
                    }
                },
                "required": ["prompt"]
            },
            tool_servers=["web_search", "visit_webpage"],
            system_prompt="You are a research assistant. Use available tools to gather and analyze information."
        )
```

**Agent Capabilities:**
- **Multi-tool access**: Agents can use multiple MCP tools and smolagents tools
- **Autonomous execution**: Agents make decisions about which tools to use
- **Configurable parameters**: Define input schema and system prompts
- **Built-in tools**: Access to web_search and visit_webpage by default

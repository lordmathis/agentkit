# AgentKit

A flexible chat client with Web UI that integrates multiple AI providers, tools, and agent frameworks through a unified plugin architecture.

> **⚠️ Disclaimer**
>
> This is a personal project provided as-is for educational and personal use. No feature requests or support requests will be accepted. Feel free to fork and modify for your own needs.

**Features**:
- OpenAI-compatible API support
- MCP integration
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

Providers define AI model endpoints (OpenAI-compatible or Anthropic APIs):

```yaml
providers:
  openrouter:
    type: "openai"  # or "anthropic" defaults to "openai"
    api_base: "https://openrouter.ai/api/v1"
    api_key: "${OPENROUTER_API_KEY}"
    verify_ssl: true
    model_filter:
      conditions:
        - field: "id"
          contains: ":free"  # Filter for free models
        - field: "id"
          excludes: "beta"  # Exclude beta models

  custom_provider:
    type: "openai"
    api_base: "https://your-api.example.com/v1"
    api_key: "${YOUR_API_KEY}"
    basic_auth_token: "${BASIC_AUTH_TOKEN}"
    model_ids:  # Explicit model list (alternative to model_filter)
      - "gpt-4"
      - "gpt-3.5-turbo"

  anthropic:
    type: "anthropic"
    api_key: "${ANTHROPIC_API_KEY}"
    model_ids:
      - "claude-3-5-sonnet-20241022"
      - "claude-3-5-haiku-20241022"
```

**Configuration options:**
- `type`: Provider type - `"openai"` (default) or `"anthropic"`
- `api_base`: Base URL for the API endpoint (OpenAI-compatible providers only)
- `api_key`: API authentication key (supports environment variables)
- `basic_auth_token`: Optional basic auth token
- `verify_ssl`: Enable/disable SSL verification (default: true)
- `model_ids`: Explicit list of model IDs to use (alternative to dynamic discovery)
- `model_filter`: Dynamic model filtering with conditions:
  - `field`: JSON path to field (e.g., "id", "architecture.modality")
  - `contains`: Include models where field contains this substring
  - `excludes`: Exclude models where field contains this substring
  - `equals`: Include models where field exactly matches this value

### MCP (Model Context Protocol) Configuration

MCP servers provide tools and capabilities to chatbots:

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
  tools_dir: "tools"  # Directory for tool plugins
  skills_dir: "skills"  # Directory for skill plugins
```

### Default Chat Configuration

Configure default settings for new chats:

```yaml
default_chat:
  provider_id: "openrouter"
  model_id: "anthropic/claude-3.5-sonnet"
  system_prompt: "You are a helpful AI assistant."
  tool_servers: ["web_tools", "time"]  # Default tools available
  max_iterations: 5
  temperature: 0.7
  max_tokens: 4000
```

### Transcription Configuration

Configure audio transcription service (optional):

```yaml
transcription:
  model: "whisper-1"
  base_url: "https://api.openai.com/v1"
  api_key: "${OPENAI_API_KEY}"
```

### Additional Configuration Options

```yaml
history_db_path: "agentkit.db"  # SQLite database for conversation history
uploads_dir: "uploads"  # Directory for uploaded files
data_dir: "data"  # Directory for tool data storage
github_token: "${GITHUB_TOKEN}"  # Optional GitHub API token
```

## Available Tools

AgentKit provides tools from multiple sources that chatbots can use:

### Built-in Tools

**WebTools** (`web_tools`) - Always available:
- `fetch_page`: Fetch and convert web pages to markdown
- `fetch_multiple_pages`: Fetch multiple URLs concurrently
- `web_search`: DuckDuckGo web search

### MCP Tools

Configure any MCP-compatible server in your `config.yaml` under the `mcps:` section. Tools are automatically discovered and made available.

### Custom Tool Plugins

Tool plugins located in `plugins/tools/` are automatically loaded. Examples:
- `notes`: Manage notes in a Gitea repository
- `website_summarizer`: Summarize and compare website content

## Plugins

AgentKit has a flexible plugin architecture supporting three types of plugins:

### 1. Chatbot Plugins

Chatbot plugins allow you to create custom chat interfaces with specific configurations. They inherit from `ChatbotPlugin` and provide a consistent initialization pattern.

**Creating a Chatbot Plugin:**

1. Create a Python file in the `chatbots/` directory (e.g., `chatbots/my_bot.py`)
2. Inherit from `ChatbotPlugin` and implement the `configure()` method:

```python
from agentkit.chatbots.plugin import ChatbotPlugin, ChatbotConfig

class MyCustomBot(ChatbotPlugin):
    def configure(self) -> ChatbotConfig:
        provider = self.provider_registry.get_provider("openrouter")

        return ChatbotConfig(
            provider=provider,
            model_id="openai/gpt-4",
            system_prompt="You are a helpful assistant.",
            tool_servers=["web_tools", "time"],  # Tool servers to use
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

### 2. Tool Plugins

Tool plugins extend AgentKit with custom capabilities. They inherit from `ToolSetHandler` and use decorators to define individual tools.

**Creating a Tool Plugin:**

1. Create a Python file in the `plugins/tools/` directory (e.g., `plugins/tools/my_tools.py`)
2. Inherit from `ToolSetHandler` and define tools using the `@tool` decorator:

```python
from agentkit.tools.toolset_handler import ToolSetHandler, tool

class MyTools(ToolSetHandler):
    def __init__(self, tool_manager, server_name: str):
        super().__init__(tool_manager, server_name)
        # Initialize any resources here

    @tool(
        description="Calculate the sum of two numbers",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["a", "b"]
        }
    )
    async def calculate_sum(self, a: float, b: float) -> dict:
        """Calculate the sum of two numbers."""
        result = a + b
        return {
            "success": True,
            "result": result,
            "message": f"The sum of {a} and {b} is {result}"
        }
```

**Key Features:**
- Automatic discovery: Tools are loaded from `tools_dir` at startup
- JSON Schema parameters: Use standard JSON Schema for input validation
- Async support: Tools can be async or sync
- Cross-tool communication: Use `self.call_other_tool()` to invoke other tools
- Persistent storage: Each tool server gets its own data directory
- Tool naming: Tools are exposed as `{server_name}__{tool_name}`

**Advanced Example:**

```python
from agentkit.tools.toolset_handler import ToolSetHandler, tool

class AdvancedTools(ToolSetHandler):
    @tool(
        description="Fetch and process data from an API",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "API endpoint URL"},
                "process": {"type": "boolean", "description": "Whether to process the data"}
            },
            "required": ["url"]
        }
    )
    async def fetch_and_process(self, url: str, process: bool = False) -> dict:
        # Use built-in web tools
        result = await self.call_other_tool("web_tools__fetch_page", {"url": url})

        if process and result.get("success"):
            # Process the fetched content
            content = result.get("content", "")
            processed = content.upper()  # Example processing

            return {
                "success": True,
                "data": processed,
                "message": "Data fetched and processed"
            }

        return result
```

### 3. Skill Plugins

Skill plugins provide reusable knowledge and prompt templates that can be injected into conversations.

**Creating a Skill Plugin:**

1. Create a directory in `plugins/skills/` (e.g., `plugins/skills/code_review/`)
2. Add a `SKILL.md` file with the skill content:

```markdown
# Code Review Assistant

You are an expert code reviewer. When reviewing code:

1. Check for security vulnerabilities
2. Identify potential bugs
3. Suggest performance improvements
4. Verify code style and best practices
5. Provide constructive feedback

Be thorough but concise in your reviews.
```

**Key Features:**
- Automatic discovery: Skills are loaded from `skills_dir`
- Markdown format: Skills are written in Markdown
- Injectable: Skills can be activated in conversations to modify chatbot behavior

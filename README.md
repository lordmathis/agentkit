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

   For multi-platform builds (amd64 and arm64):
    ```bash
    docker buildx build --platform linux/amd64,linux/arm64 -t agentkit --load .
    ```

   For arm64 only:
    ```bash
    docker buildx build --platform linux/arm64 -t agentkit --load .
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
- `model_ids`: Explicit list of model IDs to use (alternative to dynamic discovery)
- `model_filter`: Dynamic model filtering with conditions:
  - `field`: JSON path to field (e.g., "id", "architecture.modality")
  - `contains`: Include models where field contains this substring
  - `excludes`: Exclude models where field contains this substring
  - `equals`: Include models where field exactly matches this value

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
  agents_dir: "agents"  # Directory for agent plugins
  tools_dir: "tools"  # Directory for tool plugins
  skills_dir: "skills"  # Directory for skill plugins
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
repo_browser:  # Optional repository browser configuration
  type: "github"
  token: "${GITHUB_TOKEN}"
```

## Available Tools

AgentKit provides tools from multiple sources that agents can use:

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

Chatbot plugins allow you to create custom chat interfaces with specific configurations. They inherit from `ReActAgentPlugin` and provide a declarative configuration pattern.

**Creating a Chatbot Plugin:**

1. Create a Python file in the `agents/` directory (e.g., `agents/my_bot.py`)
2. Inherit from `ReActAgentPlugin` and configure via class attributes:

```python
from agentkit.agents import ReActAgentPlugin

class MyCustomBot(ReActAgentPlugin):
    default = True
    name = "my-bot"
    provider_id = "openrouter"
    model_id = "openai/gpt-4"
    system_prompt = "You are a helpful assistant."
    tool_servers = ["web_tools", "time"]
    max_iterations = 5
    temperature = 0.7
    max_tokens = 2000
```

**For custom behavior, override `post_init()` and/or `_run()`:**

```python
from agentkit.agents import ReActAgentPlugin

class StructuredBot(ReActAgentPlugin):
    name = "structured-bot"
    provider_id = "anthropic"
    model_id = "claude-sonnet-4-6"

    def post_init(self) -> None:
        # Called after dependencies are injected
        self._parser = MyOutputParser()

    async def _run(self, message: str) -> dict:
        response = await super()._run(message)
        return self._parser.parse(response)
```

**Key Features:**
- Automatic discovery: Agents are automatically loaded from the `agents_dir`
- Provider integration: Access to all configured providers
- Tool access: Can specify which MCP/agent tools to use
- `post_init()` hook: Custom setup after dependency injection
- `_run()` override: Custom agent logic with full access to injected deps

### 2. Tool Plugins

Tool plugins extend AgentKit with custom capabilities. They inherit from `ToolSetHandler` and use decorators to define individual tools.

**Creating a Tool Plugin:**

1. Create a Python file in the `plugins/tools/` directory (e.g., `plugins/tools/my_tools.py`)
2. Inherit from `ToolSetHandler`, set `server_name` as a class attribute, and define tools using the `@tool` decorator:

```python
from agentkit.tools.toolset_handler import ToolSetHandler, tool

class MyTools(ToolSetHandler):
    server_name = "my_tools"  # Required: identifies this tool server

    def __init__(self):
        super().__init__()
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
- Cross-tool communication: Use `self.call_other_tool("{server}__{tool}", args)` to invoke other tools
- Persistent storage: Each tool server gets its own data directory
- Tool naming: Tools are exposed as `{server_name}__{tool_name}`

**Advanced Example:**

```python
from agentkit.tools.toolset_handler import ToolSetHandler, tool

class AdvancedTools(ToolSetHandler):
    server_name = "advanced"

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
        # Use built-in web tools - note the full tool name format
        result = await self.call_other_tool("web_tools__fetch_page", {"url": url})

        if process and result.get("success"):
            content = result.get("content", "")
            processed = content.upper()

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

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/tools")
async def list_tools(request: Request):
    """
    List all available tool servers and their tools.
    """
    tool_manager = request.app.state.tool_manager

    tool_servers = []
    server_names = await tool_manager.list_tool_servers()

    for server_name in server_names:
        try:
            tools = await tool_manager.list_tools(server_name)

            # Convert tools to dict format
            tool_list = []
            for tool in tools:
                if hasattr(tool, 'parameters'):
                    tool_dict = {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                else:
                    tool_dict = {
                        "name": getattr(tool, 'name', 'unknown'),
                        "description": getattr(tool, 'description', ''),
                        "parameters": {}
                    }
                tool_list.append(tool_dict)

            tool_servers.append({
                "name": server_name,
                "tools": tool_list
            })
        except Exception as e:
            print(f"Warning: Could not list tools from server {server_name}: {e}")
            continue

    return {
        "tool_servers": tool_servers
    }

#!/usr/bin/env python3
"""
AgentKit CLI Client

A command-line interface for interacting with the AgentKit REST API.
Supports model selection, system prompts, tool servers, and chat functionality.
"""

import argparse
import asyncio
import json
import sys
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import httpx
from prompt_toolkit import PromptSession
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm


class AgentKitClient:
    """Client for communicating with AgentKit REST API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=300.0)
        self.console = Console()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """Check if the server is running."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available models."""
        response = await self.client.get(f"{self.base_url}/api/models")
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    async def list_providers(self) -> List[Dict[str, Any]]:
        """List all providers."""
        response = await self.client.get(f"{self.base_url}/api/providers")
        response.raise_for_status()
        data = response.json()
        return data.get("providers", [])

    async def list_tool_servers(self) -> List[Dict[str, Any]]:
        """List all available tool servers."""
        response = await self.client.get(f"{self.base_url}/api/tools")
        response.raise_for_status()
        data = response.json()
        return data.get("tool_servers", [])

    async def list_chats(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent chats."""
        response = await self.client.get(
            f"{self.base_url}/api/chats", params={"limit": limit}
        )
        response.raise_for_status()
        data = response.json()
        return data.get("chats", [])

    async def create_chat(
        self,
        title: str = "Untitled Chat",
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tool_servers: Optional[List[str]] = None,
        model_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new chat."""
        if not model:
            raise ValueError("Model is required to create a chat")
        
        payload = {
            "title": title,
            "config": {
                "model": model,
                "system_prompt": system_prompt,
                "tool_servers": tool_servers or [],
                "model_params": model_params or {}
            }
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/chats", json=payload
        )
        response.raise_for_status()
        return response.json()

    async def get_chat(self, chat_id: str) -> Dict[str, Any]:
        """Get chat details and message history."""
        response = await self.client.get(f"{self.base_url}/api/chats/{chat_id}")
        response.raise_for_status()
        return response.json()

    async def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat."""
        response = await self.client.delete(f"{self.base_url}/api/chats/{chat_id}")
        response.raise_for_status()
        return response.json().get("success", False)

    async def send_message(
        self,
        chat_id: str,
        message: str,
        model: str,
        system_prompt: Optional[str] = None,
        tool_servers: Optional[List[str]] = None,
        model_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a message to the chat."""
        config = {
            "model": model,
            "system_prompt": system_prompt,
            "tool_servers": tool_servers or [],
            "model_params": model_params or {},
        }

        response = await self.client.post(
            f"{self.base_url}/api/chats/{chat_id}/messages",
            json={"message": message, "config": config, "stream": False},
        )
        response.raise_for_status()
        return response.json()


class ChatSession:
    """Interactive chat session manager."""

    def __init__(self, client: AgentKitClient):
        self.client = client
        self.console = Console()
        self.chat_id: Optional[str] = None
        self.model: Optional[str] = None
        self.system_prompt: Optional[str] = None
        self.tool_servers: List[str] = []
        self.model_params: Dict[str, Any] = {
            "temperature": 0.7,
            "max_tokens": 2000,
            "max_iterations": 5,
        }

    def display_welcome(self):
        """Display welcome message."""
        self.console.print(
            Panel.fit(
                "[bold cyan]AgentKit CLI Client[/bold cyan]\n"
                "Type your messages to chat with the AI.\n"
                "Commands: /help, /config, /models, /tools, /new, /list, /load, /quit",
                border_style="cyan",
            )
        )

    def display_config(self):
        """Display current configuration."""
        config_table = Table(title="Current Configuration", show_header=False)
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="yellow")

        config_table.add_row("Chat ID", self.chat_id or "Not started")
        config_table.add_row("Model", self.model or "Not selected")
        config_table.add_row("System Prompt", self.system_prompt or "None")
        config_table.add_row(
            "Tool Servers", ", ".join(self.tool_servers) if self.tool_servers else "None"
        )
        config_table.add_row("Temperature", str(self.model_params.get("temperature", 0.7)))
        config_table.add_row("Max Tokens", str(self.model_params.get("max_tokens", 2000)))
        config_table.add_row(
            "Max Iterations", str(self.model_params.get("max_iterations", 5))
        )

        self.console.print(config_table)

    async def select_model(self):
        """Interactive model selection."""
        try:
            models = await self.client.list_models()

            if not models:
                self.console.print("[red]No models available[/red]")
                return

            # Display models
            table = Table(title="Available Models")
            table.add_column("#", style="cyan")
            table.add_column("Model ID", style="yellow")
            table.add_column("Owned By", style="green")

            for idx, model in enumerate(models, 1):
                table.add_row(
                    str(idx), model.get("id", ""), model.get("owned_by", "")
                )

            self.console.print(table)

            # Get selection
            selection = Prompt.ask(
                "Select a model by number",
                default=str(1) if models else "",
                show_default=True,
            )

            try:
                idx = int(selection) - 1
                if 0 <= idx < len(models):
                    self.model = models[idx]["id"]
                    self.console.print(f"[green]Selected model: {self.model}[/green]")
                else:
                    self.console.print("[red]Invalid selection[/red]")
            except ValueError:
                self.console.print("[red]Invalid input[/red]")

        except Exception as e:
            self.console.print(f"[red]Error listing models: {e}[/red]")

    async def configure_tools(self):
        """Interactive tool server configuration."""
        try:
            tool_servers = await self.client.list_tool_servers()

            if not tool_servers:
                self.console.print("[yellow]No tool servers available[/yellow]")
                return

            # Display tool servers
            table = Table(title="Available Tool Servers")
            table.add_column("#", style="cyan")
            table.add_column("Name", style="yellow")
            table.add_column("Type", style="green")
            table.add_column("Tools Count", style="magenta")

            for idx, server in enumerate(tool_servers, 1):
                table.add_row(
                    str(idx),
                    server.get("name", ""),
                    server.get("type", ""),
                    str(len(server.get("tools", []))),
                )

            self.console.print(table)

            # Get selection (comma-separated numbers)
            selection = Prompt.ask(
                "Select tool servers by number (comma-separated, or 'none' to clear)",
                default="none",
            )

            if selection.lower() == "none":
                self.tool_servers = []
                self.console.print("[green]Tool servers cleared[/green]")
            else:
                try:
                    indices = [int(s.strip()) - 1 for s in selection.split(",")]
                    selected_servers = []
                    for idx in indices:
                        if 0 <= idx < len(tool_servers):
                            selected_servers.append(tool_servers[idx]["name"])
                        else:
                            self.console.print(f"[yellow]Skipping invalid index: {idx + 1}[/yellow]")

                    self.tool_servers = selected_servers
                    self.console.print(
                        f"[green]Selected tool servers: {', '.join(self.tool_servers)}[/green]"
                    )
                except ValueError:
                    self.console.print("[red]Invalid input[/red]")

        except Exception as e:
            self.console.print(f"[red]Error listing tool servers: {e}[/red]")

    def set_system_prompt(self):
        """Set system prompt."""
        self.console.print("[cyan]Enter system prompt (or empty to clear):[/cyan]")
        prompt = Prompt.ask("System prompt", default="")

        if prompt:
            self.system_prompt = prompt
            self.console.print("[green]System prompt set[/green]")
        else:
            self.system_prompt = None
            self.console.print("[green]System prompt cleared[/green]")

    def configure_model_params(self):
        """Configure model parameters."""
        self.console.print("[cyan]Configure Model Parameters[/cyan]")

        temp = Prompt.ask(
            "Temperature (0.0-2.0)",
            default=str(self.model_params.get("temperature", 0.7)),
        )
        try:
            self.model_params["temperature"] = float(temp)
        except ValueError:
            self.console.print("[yellow]Invalid temperature, keeping current value[/yellow]")

        max_tokens = Prompt.ask(
            "Max tokens", default=str(self.model_params.get("max_tokens", 2000))
        )
        try:
            self.model_params["max_tokens"] = int(max_tokens)
        except ValueError:
            self.console.print("[yellow]Invalid max_tokens, keeping current value[/yellow]")

        max_iter = Prompt.ask(
            "Max iterations", default=str(self.model_params.get("max_iterations", 5))
        )
        try:
            self.model_params["max_iterations"] = int(max_iter)
        except ValueError:
            self.console.print(
                "[yellow]Invalid max_iterations, keeping current value[/yellow]"
            )

        self.console.print("[green]Model parameters updated[/green]")

    async def create_new_chat(self):
        """Create a new chat session."""
        # Check if model is selected
        if not self.model:
            self.console.print("[yellow]No model selected. Please select a model first.[/yellow]")
            await self.select_model()
            if not self.model:
                self.console.print("[red]Cannot create chat without a model[/red]")
                return

        title = Prompt.ask("Chat title", default="New Chat")

        try:
            chat = await self.client.create_chat(
                title=title,
                model=self.model,
                system_prompt=self.system_prompt,
                tool_servers=self.tool_servers,
                model_params=self.model_params
            )
            self.chat_id = chat["id"]
            self.console.print(f"[green]Created new chat: {self.chat_id}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error creating chat: {e}[/red]")

    async def list_recent_chats(self):
        """List recent chats."""
        try:
            chats = await self.client.list_chats(limit=20)

            if not chats:
                self.console.print("[yellow]No chats found[/yellow]")
                return

            table = Table(title="Recent Chats")
            table.add_column("#", style="cyan")
            table.add_column("ID", style="yellow")
            table.add_column("Title", style="green")
            table.add_column("Model", style="magenta")
            table.add_column("Updated", style="blue")

            for idx, chat in enumerate(chats, 1):
                table.add_row(
                    str(idx),
                    chat.get("id", "")[:8] + "...",
                    chat.get("title", ""),
                    chat.get("model", "N/A"),
                    chat.get("updated_at", "")[:19],
                )

            self.console.print(table)

        except Exception as e:
            self.console.print(f"[red]Error listing chats: {e}[/red]")

    async def load_chat(self):
        """Load an existing chat."""
        try:
            chats = await self.client.list_chats(limit=20)

            if not chats:
                self.console.print("[yellow]No chats found[/yellow]")
                return

            # Display chats
            table = Table(title="Recent Chats")
            table.add_column("#", style="cyan")
            table.add_column("ID", style="yellow")
            table.add_column("Title", style="green")
            table.add_column("Model", style="magenta")

            for idx, chat in enumerate(chats, 1):
                table.add_row(
                    str(idx),
                    chat.get("id", "")[:8] + "...",
                    chat.get("title", ""),
                    chat.get("model", "N/A"),
                )

            self.console.print(table)

            # Get selection
            selection = Prompt.ask("Select a chat by number")

            try:
                idx = int(selection) - 1
                if 0 <= idx < len(chats):
                    chat_id = chats[idx]["id"]
                    chat_details = await self.client.get_chat(chat_id)

                    self.chat_id = chat_id
                    self.model = chat_details.get("model")
                    self.system_prompt = chat_details.get("system_prompt")
                    self.tool_servers = chat_details.get("tool_servers") or []

                    # Load model params if available
                    if chat_details.get("model_params"):
                        self.model_params.update(chat_details["model_params"])

                    self.console.print(f"[green]Loaded chat: {chat_details.get('title')}[/green]")

                    # Display message history
                    messages = chat_details.get("messages", [])
                    if messages:
                        self.console.print("\n[cyan]Message History:[/cyan]")
                        for msg in messages:
                            role = msg.get("role", "")
                            content = msg.get("content", "")
                            if role == "user":
                                self.console.print(f"[green]You:[/green] {content}")
                            elif role == "assistant":
                                self.console.print(Panel(Markdown(content), title="Assistant", border_style="blue"))
                        self.console.print()

                else:
                    self.console.print("[red]Invalid selection[/red]")
            except ValueError:
                self.console.print("[red]Invalid input[/red]")

        except Exception as e:
            self.console.print(f"[red]Error loading chat: {e}[/red]")

    async def send_chat_message(self, message: str):
        """Send a message in the current chat."""
        if not self.chat_id:
            self.console.print(
                "[yellow]No active chat. Use /new to create one or /load to load an existing chat.[/yellow]"
            )
            return

        if not self.model:
            self.console.print(
                "[yellow]No model selected. Use /models to select one.[/yellow]"
            )
            return

        try:
            self.console.print("[dim]Sending message...[/dim]")

            response = await self.client.send_message(
                chat_id=self.chat_id,
                message=message,
                model=self.model,
                system_prompt=self.system_prompt,
                tool_servers=self.tool_servers,
                model_params=self.model_params,
            )

            # Display assistant response (OpenAI format)
            choices = response.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                if content:
                    self.console.print(
                        Panel(Markdown(content), title="Assistant", border_style="blue")
                    )
                else:
                    self.console.print("[yellow]No response from assistant[/yellow]")
            else:
                self.console.print("[yellow]No response from assistant[/yellow]")

        except httpx.HTTPStatusError as e:
            self.console.print(f"[red]HTTP Error {e.response.status_code}: {e.response.text}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error sending message: {e}[/red]")

    def display_help(self):
        """Display help message."""
        help_text = """
        [bold cyan]Available Commands:[/bold cyan]
        
        [yellow]/help[/yellow]         - Show this help message
        [yellow]/config[/yellow]       - Show current configuration
        [yellow]/models[/yellow]       - Select a model
        [yellow]/tools[/yellow]        - Configure tool servers
        [yellow]/prompt[/yellow]       - Set system prompt
        [yellow]/params[/yellow]       - Configure model parameters (temperature, max_tokens, etc.)
        [yellow]/new[/yellow]          - Create a new chat
        [yellow]/list[/yellow]         - List recent chats
        [yellow]/load[/yellow]         - Load an existing chat
        [yellow]/quit[/yellow] or [yellow]/exit[/yellow] - Exit the CLI
        
        Type any other text to send a message to the AI.
        """
        self.console.print(Panel(help_text, border_style="cyan"))

    async def run(self):
        """Run the interactive chat session."""
        self.display_welcome()

        # Create prompt session
        session = PromptSession()

        while True:
            try:
                # Get user input
                user_input = await session.prompt_async("You: ")

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    command = user_input.strip().lower()

                    if command in ["/quit", "/exit"]:
                        self.console.print("[cyan]Goodbye![/cyan]")
                        break
                    elif command == "/help":
                        self.display_help()
                    elif command == "/config":
                        self.display_config()
                    elif command == "/models":
                        await self.select_model()
                    elif command == "/tools":
                        await self.configure_tools()
                    elif command == "/prompt":
                        self.set_system_prompt()
                    elif command == "/params":
                        self.configure_model_params()
                    elif command == "/new":
                        await self.create_new_chat()
                    elif command == "/list":
                        await self.list_recent_chats()
                    elif command == "/load":
                        await self.load_chat()
                    else:
                        self.console.print(f"[red]Unknown command: {command}[/red]")
                        self.console.print("[yellow]Type /help for available commands[/yellow]")
                else:
                    # Send message
                    await self.send_chat_message(user_input)

            except EOFError:
                self.console.print("\n[cyan]Goodbye![/cyan]")
                break


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AgentKit CLI Client - Interactive chat with AI agents"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the AgentKit server (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--model",
        help="Model to use (skips model selection)",
    )
    parser.add_argument(
        "--system-prompt",
        help="System prompt to use",
    )
    parser.add_argument(
        "--tools",
        help="Comma-separated list of tool server names",
    )

    args = parser.parse_args()

    # Create client
    client = AgentKitClient(base_url=args.url)

    try:
        # Check server health
        console = Console()
        console.print("[cyan]Connecting to AgentKit server...[/cyan]")

        if not await client.health_check():
            console.print(f"[red]Error: Cannot connect to server at {args.url}[/red]")
            console.print("[yellow]Make sure the server is running[/yellow]")
            return 1

        console.print("[green]Connected successfully![/green]\n")

        # Create chat session
        session = ChatSession(client)

        # Apply command-line arguments
        if args.model:
            session.model = args.model
            console.print(f"[green]Using model: {args.model}[/green]")

        if args.system_prompt:
            session.system_prompt = args.system_prompt
            console.print("[green]System prompt set from command line[/green]")

        if args.tools:
            session.tool_servers = [t.strip() for t in args.tools.split(",")]
            console.print(
                f"[green]Using tool servers: {', '.join(session.tool_servers)}[/green]"
            )

        # Run interactive session
        await session.run()

    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1
    finally:
        await client.close()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

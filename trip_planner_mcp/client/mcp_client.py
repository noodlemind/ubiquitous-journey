#!/usr/bin/env python3
"""
MCP Client - CLI entry point for the Trip Planner
"""

import typer
import json
from typing import Optional
from pathlib import Path
import sys
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from mcp_server.server import MCPServer
from mcp_server.schema import MCPRequest

app = typer.Typer(help="Trip Planner MCP Demo - Natural language travel assistant")
console = Console()


def format_response_output(response_json: str, verbose: bool = False) -> None:
    """Format and display the response in a user-friendly way"""
    try:
        response = json.loads(response_json)
        
        if response.get("status") == "error":
            console.print(f"[red]Error: {response.get('error', 'Unknown error')}[/red]")
            return
        
        # Show intent if verbose
        if verbose and response.get("intent"):
            console.print(f"\n[blue]Intent: {response['intent']}[/blue]")
        
        # Show natural language response
        if response.get("natural"):
            console.print(Panel(
                response["natural"],
                title="🧠 Trip Planner Response",
                border_style="green"
            ))
        
        # Show raw data if verbose
        if verbose and response.get("data"):
            console.print("\n[yellow]Raw Data:[/yellow]")
            syntax = Syntax(
                json.dumps(response["data"], indent=2),
                "json",
                theme="monokai",
                line_numbers=False
            )
            console.print(syntax)
            
    except json.JSONDecodeError:
        console.print(f"[red]Error parsing response[/red]")
        console.print(response_json)


@app.command()
def query(
    user_query: str = typer.Argument(..., help="Natural language query about travel"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output including classifier results and raw data"),
    model: str = typer.Option("llama3", "--model", "-m", help="Ollama model to use")
):
    """
    Send a natural language query to the Trip Planner
    
    Examples:
        python mcp_client.py "weather in Kyoto"
        python mcp_client.py "3-day Kyoto itinerary" --verbose
        python mcp_client.py "best ramen in Kyoto" -v
    """
    # Create server instance
    server = MCPServer(ollama_model=model)
    
    # Create request
    request = MCPRequest(
        task="nl_query",
        query=user_query,
        verbose=verbose
    )
    
    if verbose:
        console.print(f"\n[cyan]Query: {user_query}[/cyan]")
        console.print(f"[cyan]Model: {model}[/cyan]")
    
    # Process request
    with console.status("[bold green]Processing query..."):
        response_json = server.process_json_request(request.model_dump_json())
    
    # Display response
    format_response_output(response_json, verbose)


@app.command()
def test():
    """Run a quick test to verify the system is working"""
    test_queries = [
        "weather in Kyoto",
        "top attractions in Kyoto",
        "best ramen restaurants in Kyoto",
        "2-day Kyoto itinerary"
    ]
    
    server = MCPServer()
    
    for query in test_queries:
        console.print(f"\n[bold]Testing: {query}[/bold]")
        request = MCPRequest(task="nl_query", query=query, verbose=False)
        
        try:
            response_json = server.process_json_request(request.model_dump_json())
            response = json.loads(response_json)
            
            if response.get("status") == "success":
                console.print("[green]✓ Success[/green]")
            else:
                console.print(f"[red]✗ Failed: {response.get('error')}[/red]")
        except Exception as e:
            console.print(f"[red]✗ Exception: {str(e)}[/red]")


@app.command()
def info():
    """Show information about the Trip Planner MCP Demo"""
    info_text = """
    🧠 Trip Planner MCP Demo
    
    A self-contained demo showing how MCP servers, agents, tools, and LLMs work together.
    
    Supported intents:
    • weather_lookup - Get weather information for a city
    • hotspots_list - List top attractions in a city
    • food_reco - Get restaurant recommendations
    • trip_plan - Create multi-day trip itineraries
    
    Example queries:
    • "weather in Kyoto"
    • "top temples in Kyoto"
    • "best ramen in Tokyo"
    • "3-day Kyoto itinerary"
    
    Requirements:
    • Ollama running locally (ollama run llama3)
    • Python packages: pydantic, typer, requests, rich
    """
    console.print(Panel(info_text, title="About", border_style="blue"))


@app.command()
def interactive(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    model: str = typer.Option("llama3", "--model", "-m", help="Ollama model to use")
):
    """
    Run the Trip Planner in interactive mode
    
    This is the default mode - just run:
        python mcp_client.py
    """
    console.print(Panel(
        "🧠 Welcome to Trip Planner MCP Demo!\n"
        "Ask me about weather, attractions, restaurants, or trip planning.\n"
        "Type 'exit' or 'quit' to leave.",
        title="Trip Planner",
        border_style="blue"
    ))
    
    # Create server instance
    server = MCPServer(ollama_model=model)
    
    while True:
        try:
            # Get user input
            user_query = Prompt.ask("\n[cyan]Your query[/cyan]")
            
            # Check for exit commands
            if user_query.lower() in ['exit', 'quit', 'q']:
                console.print("[yellow]Goodbye! Safe travels! 👋[/yellow]")
                break
            
            # Skip empty queries
            if not user_query.strip():
                continue
            
            # Create request
            request = MCPRequest(
                task="nl_query",
                query=user_query,
                verbose=verbose
            )
            
            # Process request
            with console.status("[bold green]Thinking..."):
                response_json = server.process_json_request(request.model_dump_json())
            
            # Display response
            format_response_output(response_json, verbose)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Goodbye! 👋[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


# Make interactive mode the default when no command is specified
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Trip Planner MCP Demo - Natural language travel assistant
    
    By default, runs in interactive mode. Use subcommands for other modes.
    """
    if ctx.invoked_subcommand is None:
        # No subcommand specified, run interactive mode with defaults
        interactive(verbose=False, model="llama3")


if __name__ == "__main__":
    app()
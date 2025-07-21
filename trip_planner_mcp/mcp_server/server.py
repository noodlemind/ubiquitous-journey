import json
from typing import Optional
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from mcp_server.schema import MCPRequest, MCPResponse
from agent.trip_planner_agent import TripPlannerAgent


class MCPServer:
    """MCP Server that handles requests and coordinates with the agent"""
    
    def __init__(self, ollama_model: str = "llama3"):
        self.agent = None
        self.ollama_model = ollama_model
    
    def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Handle an MCP request and return an MCP response
        """
        try:
            # Validate request object
            if not request:
                return MCPResponse(
                    status="error",
                    error="Empty request received"
                )
            
            # Validate task type
            if not hasattr(request, 'task') or request.task != "nl_query":
                task_name = getattr(request, 'task', 'unknown')
                return MCPResponse(
                    status="error",
                    error=f"Unknown task type: {task_name}. Only 'nl_query' is supported.",
                    metadata=getattr(request, 'metadata', None)
                )
            
            # Validate query
            if not hasattr(request, 'query') or not request.query:
                return MCPResponse(
                    status="error",
                    error="Query is required for nl_query task",
                    metadata=getattr(request, 'metadata', None)
                )
            
            # Validate query length and content
            query = str(request.query).strip()
            if len(query) == 0:
                return MCPResponse(
                    status="error",
                    error="Query cannot be empty",
                    metadata=getattr(request, 'metadata', None)
                )
            
            if len(query) > 2000:  # Reasonable limit
                return MCPResponse(
                    status="error",
                    error="Query too long (max 2000 characters)",
                    metadata=getattr(request, 'metadata', None)
                )
            
            # Initialize agent with verbose flag from request
            verbose = getattr(request, 'verbose', False) or False
            try:
                if self.agent is None or self.agent.verbose != verbose:
                    self.agent = TripPlannerAgent(
                        ollama_model=self.ollama_model,
                        verbose=verbose
                    )
            except Exception as e:
                return MCPResponse(
                    status="error",
                    error=f"Failed to initialize agent: {str(e)}",
                    metadata=getattr(request, 'metadata', None)
                )
            
            # Process the query
            print(f"\n🔄 [MCP SERVER] Forwarding query to Agent: '{query}'")
            try:
                data, natural_response = self.agent.process_query(query)
                print(f"✅ [MCP SERVER] Agent completed processing")
            except Exception as e:
                return MCPResponse(
                    status="error",
                    error=f"Query processing failed: {str(e)}",
                    metadata=getattr(request, 'metadata', None)
                )
            
            # Validate response data
            if not isinstance(data, dict):
                return MCPResponse(
                    status="error",
                    error="Invalid response format from agent",
                    metadata=getattr(request, 'metadata', None)
                )
            
            # Check for errors
            if "error" in data:
                return MCPResponse(
                    status="error",
                    error=data.get("error", "Unknown error occurred"),
                    metadata=getattr(request, 'metadata', None)
                )
            
            # Validate natural response
            if not natural_response or not isinstance(natural_response, str):
                natural_response = "Response generated successfully but formatting failed."
            
            # Build successful response
            return MCPResponse(
                status="success",
                intent=data.get("intent"),
                data=data.get("data"),
                natural=natural_response,
                metadata=getattr(request, 'metadata', None)
            )
            
        except AttributeError as e:
            return MCPResponse(
                status="error",
                error=f"Invalid request format: {str(e)}",
                metadata=None
            )
        except Exception as e:
            return MCPResponse(
                status="error",
                error=f"Server error: {str(e)}",
                metadata=getattr(request, 'metadata', None) if hasattr(request, 'metadata') else None
            )
    
    def process_json_request(self, json_str: str) -> str:
        """
        Process a JSON string request and return JSON response
        """
        try:
            # Validate input
            if not json_str or not json_str.strip():
                error_response = MCPResponse(
                    status="error",
                    error="Empty JSON request"
                )
                return error_response.model_dump_json(indent=2)
            
            # Limit JSON size to prevent DoS
            if len(json_str) > 10000:  # 10KB limit
                error_response = MCPResponse(
                    status="error",
                    error="JSON request too large (max 10KB)"
                )
                return error_response.model_dump_json(indent=2)
            
            # Parse request
            try:
                request_data = json.loads(json_str.strip())
            except json.JSONDecodeError as e:
                error_response = MCPResponse(
                    status="error",
                    error=f"Invalid JSON format: {str(e)}"
                )
                return error_response.model_dump_json(indent=2)
            
            # Validate basic structure
            if not isinstance(request_data, dict):
                error_response = MCPResponse(
                    status="error",
                    error="Request must be a JSON object"
                )
                return error_response.model_dump_json(indent=2)
            
            # Create MCPRequest with validation
            try:
                request = MCPRequest(**request_data)
            except TypeError as e:
                error_response = MCPResponse(
                    status="error",
                    error=f"Invalid request format: {str(e)}"
                )
                return error_response.model_dump_json(indent=2)
            except Exception as e:
                error_response = MCPResponse(
                    status="error",
                    error=f"Request validation failed: {str(e)}"
                )
                return error_response.model_dump_json(indent=2)
            
            # Handle request
            try:
                response = self.handle_request(request)
            except Exception as e:
                error_response = MCPResponse(
                    status="error",
                    error=f"Request handling failed: {str(e)}"
                )
                return error_response.model_dump_json(indent=2)
            
            # Return JSON response
            try:
                return response.model_dump_json(indent=2, exclude_none=True)
            except Exception as e:
                error_response = MCPResponse(
                    status="error",
                    error=f"Response serialization failed: {str(e)}"
                )
                return error_response.model_dump_json(indent=2)
            
        except Exception as e:
            # Catch-all for any unexpected errors
            try:
                error_response = MCPResponse(
                    status="error",
                    error=f"Unexpected error processing request: {str(e)}"
                )
                return error_response.model_dump_json(indent=2)
            except:
                # If even error response fails, return basic JSON
                return '{"status": "error", "error": "Critical error - unable to process request"}'


# Simple test/demo if run directly
if __name__ == "__main__":
    server = MCPServer()
    
    # Test request
    test_request = MCPRequest(
        task="nl_query",
        query="weather in Kyoto",
        verbose=True
    )
    
    response = server.handle_request(test_request)
    print(response.model_dump_json(indent=2))
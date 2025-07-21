import pytest
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from mcp_server.server import MCPServer
from mcp_server.schema import MCPRequest, MCPResponse


class TestEndToEnd:
    """End-to-end tests for the Trip Planner MCP system"""
    
    @pytest.fixture
    def server(self):
        """Create a server instance for testing"""
        return MCPServer(ollama_model="llama3")
    
    def test_weather_lookup(self, server):
        """Test weather lookup functionality"""
        request = MCPRequest(
            task="nl_query",
            query="what's the weather in Kyoto?",
            verbose=False
        )
        
        response = server.handle_request(request)
        
        assert response.status == "success"
        assert response.intent == "weather_lookup"
        assert response.data is not None
        assert response.natural is not None
        assert "kyoto" in response.data.get("city", "").lower()
    
    def test_hotspots_list(self, server):
        """Test hotspot listing functionality"""
        request = MCPRequest(
            task="nl_query",
            query="show me top attractions in Kyoto",
            verbose=False
        )
        
        response = server.handle_request(request)
        
        assert response.status == "success"
        assert response.intent == "hotspots_list"
        assert response.data is not None
        assert "hotspots" in response.data
        assert len(response.data["hotspots"]) > 0
    
    def test_restaurant_recommendations(self, server):
        """Test restaurant recommendation functionality"""
        request = MCPRequest(
            task="nl_query",
            query="best ramen restaurants in Kyoto",
            verbose=False
        )
        
        response = server.handle_request(request)
        
        assert response.status == "success"
        assert response.intent == "food_reco"
        assert response.data is not None
        assert "restaurants" in response.data
    
    def test_trip_planning(self, server):
        """Test trip planning functionality"""
        request = MCPRequest(
            task="nl_query",
            query="plan a 3-day trip to Kyoto",
            verbose=False
        )
        
        response = server.handle_request(request)
        
        assert response.status == "success"
        assert response.intent == "trip_plan"
        assert response.data is not None
        assert all(key in response.data for key in ["weather", "hotspots", "restaurants"])
    
    def test_invalid_city(self, server):
        """Test handling of invalid city"""
        request = MCPRequest(
            task="nl_query",
            query="weather in Atlantis",
            verbose=False
        )
        
        response = server.handle_request(request)
        
        assert response.status == "error"
        assert response.error is not None
    
    def test_invalid_task(self, server):
        """Test handling of invalid task type"""
        request = MCPRequest(
            task="invalid_task",  # This will cause validation error
            query="test query",
            verbose=False
        )
        
        # This should raise a validation error
        with pytest.raises(ValueError):
            response = server.handle_request(request)
    
    def test_verbose_mode(self, server):
        """Test verbose mode doesn't break functionality"""
        request = MCPRequest(
            task="nl_query",
            query="weather in Kyoto",
            verbose=True
        )
        
        response = server.handle_request(request)
        
        assert response.status == "success"
        assert response.intent == "weather_lookup"
    
    def test_json_request_processing(self, server):
        """Test JSON string request processing"""
        json_request = json.dumps({
            "task": "nl_query",
            "query": "weather in Tokyo",
            "verbose": False
        })
        
        response_json = server.process_json_request(json_request)
        response = json.loads(response_json)
        
        assert response["status"] == "success"
        assert "intent" in response
        assert "data" in response
    
    def test_malformed_json_request(self, server):
        """Test handling of malformed JSON"""
        malformed_json = "{'task': 'nl_query', 'query': 'test'}"  # Invalid JSON
        
        response_json = server.process_json_request(malformed_json)
        response = json.loads(response_json)
        
        assert response["status"] == "error"
        assert "Invalid JSON" in response["error"]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
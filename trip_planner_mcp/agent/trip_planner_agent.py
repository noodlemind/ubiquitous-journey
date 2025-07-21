import json
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from llm.ollama_connector import OllamaConnector
from tools.weather_tool import WeatherTool
from tools.hotspot_tool import HotspotTool
from tools.restaurant_tool import RestaurantTool


class TripPlannerAgent:
    """Agent that coordinates LLM reasoning and tool calls"""
    
    def __init__(self, ollama_model: str = "llama3", verbose: bool = False):
        self.llm = OllamaConnector(model=ollama_model)
        self.weather_tool = WeatherTool()
        self.hotspot_tool = HotspotTool()
        self.restaurant_tool = RestaurantTool()
        self.verbose = verbose
    
    def process_query(self, query: str) -> Tuple[Dict[str, Any], str]:
        """
        Process a natural language query using two-prompt cycle:
        1. Classify intent and extract parameters
        2. Call appropriate tools and format response
        
        Returns: (data_dict, natural_language_response)
        """
        # Input validation
        if not query or not query.strip():
            return {"error": "Empty query"}, "Please provide a query about travel, weather, or restaurants."
        
        # Sanitize query length to prevent excessive processing
        if len(query) > 1000:
            return {"error": "Query too long"}, "Please provide a shorter query (under 1000 characters)."
        
        try:
            print(f"\n🧠 [AGENT] Starting two-prompt cycle for: '{query.strip()}'")
            print(f"📝 [AGENT] Step 1: Calling LLM for intent classification...")
            
            # Step 1: Classify intent
            classification = self.llm.classify_intent(query.strip())
            
            # Handle LLM errors from classification
            if "error" in classification:
                return {"error": "Classification failed", "details": classification["error"]}, \
                       "I'm having trouble understanding your request. Please try rephrasing it."
            
            print(f"✅ [AGENT] LLM classified intent: {classification.get('intent', 'unknown')}")
            if classification.get('city'):
                print(f"🏙️  [AGENT] Extracted city: {classification.get('city')}")
            if classification.get('cuisine'):
                print(f"🍽️  [AGENT] Extracted cuisine: {classification.get('cuisine')}")
            if classification.get('days'):
                print(f"📅 [AGENT] Extracted days: {classification.get('days')}")
            
            if self.verbose:
                print(f"\n[VERBOSE CLASSIFIER OUTPUT]\n{json.dumps(classification, indent=2)}\n")
            
            intent = classification.get("intent", "unknown")
            city = classification.get("city") or ""  # Already normalized to lowercase in LLM connector
            days = classification.get("days")
            cuisine = classification.get("cuisine")
            
            # Validate days parameter
            if days is not None:
                try:
                    days = int(days)
                    if days <= 0 or days > 14:
                        days = 3  # Default fallback
                except (ValueError, TypeError):
                    days = 3  # Default fallback
            
            # Check if city is required but missing
            if intent in ["weather_lookup", "hotspots_list", "food_reco", "trip_plan"] and not city:
                return self._handle_missing_city(query, intent)
            
            print(f"🔧 [AGENT] Step 2: Executing handler for intent '{intent}'...")
            
            # Step 2: Execute based on intent
            if intent == "weather_lookup":
                return self._handle_weather(city)
            elif intent == "hotspots_list":
                return self._handle_hotspots(city)
            elif intent == "food_reco":
                return self._handle_restaurants(city, cuisine)
            elif intent == "trip_plan":
                return self._handle_trip_plan(city, days or 3)
            else:
                return self._handle_unknown(query)
                
        except Exception as e:
            error_msg = f"An unexpected error occurred while processing your query: {str(e)}"
            return {"error": "Processing error", "details": str(e)}, error_msg
    
    def _handle_weather(self, city: str) -> Tuple[Dict[str, Any], str]:
        """Handle weather lookup requests"""
        try:
            print(f"🛠️  [WEATHER TOOL] Fetching weather data for '{city}'...")
            weather_data = self.weather_tool.get_weather(city)
            
            if "error" not in weather_data:
                print(f"✅ [WEATHER TOOL] Successfully loaded weather data for {city}")
            else:
                print(f"❌ [WEATHER TOOL] Error: {weather_data.get('error')}")
            
            if self.verbose:
                print(f"[WEATHER TOOL OUTPUT]\n{json.dumps(weather_data, indent=2)}\n")
            
            if "error" in weather_data:
                return weather_data, weather_data["error"]
            
            # Format response
            print(f"📝 [AGENT] Calling LLM to format weather response...")
            natural_response = self.llm.format_response("weather_lookup", weather_data, city=city)
            print(f"✅ [AGENT] LLM completed weather response formatting")
            
            # Handle formatting errors
            if natural_response.startswith("Error:"):
                return {
                    "intent": "weather_lookup", 
                    "city": city, 
                    "error": "Formatting failed"
                }, f"I found weather data for {city} but couldn't format it properly."
            
            return {
                "intent": "weather_lookup",
                "city": city,
                "data": weather_data
            }, natural_response
            
        except Exception as e:
            error_msg = f"Failed to get weather for {city}: {str(e)}"
            return {"error": "Weather lookup failed", "city": city}, error_msg
    
    def _handle_hotspots(self, city: str) -> Tuple[Dict[str, Any], str]:
        """Handle hotspot listing requests"""
        try:
            hotspot_data = self.hotspot_tool.get_hotspots(city)
            
            if self.verbose:
                print(f"[HOTSPOT TOOL OUTPUT]\n{json.dumps(hotspot_data, indent=2)}\n")
            
            if "error" in hotspot_data:
                return hotspot_data, hotspot_data["error"]
            
            # Format response
            natural_response = self.llm.format_response("hotspots_list", hotspot_data, city=city)
            
            # Handle formatting errors
            if natural_response.startswith("Error:"):
                return {
                    "intent": "hotspots_list", 
                    "city": city, 
                    "error": "Formatting failed"
                }, f"I found attractions in {city} but couldn't format them properly."
            
            return {
                "intent": "hotspots_list",
                "city": city,
                "data": hotspot_data
            }, natural_response
            
        except Exception as e:
            error_msg = f"Failed to get attractions for {city}: {str(e)}"
            return {"error": "Hotspot lookup failed", "city": city}, error_msg
    
    def _handle_restaurants(self, city: str, cuisine: Optional[str]) -> Tuple[Dict[str, Any], str]:
        """Handle restaurant recommendation requests"""
        try:
            cuisine_filter = f" (filtering by {cuisine})" if cuisine else ""
            print(f"🛠️  [RESTAURANT TOOL] Fetching restaurant data for '{city}'{cuisine_filter}...")
            restaurant_data = self.restaurant_tool.get_restaurants(city, cuisine)
            
            if "error" not in restaurant_data:
                num_restaurants = len(restaurant_data.get('restaurants', []))
                print(f"✅ [RESTAURANT TOOL] Found {num_restaurants} restaurants for {city}")
            else:
                print(f"❌ [RESTAURANT TOOL] Error: {restaurant_data.get('error')}")
            
            if self.verbose:
                print(f"[RESTAURANT TOOL OUTPUT]\n{json.dumps(restaurant_data, indent=2)}\n")
            
            if "error" in restaurant_data:
                return restaurant_data, restaurant_data["error"]
            
            # Format response
            print(f"📝 [AGENT] Calling LLM to format restaurant response...")
            natural_response = self.llm.format_response("food_reco", restaurant_data, 
                                                       city=city, cuisine=cuisine)
            print(f"✅ [AGENT] LLM completed restaurant response formatting")
            
            # Handle formatting errors
            if natural_response.startswith("Error:"):
                cuisine_text = f" for {cuisine}" if cuisine else ""
                return {
                    "intent": "food_reco", 
                    "city": city, 
                    "cuisine": cuisine,
                    "error": "Formatting failed"
                }, f"I found restaurants{cuisine_text} in {city} but couldn't format them properly."
            
            return {
                "intent": "food_reco",
                "city": city,
                "cuisine": cuisine,
                "data": restaurant_data
            }, natural_response
            
        except Exception as e:
            cuisine_text = f" for {cuisine}" if cuisine else ""
            error_msg = f"Failed to get restaurants{cuisine_text} in {city}: {str(e)}"
            return {"error": "Restaurant lookup failed", "city": city, "cuisine": cuisine}, error_msg
    
    def _handle_trip_plan(self, city: str, days: int) -> Tuple[Dict[str, Any], str]:
        """Handle trip planning requests"""
        try:
            # Validate input parameters
            if not city or not city.strip():
                return {"error": "City required for trip planning"}, "I need a city name to plan your trip."
            
            if days <= 0 or days > 14:
                return {"error": "Invalid trip duration"}, "I can only plan trips between 1 and 14 days."
            
            # Gather all necessary data
            weather_data = self.weather_tool.get_weather(city)
            hotspot_data = self.hotspot_tool.get_hotspots(city)
            restaurant_data = self.restaurant_tool.get_restaurants(city)
            
            if self.verbose:
                print(f"[TRIP PLANNING - GATHERING DATA]")
                print(f"Weather: {json.dumps(weather_data, indent=2)}")
                print(f"Hotspots: {json.dumps(hotspot_data, indent=2)}")
                print(f"Restaurants: {json.dumps(restaurant_data, indent=2)}\n")
            
            # Check for critical errors (missing essential data)
            errors = []
            if "error" in weather_data:
                errors.append("weather")
            if "error" in hotspot_data:
                errors.append("attractions")
            if "error" in restaurant_data:
                errors.append("restaurants")
            
            # For trip planning, we need at least hotspots and restaurants
            if "attractions" in errors and "restaurants" in errors:
                error_msg = f"Unable to create trip plan for {city} - missing essential data"
                return {"error": error_msg, "missing": errors}, error_msg
            
            # Combine all data (including partial data with errors)
            all_data = {
                "weather": weather_data,
                "hotspots": hotspot_data,
                "restaurants": restaurant_data
            }
            
            # Format response
            natural_response = self.llm.format_response("trip_plan", all_data, 
                                                       city=city, days=days)
            
            # Handle formatting errors
            if natural_response.startswith("Error:"):
                return {
                    "intent": "trip_plan", 
                    "city": city, 
                    "days": days,
                    "error": "Formatting failed"
                }, f"I gathered data for a {days}-day trip to {city} but couldn't format it properly."
            
            return {
                "intent": "trip_plan",
                "city": city,
                "days": days,
                "data": all_data
            }, natural_response
            
        except Exception as e:
            error_msg = f"Failed to plan trip for {city}: {str(e)}"
            return {"error": "Trip planning failed", "city": city, "days": days}, error_msg
    
    def _handle_missing_city(self, query: str, intent: str) -> Tuple[Dict[str, Any], str]:
        """Handle requests where city information is missing"""
        intent_descriptions = {
            "weather_lookup": "weather information",
            "hotspots_list": "attractions or hotspots",
            "food_reco": "restaurant recommendations", 
            "trip_plan": "trip planning"
        }
        
        description = intent_descriptions.get(intent, "information")
        error_msg = (
            f"I need to know which city you're asking about for {description}. "
            f"Please specify a city name in your request. "
            f"Available cities: Kyoto, Tokyo"
        )
        return {"error": "Missing city", "query": query, "intent": intent}, error_msg
    
    def _handle_unknown(self, query: str) -> Tuple[Dict[str, Any], str]:
        """Handle unknown/unclassified requests"""
        error_msg = (
            "I couldn't understand your request. "
            "Please try asking about weather, hotspots, restaurants, "
            "or trip planning for a specific city."
        )
        return {"error": "Unknown intent", "query": query}, error_msg